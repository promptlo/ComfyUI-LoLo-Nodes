import torch
import comfy.model_management
import comfy.utils
import logging
import node_helpers
import nodes

from comfy_api.latest import io
# 从原始模块导入所需函数和类（假设它们都在 nodes_wan 或 model_multitalk 中）
# 从 comfy_extras 导入 nodes_wan 中的内容
from comfy_extras.nodes_wan import (
    WanInfiniteTalkToVideo,
    linear_interpolation,
    project_audio_features
)

# 从 comfy.ldm.wan 导入 model_multitalk 中的内容
from comfy.ldm.wan.model_multitalk import (
    InfiniteTalkOuterSampleWrapper,
    MultiTalkCrossAttnPatch,
    MultiTalkGetAttnMapPatch
)
# 确保 comfy.patcher_extension 可用
import comfy.patcher_extension

class WanInfiniteTalkToVideoEx(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="WanInfiniteTalkToVideoEx",
            category="conditioning/video_models",
            inputs=[
                io.DynamicCombo.Input("mode", options=[
                io.DynamicCombo.Option("single_speaker", []),
                io.DynamicCombo.Option("two_speakers", [
                    io.AudioEncoderOutput.Input("audio_encoder_output_2", optional=True),
                    io.Mask.Input("mask_1", optional=True, tooltip="Mask for the first speaker, required if using two audio inputs."),
                    io.Mask.Input("mask_2", optional=True, tooltip="Mask for the second speaker, required if using two audio inputs."),
                    ]),
                ]),
                io.Model.Input("model"),
                io.ModelPatch.Input("model_patch"),
                io.Conditioning.Input("positive"),
                io.Conditioning.Input("negative"),
                io.Vae.Input("vae"),
                io.Int.Input("width", default=832, min=16, max=nodes.MAX_RESOLUTION, step=16),
                io.Int.Input("height", default=480, min=16, max=nodes.MAX_RESOLUTION, step=16),
                io.Int.Input("length", default=81, min=1, max=nodes.MAX_RESOLUTION, step=4),
                io.ClipVisionOutput.Input("clip_vision_output", optional=True),
                io.Image.Input("start_image", optional=True),
                io.AudioEncoderOutput.Input("audio_encoder_output_1"),
                io.Int.Input("motion_frame_count", default=9, min=1, max=33, step=1, tooltip="Number of previous frames to use as motion context.", advanced=True),
                io.Float.Input("audio_scale", default=1.0, min=-10.0, max=10.0, step=0.01),
                io.Image.Input("previous_frames", optional=True),
                # 新增的 audio_offset 输入
                io.Int.Input("audio_offset", optional=True, default=None, min=0, max=nodes.MAX_RESOLUTION, tooltip="Audio start frame index (relative to full audio). If provided, overrides calculation from previous_frames length."),
            ],
            outputs=[
                io.Model.Output(display_name="model"),
                io.Conditioning.Output(display_name="positive"),
                io.Conditioning.Output(display_name="negative"),
                io.Latent.Output(display_name="latent"),
                io.Int.Output(display_name="trim_image"),
            ],
        )

    @classmethod
    def execute(cls, mode, model, model_patch, positive, negative, vae, width, height, length, 
                audio_encoder_output_1, motion_frame_count, audio_scale=1.0,
                start_image=None, clip_vision_output=None, previous_frames=None,
                audio_encoder_output_2=None, mask_1=None, mask_2=None,
                audio_offset=None):   # 新增参数
        """执行逻辑与原始节点基本相同，但音频起始位置优先使用 audio_offset"""

        # 处理模式选择（同原始代码）
        if mode["mode"] == "two_speakers":
            audio_encoder_output_2 = mode["audio_encoder_output_2"]
            mask_1 = mode["mask_1"]
            mask_2 = mode["mask_2"]

        if audio_encoder_output_2 is not None and (mask_1 is None or mask_2 is None):
            raise ValueError("Masks must be provided if two audio encoder outputs are used.")

        ref_masks = None
        if mask_1 is not None and mask_2 is not None:
            if audio_encoder_output_2 is None:
                raise ValueError("Second audio encoder output must be provided if two masks are used.")
            ref_masks = torch.cat([mask_1, mask_2])

        # 处理 start_image（同原始代码）
        concat_latent_image = None
        if start_image is not None:
            start_image = comfy.utils.common_upscale(start_image[:length].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
            image = torch.ones((length, height, width, start_image.shape[-1]), device=start_image.device, dtype=start_image.dtype) * 0.5
            image[:start_image.shape[0]] = start_image
            concat_latent_image = vae.encode(image[:, :, :, :3])
            concat_mask = torch.ones((1, 1, ((length-1)//4)+1, concat_latent_image.shape[-2], concat_latent_image.shape[-1]), device=start_image.device, dtype=start_image.dtype)
            concat_mask[:, :, :((start_image.shape[0] - 1) // 4) + 1] = 0.0
            positive = node_helpers.conditioning_set_values(positive, {"concat_latent_image": concat_latent_image, "concat_mask": concat_mask})
            negative = node_helpers.conditioning_set_values(negative, {"concat_latent_image": concat_latent_image, "concat_mask": concat_mask})

        if clip_vision_output is not None:
            positive = node_helpers.conditioning_set_values(positive, {"clip_vision_output": clip_vision_output})
            negative = node_helpers.conditioning_set_values(negative, {"clip_vision_output": clip_vision_output})

        # 占位 latent（同原始代码）
        latent = torch.zeros([1, 16, ((length - 1) // 4) + 1, height // 8, width // 8], device=comfy.model_management.intermediate_device())

        model_patched = model.clone()

        # 处理音频编码（同原始代码）
        encoded_audio_list = []
        seq_lengths = []
        for audio_encoder_output in [audio_encoder_output_1, audio_encoder_output_2]:
            if audio_encoder_output is None:
                continue
            all_layers = audio_encoder_output["encoded_audio_all_layers"]
            encoded_audio = torch.stack(all_layers, dim=0).squeeze(1)[1:]  # [num_layers, T, 512]
            encoded_audio = linear_interpolation(encoded_audio, input_fps=50, output_fps=25).movedim(0, 1)  # [T, num_layers, 512]
            encoded_audio_list.append(encoded_audio)
            seq_lengths.append(encoded_audio.shape[0])

        multi_audio_type = "add"
        if len(encoded_audio_list) > 1:
            if multi_audio_type == "para":
                max_len = max(seq_lengths)
                padded = []
                for emb in encoded_audio_list:
                    if emb.shape[0] < max_len:
                        pad = torch.zeros(max_len - emb.shape[0], *emb.shape[1:], dtype=emb.dtype)
                        emb = torch.cat([emb, pad], dim=0)
                    padded.append(emb)
                encoded_audio_list = padded
            elif multi_audio_type == "add":
                total_len = sum(seq_lengths)
                full_list = []
                offset = 0
                for emb, seq_len in zip(encoded_audio_list, seq_lengths):
                    full = torch.zeros(total_len, *emb.shape[1:], dtype=emb.dtype)
                    full[offset:offset+seq_len] = emb
                    full_list.append(full)
                    offset += seq_len
                encoded_audio_list = full_list

        token_ref_target_masks = None
        if ref_masks is not None:
            token_ref_target_masks = torch.nn.functional.interpolate(
                ref_masks.unsqueeze(0), size=(latent.shape[-2] // 2, latent.shape[-1] // 2), mode='nearest')[0]
            token_ref_target_masks = (token_ref_target_masks > 0).view(token_ref_target_masks.shape[0], -1)

        # ========== 核心修改：处理前置帧和音频偏移 ==========
        if previous_frames is not None:
            motion_frames = comfy.utils.common_upscale(previous_frames[-motion_frame_count:].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
            # 优先使用传入的 audio_offset
            if audio_offset is not None:
                frame_offset = audio_offset
            else:
                frame_offset = previous_frames.shape[0] - motion_frame_count

            audio_start = frame_offset
            audio_end = audio_start + length
            logging.info(f"InfiniteTalkEx: Processing audio frames {audio_start} - {audio_end}")

            motion_frames_latent = vae.encode(motion_frames[:, :, :, :3])
            trim_image = motion_frame_count
        else:
            audio_start = trim_image = 0
            audio_end = length
            # 占位 motion_frames_latent（同原始代码）
            if concat_latent_image is not None:
                motion_frames_latent = concat_latent_image[:, :, :1]
            else:
                motion_frames_latent = torch.zeros([1, 16, 1, height//8, width//8], device=latent.device)

        # 音频投影（同原始代码）
        audio_embed = project_audio_features(model_patch.model.audio_proj, encoded_audio_list, audio_start, audio_end).to(model_patched.model_dtype())
        model_patched.model_options["transformer_options"]["audio_embeds"] = audio_embed

        # 添加包装器和补丁（同原始代码）
        model_patched.add_wrapper_with_key(
            comfy.patcher_extension.WrappersMP.OUTER_SAMPLE,
            "infinite_talk_outer_sample",
            InfiniteTalkOuterSampleWrapper(
                motion_frames_latent,
                model_patch,
                is_extend=previous_frames is not None,
            ))
        model_patched.set_model_patch(MultiTalkCrossAttnPatch(model_patch, audio_scale), "attn2_patch")
        if token_ref_target_masks is not None:
            model_patched.set_model_patch(MultiTalkGetAttnMapPatch(token_ref_target_masks), "attn1_patch")

        out_latent = {"samples": latent}
        return io.NodeOutput(model_patched, positive, negative, out_latent, trim_image)