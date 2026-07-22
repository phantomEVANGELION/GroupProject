# 🌍 AI 跨境出海运营助手 · Demo

AI-powered Export Marketing Assistant — 面向中小制造企业/个人卖家出海场景的 AI 运营工具。

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
   ├── 🌍 市场分析 —— 目标国家推荐 · 市场规模 · 头部企业 · 准入认证
   ├── ⚔️ 竞品分析 —— 竞品对比表格 · 差异化机会 · 改进建议
   ├── 🎯 营销策略 —— 品牌定位 · 渠道建议 · 内容方向
   ├── ✍️ 文案编写 —— Amazon Listing · TikTok 脚本 · 开发信 · 直播话术（中英双语）
   └── 📋 综合报告 —— 核心摘要 · 物流运输建议 · 下一步行动
```

---

## 快速启动

### 环境要求

- Python 3.10+
- 网络连接（首次运行需下载 Embedding 模型，后续离线可用）
- DeepSeek API Key

### 安装与运行

```bash
# 1. 进入项目目录
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
3. 启动 FastAPI 服务

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户浏览器（SPA）                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  首页     │  │ 产品分析  │  │海外平台   │  │汇率咨询   │           │
│  │ #home     │  │ #analyze │  │#platforms│  │ #rates   │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                      │  SSE 流式推送 / REST API                      │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────────┐
│                     FastAPI 后端（app.py）                           │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              LangGraph Workflow（6 节点流水线）                  │ │
│  │                                                                │ │
│  │  product → market → competitor → strategy → content → report   │ │
│  │                                                                │ │
│  │  每个节点：RAG 检索 + Prompt 组装 + LLM 调用 + JSON 容错解析    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                         │                    │                      │
│              ┌──────────▼────┐    ┌─────────▼───────┐              │
│              │   ChromaDB    │    │   DeepSeek API  │              │
│              │  ┌─────────┐  │    │   deepseek-chat  │              │
│              │  │market_kb│  │    │   温度 0.3/0.5   │              │
│              │  │competitor│  │    │                  │              │
│              │  │product_kb│  │    │  BGE Embedding  │              │
│              │  └─────────┘  │    │  bge-small-zh    │              │
│              └───────────────┘    └──────────────────┘              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  app_format.py  结果 dict → 原生 HTML（含置信度标签/表格等）   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| **后端框架** | FastAPI + Uvicorn | REST API + SSE 流式推送 |
| **前端** | 原生 HTML/CSS/JS（SPA） | Hash 路由 4 页面，零框架依赖 |
| **AI 编排** | LangChain ≥0.2 + LangGraph | StateGraph 6 节点串联工作流 |
| **向量数据库** | ChromaDB（本地持久化） | 3 个 Collection：market / competitor / product |
| **Embedding** | BAAI/bge-small-zh-v1.5 | 本地 CPU 推理，自动降级 OpenAI Compatible |
| **LLM** | DeepSeek API（deepseek-chat） | OpenAI 兼容接口，高性价比 |
| **文档解析** | PyMuPDF / python-docx | 支持 PDF / DOCX / TXT / MD / JSON 上传 |

---

## Demo 使用流程

### 标准演示（推荐）

```
1. 打开 http://127.0.0.1:7860
2. 点击导航栏「全面产品分析」
3. 点击「📂 加载示例产品」→ 自动填充 X100 智能运动手表数据
4. 点击「🚀 开始全面分析」
5. 观察 SSE 流式进度条逐步推进（约 30-60 秒完成 6 个节点）
6. 每步完成后弹出 Toast 通知，逐一切换结果标签页查看
7. 在「文案编写」标签页中切换子标签查看 Amazon / TikTok / 开发信 / 直播话术
8. 底部查看「📎 数据来源」了解 RAG 检索结果与降级情况
```

### 自行输入产品

```
1. 填写产品名称和详细描述
2. 可选上传 PDF/TXT/DOCX/MD 产品资料文件
3. 点击「开始全面分析」
```

### 其他页面

| 页面 | 功能 |
|------|------|
| **首页** `#home` | 项目介绍、核心功能卡片、三步上手引导 |
| **海外平台** `#platforms` | Amazon / eBay / TikTok / YouTube / X / Walmart 六大平台介绍 |
| **汇率咨询** `#rates` | 13 种货币实时汇率 + 点击查看 12 月历史走势折线图 + 7 日预测 |

---

## 项目结构

