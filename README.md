# NAI Flow

面向 NovelAI Diffusion V5 的图片与多页漫画工作流。项目参考 `D:\opencode\h3-api` 和 `D:\opencode\ocworkflow` 的目录边界：Vite 前端只调用相对 `/api`，FastAPI 后端代理模型服务并持久化运行时配置。

## 启动

首次安装依赖：

```powershell
cd D:\codex\nai\server
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

cd ..\web
# 如果系统盘空间很紧张，把 npm 的缓存和临时文件放到项目盘
$env:npm_config_cache = "D:\codex\nai\.npm-cache"
$env:TEMP = "D:\codex\nai\.tmp"
$env:TMP = "D:\codex\nai\.tmp"
npm install
```

启动两个进程：

```powershell
# 终端 1：后端 API，默认 http://127.0.0.1:8000
cd D:\codex\nai\server
.\.venv\Scripts\python -m uvicorn main:app --reload --port 8000

# 终端 2：前端，默认 http://127.0.0.1:5173
cd D:\codex\nai\web
npm run dev
```

访问 `http://127.0.0.1:5173`，在“服务端连接设置”输入 NovelAI API Token。

## 包含的流程

- 基础出图：V5 Full / Curated、尺寸、步骤、CFG、采样器、随机种子、正反向提示词和结构化角色提示词。
- 本子生成：故事梗概 → 本地可编辑分镜，或用 OpenAI 兼容文本模型生成 JSON 分镜 → 每页多格漫画图。
- 素材库：保存当前会话生成结果，下载图片，导出/导入项目 JSON。

## 数据与密钥

- 页面只保存项目编辑状态；旧版遗留在浏览器中的 token 会自动移除。
- API Token 和模型地址由后端保存到 `server/store/settings.json`（已在 `.gitignore` 中排除），前端不会读取 token；图片与剧本请求均通过后端代理。
- 生成接口返回的 ZIP 图片会在浏览器端解包。浏览器需要支持 `DecompressionStream`（当前 Chrome/Edge 支持）。
