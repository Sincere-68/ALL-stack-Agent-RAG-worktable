# Agentic AI + RAG 文档知识库工作台

## 项目概要

本项目是一个基于 **Agentic AI + RAG** 的文档知识库问答系统，面向论文、报告、业务文档等长文档场景。系统支持文档上传、PDF 解析、语义分块、Embedding 向量化、ChromaDB 检索、多轮对话、工具调用和引用来源展示，帮助用户围绕本地知识库进行可追溯问答。

项目重点解决长文档问答中的几个问题：大模型直接处理长文档时上下文受限，普通分块容易切断语义，表格内容容易丢失结构，检索结果缺少来源说明，以及模型调用或向量库异常容易导致接口失败。系统通过父子 chunk 分层切分、句子边界切分、表格独立 chunk、轻量级 rerank、引用溯源和异常降级处理，提高问答准确性、上下文完整性和系统稳定性。

## 技术栈

- 后端与 Agent：**FastAPI**、**LangGraph**、**LangChain**、**Pydantic**
- 知识库与检索：**ChromaDB**、**OpenAIEmbeddings**、**SQLite**
- 文档解析：**PyMuPDF**、**OCR/VLM**
- 模型接入：**OpenAI-compatible API**、**Qwen**、**DeepSeek**
- 前端工程：**Vite**、**React**、**Tailwind CSS**

## 核心能力

- 文档上传与知识库管理，支持 **PDF / DOCX / TXT / MD / CSV / XLSX**
- PDF 按页解析，保留来源文件、页码、章节路径和内容类型
- 父子 chunk 分层切分：父 chunk 提供完整上下文，子 chunk 提供精确检索
- 句子边界切分，降低语义被截断的概率
- 表格独立 chunk，保留表格编号、caption、Markdown 内容和问答上下文
- ChromaDB 向量检索，支持切换不同 Embedding 模型和 collection
- 轻量级 rerank，根据关键词、章节、chunk 类型和表格编号提升检索排序
- LangGraph Agent 工作流，支持知识库检索、计算器、当前时间等工具调用
- 多轮会话管理，使用 SQLite 保存会话和消息
- 回答引用来源展示，包含文件名、页码、章节、chunk 类型和表格编号
- 异常降级处理，避免 LLM 连接失败、检索失败或工具不可用时直接 500

## 项目结构

```text
.
├── agent/                         # Agent、RAG、工具和模型调用核心逻辑
│   ├── graph/                     # LangGraph 工作流构建
│   ├── knowledge/                 # 文档解析、语义分块、向量库检索
│   ├── llm/                       # LLM 工厂与模型接入
│   ├── memory/                    # SQLite 会话存储
│   ├── nodes/                     # Agent 节点逻辑
│   ├── prompts/                   # 系统提示词
│   ├── state/                     # Agent 状态定义
│   └── tools/                     # 本地工具和 Web Search 占位工具
├── backend/                       # FastAPI 接口层
│   ├── main.py                    # FastAPI 应用入口
│   ├── routes.py                  # Chat 接口
│   ├── routes_conversation.py     # 会话管理接口
│   ├── routes_knowledge.py        # 知识库上传、删除、列表、文件预览接口
│   └── schemas.py                 # Pydantic 数据模型
├── frontend/                      # Vite 前端工作台
│   ├── src/
│   │   ├── components/            # Chat、Navbar、ToolPanel 等组件
│   │   ├── pages/                 # 首页、工作台、知识库页面
│   │   └── utils/                 # API 请求封装
│   ├── package.json
│   └── vite.config.js
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖
├── pyproject.toml                 # Python 项目配置
└── README.md
```

运行时会生成以下目录或文件，默认不会提交到 Git：

```text
chroma_db/                         # ChromaDB 本地向量库
uploads/                           # 上传的文档文件
logs/                              # 运行日志
conversations.db                   # SQLite 会话数据库
.env                               # 本地环境变量和 API key
```

## 环境变量

复制 `.env.example` 为 `.env`，并填写自己的 API key：

```powershell
copy .env.example .env
```

主要配置项：

```env
LLM_PROVIDER=openai
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
LLM_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_API_KEY=sk-xxx

EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_COLLECTION_NAME=knowledge_base_qwen3_embedding_8b

OCR_MODEL=deepseek-ai/DeepSeek-OCR
```

注意：切换 `EMBEDDING_MODEL` 后，不要复用旧的 ChromaDB collection。建议同步修改 `EMBEDDING_COLLECTION_NAME`，或删除并重建 `chroma_db/`，避免不同向量维度混用导致入库失败。

## 运行方式

### 1. 启动后端

推荐使用已有的 `conda` 环境：

```powershell
conda activate agent
cd /d D:\workflow\Full-Stack-Agentic-AI-Project-main
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

如果是首次安装依赖：

```powershell
pip install -r requirements.txt
```

后端接口地址：

```text
http://127.0.0.1:8000
```

### 2. 启动前端

```powershell
cd /d D:\workflow\Full-Stack-Agentic-AI-Project-main\frontend
npm install
npm run dev -- --host 127.0.0.1
```

前端访问地址：

```text
http://127.0.0.1:5173
```

常用页面：

```text
首页：   http://127.0.0.1:5173/
工作台： http://127.0.0.1:5173/chat
知识库： http://127.0.0.1:5173/knowledge
```

## 使用流程

1. 启动后端和前端。
2. 进入知识库页面上传文档。
3. 系统解析文档、生成 chunk、调用 Embedding API 并写入 ChromaDB。
4. 进入工作台，在左侧查看 PDF 原文，在中间与 Agent 对话。
5. Agent 会结合知识库检索结果回答，并展示引用来源。

## 验证命令

后端语法检查：

```powershell
python -m py_compile backend\main.py backend\routes.py backend\routes_knowledge.py agent\runner.py
```

前端检查：

```powershell
cd frontend
npm run lint
npm run build
```

Windows 环境下如果 `npm run build` 出现 `esbuild spawn EPERM`，可以尝试使用管理员终端或提升权限后重新运行。

## 说明

- `.env` 包含本地 API key，不要提交到 GitHub。
- `uploads/`、`chroma_db/`、`conversations.db` 属于运行数据，默认已加入 `.gitignore`。
- 当前 Web Search 需要配置 `TAVILY_API_KEY` 并启用 `ENABLE_ONLINE_TOOLS=1` 后使用。
- MCP 工具入口已预留，可继续扩展文件系统、数据库、浏览器、GitHub 等工具能力。