```
ai-export-demo/
│
├── app.py                          # ★ FastAPI 入口 + 完整前端 SPA（4 页面）
├── app_format.py                   # ★ 结果格式化（dict → 原生 HTML 字符串）
├── config.py                       # ★ 全局配置中心（API Key、阈值、路径等）
├── requirements.txt                # Python 依赖清单
├── .env                            # DeepSeek API Key（环境变量）
│
├── workflow/                       # ★ LangGraph 工作流引擎
│   ├── graph.py                    #   图定义：6 节点 DAG 串联
│   ├── state.py                    #   WorkflowState TypedDict
│   └── nodes.py                    #   ★ 6 个节点函数（含 4 层 JSON 容错）
│
├── rag/                            # ★ RAG 知识检索基础设施
│   ├── chroma_client.py            #   ChromaDB 管理 + 双方案 Embedding 加载
│   ├── loader.py                   #   文档加载器（PDF/DOCX/TXT/MD/JSON）
│   └── prompts.py                  #   ★ 5 套 Prompt 模板 + format_prompt()
│
├── knowledge_base/                 # ★ 预置行业知识库（9 大品类）
│   ├── market/                     #   市场数据（11 个 .md 文件，含物流）
│   └── competitors/                #   竞品数据（9 个 .json 文件，各含 5 个竞品）
│
├── init_knowledge_base.py          # 知识库初始化脚本（启动时自动调用）
├── sample_data/                    # 示例产品数据（X100 智能运动手表）
├── data/
│   ├── chroma_db/                  # ChromaDB 持久化存储（自动创建，已 gitignore）
│   └── uploads/                    # 用户上传文件临时目录
│
└── docs/                           # 项目文档（详见 ../../docs/）
```

> 详细项目文档位于 `D:\GroupProject\docs/`，含完整开发日志、项目档案和文档索引。

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `GET /` | — | 返回 SPA 前端完整 HTML |
| `POST /upload` | 文件上传 | 保存到临时目录，返回路径列表（PDF/DOCX/TXT/MD/JSON） |
| `POST /analyze` | 同步分析 | 旧版接口，等待全部完成才返回（向后兼容） |
| `POST /analyze-stream` | **SSE 流式分析** | ★ 推荐方式，每完成一个节点立即推送结果 |
| `GET /api/rates` | 实时汇率 | 调用 ExchangeRate-API，30 分钟缓存，13 种货币 |
| `GET /api/rates/history` | 历史汇率 | 调用 Frankfurter API，近 12 月数据 + 线性回归 7 日预测 |

---

## 当前限制

> ⚠️ 本应用为 **Demo 演示版本**，非生产系统。

| 限制 | 说明 |
|------|------|
| **市场数据** | 来自预置 9 大品类知识库，非实时市场数据 |
| **竞品数据** | 每品类预置 5 个竞品，未覆盖品类降级到 LLM 内置知识 |
| **不支持图片** | 文件上传仅支持 PDF/TXT/DOCX/MD/JSON，无 OCR 能力 |
| **无用户系统** | 单用户模式，每次分析结果保存在内存中 |
| **并发能力** | 单次执行，不支持多用户并发 |
| **API 依赖** | 需要 DeepSeek API Key，Embedding 模型首次需下载 |

---

## 已知问题 / 待办

### 高优先级
- [ ] **移动端适配** — 目前只有 1 条 `@media` 规则，手机体验差
- [ ] **图片 OCR** — 不支持图片上传，需接入 PaddleOCR 或 Tesseract

### 中优先级
- [ ] **知识库动态扩展** — 接入百度搜索实现未命中品类的实时数据补充
- [ ] **多轮对话** — 支持追问和迭代优化
- [ ] **导出报告** — 支持 PDF/Word 导出分析结果

### 低优先级
- [ ] 接入真实 Amazon / Google Trends API
- [ ] 接入 Shopify / TikTok Shop API 实现自动发布
- [ ] 多用户支持 + 历史记录
- [ ] PWA 离线支持

---

## 踩坑记录（开发前必读）

详见 `docs/work-log.md` 完整开发日志。关键要点：

1. **模板花括号转义** — `.format()` 中字面花括号必须用 `{{}}`，否则被解析为占位符
2. **SPA 路由初始化** — 脚本末尾必须主动调用 `navigate()`，不能依赖 `hashchange` 事件
3. **LLM 免责声明** — Prompt 不能写"如果数据不足请如实说明"，应改为"即使没有数据也要输出标准 JSON"
4. **进度条不更新** — 已改为 SSE 流式逐步推送，不再等待全部完成
5. **Gradio 架构废弃** — 最初使用 Gradio UI，因白屏无响应问题弃用，改用 FastAPI + 纯前端 SPA

---

## 相关文档

- [完整开发日志](../docs/work-log.md) — 所有改动记录、踩坑与解决方案
- [项目档案](../docs/profile.md) — 完整项目分析、架构总览、数据流（答辩用）
- [文档索引](../docs/MEMORY.md) — 项目文档导航
- [交接文档](../HANDOVER.md) — 项目概况、启动方式、架构要点
