// ComfyUI-LoLo-Nodes/web/lolo_nodes.js
import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "LoLo.Nodes.SaveDirToZip",

    async nodeCreated(node) {
        if (node.comfyClass !== "LoloSaveDirToZip") return;

        console.log(`[LoLo Nodes] 节点 ${node.id} 已创建 (类型: ${node.type})`);

        // 1. 创建下载按钮
        const downloadButton = document.createElement('button');

        // 2. 【状态恢复】检查节点是否已有输出（工作流重新加载时）
        const previewWidget = node.widgets?.find(w => w.name === 'preview');
        const hasOutput = previewWidget && previewWidget.value &&
                         typeof previewWidget.value === 'string' &&
                         previewWidget.value.includes('/view?');

        if (hasOutput) {
            // 情况A：工作流重新加载，节点已有输出 -> 直接创建激活按钮
            console.log(`[LoLo Nodes] 节点 ${node.id} 检测到已有输出，创建激活按钮`);
            downloadButton.textContent = '⬇ 下载ZIP文件';
            downloadButton.disabled = false;
            downloadButton.style.cssText = getActiveButtonStyle();
            // 绑定下载事件
            const filePath = previewWidget.value;
            downloadButton.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log(`[LoLo Nodes] 从缓存状态下载: ${filePath}`);
                window.open(filePath, '_blank');
            };
        } else {
            // 情况B：全新节点 -> 创建待机按钮
            console.log(`[LoLo Nodes] 节点 ${node.id} 无输出，创建待机按钮`);
            downloadButton.textContent = '⏳ 请先执行';
            downloadButton.disabled = true;
            downloadButton.style.cssText = getDisabledButtonStyle();
        }

        // 3. 将按钮添加为DOM部件
        node.addDOMWidget(
            "lolo_download_btn",
            "custom",
            downloadButton,
            () => '',
            () => {}
        );
        node._loloDownloadButton = downloadButton;

        // 4. 【重要】节点ID就是后端的 unique_id，保存以供消息匹配
        node._loloNodeId = node.id;
        console.log(`[LoLo Nodes] 节点 ${node.id} 初始化完成，等待消息。`);
    },

    async setup() {
        console.log('[LoLo Nodes] 扩展已安装，监听消息中...');

        // 监听来自Python后端的 'lolo.zip_ready' 事件
        app.api.addEventListener("lolo.zip_ready", (event) => {
            const { file_path, node_id } = event.detail; // 包含后端发送的 node_id
            console.log(`[LoLo Nodes] 收到消息，目标节点ID: ${node_id}, 文件路径: ${file_path}`);

            if (node_id === undefined || node_id === null) {
                console.warn('[LoLo Nodes] 错误：消息中未包含节点ID。');
                return;
            }

            // ========== 核心修改：直接通过 node_id 查找节点 ==========
            // 后端的 unique_id 就是前端的节点 id，可以直接查找
            const targetNode = app.graph._nodes_by_id[node_id];

            if (!targetNode) {
                console.warn(`[LoLo Nodes] 错误：未找到ID为 ${node_id} 的节点。`);
                return;
            }

            if (!targetNode._loloDownloadButton) {
                console.warn(`[LoLo Nodes] 错误：节点 ${node_id} 没有下载按钮。`);
                return;
            }
            // =====================================================

            console.log(`[LoLo Nodes] 成功找到节点 ${node_id}，正在激活下载按钮。`);
            const button = targetNode._loloDownloadButton;

            // 更新按钮为激活状态
            button.disabled = false;
            button.textContent = '⬇ 下载ZIP文件';
            button.style.cssText = getActiveButtonStyle();
            // 添加悬停效果
            button.onmouseover = () => button.style.opacity = '0.9';
            button.onmouseout = () => button.style.opacity = '1';

            // 绑定点击下载事件
            button.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log(`[LoLo Nodes] 触发下载: ${file_path}`);
                window.open(file_path, '_blank');
            };

            console.log(`[LoLo Nodes] 节点 ${node_id} 的按钮已更新并生效。`);
        });
    }
});

// 工具函数：获取激活按钮样式
function getActiveButtonStyle() {
    return `
        margin: 10px 5px 5px 5px;
        padding: 8px 12px;
        width: calc(100% - 10px);
        box-sizing: border-box;
        background: linear-gradient(to bottom, #4CAF50, #2E7D32);
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
        font-weight: bold;
        font-family: inherit;
        text-align: center;
        display: block;
        transition: opacity 0.2s;
    `;
}

// 工具函数：获取禁用按钮样式
function getDisabledButtonStyle() {
    return `
        margin: 10px 5px 5px 5px;
        padding: 8px 12px;
        width: calc(100% - 10px);
        box-sizing: border-box;
        background-color: #e0e0e0;
        color: #9e9e9e;
        border: 1px solid #bdbdbd;
        border-radius: 4px;
        cursor: not-allowed;
        font-size: 12px;
        font-weight: bold;
        font-family: inherit;
        text-align: center;
        display: block;
    `;
}

// 为 LoloGetVideoInfo 添加文件上传按钮

// 为 LoloGetVideoInfo 添加文件上传按钮
app.registerExtension({
    name: "LoLoNodes.VideoUpload",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LoloGetVideoInfo") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated?.apply(this, arguments);

                // 查找 video_path 的 widget
                const widget = this.widgets.find(w => w.name === "video_path");
                if (widget) {
                    // 隐藏原文本框
                    widget.type = "hidden";

                    // 创建按钮
                    const button = document.createElement("button");
                    button.textContent = "📁 选择视频文件";
                    button.style.margin = "5px 0";
                    button.style.padding = "8px 12px";
                    button.style.background = "#2a6d8c";
                    button.style.color = "white";
                    button.style.border = "none";
                    button.style.borderRadius = "4px";
                    button.style.cursor = "pointer";
                    button.addEventListener("click", async () => {
                        const input = document.createElement("input");
                        input.type = "file";
                        input.accept = "video/*";
                        input.onchange = async (e) => {
                            const file = e.target.files[0];
                            if (!file) return;

                            // 上传文件到 ComfyUI 的 input 目录
                            const formData = new FormData();
                            formData.append("image", file); // 复用上传接口
                            formData.append("subfolder", "video");
                            formData.append("type", "input");

                            try {
                                const resp = await fetch("/upload/image", {
                                    method: "POST",
                                    body: formData
                                });
                                const data = await resp.json();
                                if (data.name) {
                                    // 存储相对路径，ComfyUI 默认 input 目录
                                    const filePath = `input/video/${data.name}`;
                                    widget.value = filePath;
                                    // 触发更新
                                    this.setDirtyCanvas(true);
                                }
                            } catch (err) {
                                alert("上传失败: " + err);
                            }
                        };
                        input.click();
                    });

                    // 延迟将按钮插入节点 DOM（确保 this.el 已存在）
                    setTimeout(() => {
                        const el = this.el;
                        if (el) {
                            const btns = el.querySelector(".comfy-node-btns");
                            if (btns) btns.appendChild(button);
                            else el.appendChild(button);
                        }
                    }, 10);
                }
                return r;
            };
        }
    }
});