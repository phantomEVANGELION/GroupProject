# 🌍 AI 跨境出海运营助手 · Demo

AI-powered Export Marketing Assistant — 面向中小制造企业出海场景的 AI 运营助手 Demo。

通过 **RAG + LangGraph + DeepSeek** 实现从产品分析到营销内容生成的完整闭环。

---

## 功能概览

用户输入产品信息后，系统自动完成以下全流程分析：

```
📄 产品资料
   ↓
📚 RAG 知识检索（ChromaDB + BGE Embedding）
   ↓
🤖 AI 分析（DeepSeek LLM via LangGraph Workflow）
   ├── 📋 产品分析 —— 分类 · 卖点 · 用户画像 · 痛点
   ├── 🌍 市场分析 —— 目标国家推荐 · 市场机会 · 进入风险
   ├── ⚔️ 竞品分析 —— 竞品对比表格 · 差异化机会
   ├── 🎯 营销策略 —— 品牌定位 · 渠道建议 · 内容方向
   └── ✍️ 内容生成 —— Amazon Listing · TikTok 脚本 · 开发信 · 直播话术
```

---

## 快速启动

### 环境要求

- Python 3.10+
- 网络连接（首次运行需下载 Embedding 模型，后续离线可用）
- DeepSeek API Key

### 安装与运行

```bash
# 1. 克隆项目
cd ai-export-demo

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
# 编辑 .env 文件，填入你的 DeepSeek API Key
# DEEPSEEK_API_KEY=sk-your-key-here

# 4. 启动应用
python app.py

# 5. 打开浏览器
# 访问 http://127.0.0.1:7860
```

首次启动会自动完成：
1. 下载 BGE Embedding 模型（约 33MB）
2. 初始化市场知识库和竞品知识库到 ChromaDB
3. 启动 Gradio 交互界面

---

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                    Gradio 前端                       │
│  输入产品信息 → yield 进度展示 → 5 个结果 Tab 页     │
└─────────────────────┬───────────────────────────────┘
                      │ workflow.invoke()
┌─────────────────────▼───────────────────────────────┐
│              LangGraph Workflow（同步执行）            │
│                                                     │
│  product_node → market_node → competitor_node       │
│       → strategy_node → content_node                │
│                                                     │
│  每个节点：RAG 检索 + Prompt 组装 + LLM 调用          │
└──────────┬─────────────────────────┬────────────────┘
           │                         │
┌──────────▼──────────┐  ┌──────────▼───────────────┐
│     ChromaDB        │  │     DeepSeek API          │
│  ┌──────────────┐   │  │                          │
│  │ product_kb   │   │  │  模型: deepseek-chat      │
│  │ (用户上传)    │   │  │  温度: 0.3(分析) / 0.5(内容)│
│  ├──────────────┤   │  │                          │
│  │ market_kb    │   │  │  Embedding:               │
│  │ (预置市场数据) │   │  │  BAAI/bge-small-zh-v1.5  │
│  ├──────────────┤   │  │  (本地 CPU, 512维)         │
│  │ competitor_kb│   │  │                          │
│  │ (预置竞品数据) │   │  │  降级: OpenAI Compatible  │
│  └──────────────┘   │  │                          │
└─────────────────────┘  └──────────────────────────┘
```

### 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 前端交互 | Gradio 5.50.0 | 单页应用，支持 generator 逐步更新 |
| AI 编排 | LangChain ≥0.2 + LangGraph | Workflow 状态图、RAG 抽象 |
| 向量数据库 | ChromaDB | 持久化本地运行，3 个 Collection |
| Embedding | BAAI/bge-small-zh-v1.5 | 本地 CPU 推理，自动降级 |
| LLM | DeepSeek API | OpenAI 兼容接口，高性价比 |
| 文档处理 | PyMuPDF / python-docx | 支持 PDF/TXT/DOCX/MD/JSON |

---

## Demo 使用流程

### 标准演示（推荐）

```
1. 打开 http://127.0.0.1:7860
2. 点击「📂 加载示例产品」→ 自动填充 X100 智能运动手表数据
3. 点击「🚀 开始全面分析」
4. 观察进度条逐步推进（约 25-35 秒完成 5 个节点）
5. 逐一切换 5 个结果标签页查看完整分析
6. 在内容生成标签页中查看 Amazon / TikTok / 开发信 / 直播话术
7. 底部查看「📎 数据来源」展示 RAG 检索结果
```

### 自行输入产品

```
1. 填写产品名称和详细描述
2. 可选上传 PDF/TXT/DOCX 产品资料
3. 点击「开始全面分析」
```

---

## 项目结构

```
ai-export-demo/
│
├── app.py                          # Gradio 唯一入口（启动 + 前端 + 工作流调用）
├── config.py                       # 全局配置（API Key、ChromaDB 路径、RAG 参数）
├── requirements.txt                # Python 依赖
├── .env                            # 环境变量（DeepSeek API Key）
├── README.md                       # 本文件
│
├── workflow/                       # LangGraph 工作流
│   ├── graph.py                    # 图定义 + 编译
│   ├── state.py                    # WorkflowState TypedDict
│   └── nodes.py                    # 5 个节点函数（含 JSON 容错）
│
├── rag/                            # RAG 基础设施
│   ├── loader.py                   # 文档加载器（PDF/TXT/DOCX/MD/JSON）
│   ├── chroma_client.py            # ChromaDB 管理（3 个 Collection + Embedding）
│   └── prompts.py                  # 5 个节点的 Prompt 模板
│
├── knowledge_base/                 # 预置行业知识库
│   ├── market/                     # 市场数据（美国/日本/欧洲）
│   └── competitors/                # 竞品数据（智能手表品类 5 个竞品）
│
├── sample_data/                    # 示例产品数据
│   └── smart_watch_demo.txt
│
├── init_knowledge_base.py          # 知识库初始化脚本（启动时自动调用）
└── data/chroma_db/                 # ChromaDB 持久化目录（自动创建）
```

---

## 当前限制

> ⚠️ 本应用为 **Demo 演示版本**，非生产系统。

| 限制 | 说明 |
|------|------|
| **市场数据** | 来自预置知识库，非实时市场数据 |
| **竞品数据** | 预置了智能手表品类 5 个竞品，其他品类需补充 |
| **AI 输出** | 仅供辅助决策参考，建议人工审核后使用 |
| **文件上传** | 仅支持 PDF/TXT/DOCX，不支持 OCR 图片识别 |
| **并发** | 单用户同步执行，不支持多用户并发 |
| **数据持久化** | 无用户系统，每次分析结果保存在内存中 |
| **API 依赖** | 需要 DeepSeek API Key，Embedding 模型首次需下载 |

---

## 扩展方向

- 接入实时 Amazon / Google Trends API 获取真实市场数据
- 增加更多品类（家居、服装、小家电等）的预置知识库
- 支持用户自定义知识库数据
- 增加内容多轮迭代优化
- 接入 Shopify / TikTok Shop API 实现自动发布
