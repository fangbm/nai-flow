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
- 本子导出：一键下载 ZIP，包含已生成的页面图片、每页完整提示词、分镜 JSON 与说明；尚未出图的页面也会保留剧本和提示词。
- 素材库：图片会保存到本机后端，刷新页面后仍能恢复；支持下载图片，导出/导入项目 JSON。

## 本子提示词策略

本子分镜遵循内置的 NAI V5 规则文件 [`server/app/nai5_storyboard_skill.md`](server/app/nai5_storyboard_skill.md)。它基于用户提供的 [`nai5-prompting`](https://github.com/Miint-Sunny/nai5-prompting) 的构思、字段分工、多角色、漫画分格和排查章节整理为可在运行时直接注入剧本文本模型的上下文，因此部署此项目时不需要额外安装 Codex Skill。

- LLM 只在分镜主提示词中使用 `Character 1`、`Character 2` 等编号，避免角色名和外貌描述污染分镜。
- NovelAI V5 的独立 `Character N` 字段负责绑定角色身份；界面可将中文角色名识别为英文/罗马字名和作品出处后填入该字段。
- 每格是一个清晰的定格瞬间，明确动作发起者、接受者、镜头、场景和光照；多格页先锁定版式与格位锚点，再逐格生成，并携带跨格/跨页的视觉连续性。
- 人数提示按单格内同时出现的 `Character N` 计算，避免把同一角色在不同格里的重复出场误判为多人。

实际注入文本模型的 system prompt 位于 `server/app/services.py`，而前端将分镜拼接成 NovelAI V5 Prompt 及 Character 字段的逻辑位于 `web/app.js`。

## 数据与密钥

- 页面只保存项目编辑状态；旧版遗留在浏览器中的 token 会自动移除。
- API Token 和模型地址由后端保存到 `server/store/settings.json`；项目状态保存到 `server/store/project.json`；生成图片保存到 `server/store/assets/`。这些运行时数据均已在 `.gitignore` 中排除，前端不会读取 token；图片与剧本请求均通过后端代理。
- 生成接口返回的 ZIP 图片由前端通过 `fflate` 解包。
