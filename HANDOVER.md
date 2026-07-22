# 👋 项目交接文档

> 请 Claude 先阅读此文件，再开始工作。
> 当前存档点：`ff220ba` | 运行在 http://127.0.0.1:7860

---

## 📋 项目概况

AI 跨境出海运营助手 — 面向中小制造企业/个人卖家的 AI 运营工具。
输入产品信息 → 自动完成产品分析 → 市场洞察 → 竞品对比 → 营销策略 → 内容生成 → 综合报告（含物流运输建议）

**技术栈**: FastAPI + LangGraph + ChromaDB(RAG) + DeepSeek LLM + 纯 HTML/JS 前端

---

## 🚀 启动方式

```bash
cd D:\GroupProject\ai-export-demo
# 确保 .env 中有 DEEPSEEK_API_KEY
python app.py
# 访问 http://127.0.0.1:7860
```

首次启动会自动下载 BGE Embedding 模型（~33MB）并初始化知识库到 ChromaDB。

---

## 📁 项目结构

```
ai-export-demo/
├── app.py                          # FastAPI 入口 + 完整前端 SPA（4 页面）
├── app_format.py                   # 结果格式化（dict → HTML）
├── config.py                       # 全局配置（API Key、阈值、路径）
├── requirements.txt                # Python 依赖
├── .env                            # DeepSeek API Key
│
├── workflow/
│   ├── graph.py                    # LangGraph 工作流（6 节点串联）
│   ├── state.py                    # WorkflowState TypedDict
│   └── nodes.py                    # 6 个节点函数（含 JSON 容错）
│
├── rag/
│   ├── chroma_client.py            # ChromaDB 管理 + Embedding 加载
│   ├── loader.py                   # 文档加载器（PDF/DOCX/TXT/MD/JSON）
│   └── prompts.py                  # 6 个节点 + 综合报告的 Prompt 模板
│
├── knowledge_base/
│   ├── market/                     # 市场数据（11 个文件，含物流）
│   └── competitors/                # 竞品数据（9 个 JSON）
│
├── init_knowledge_base.py          # 知识库初始化脚本
├── sample_data/                    # 示例产品（X100 智能运动手表）
├── data/chroma_db/                 # ChromaDB 持久化（自动创建，已 gitignore）
│
├── docs/                           
│   └── HANDOVER.md                 # 本文件
│
└── (详细文档见 D:\GroupProject\docs\)
```

---

## 🧠 架构要点

### 工作流（6 步流水线）
```
产品分析 → 市场分析 → 竞品分析 → 营销策略 → 文案编写 → 综合报告
```

每步模式：RAG 检索 → Prompt 组装 → LLM 调用 → JSON 容错解析

### 前端（SPA Hash 路由）
- `#home` — 首页（项目介绍 + 引导）
- `#analyze` — 产品分析页（核心功能）
- `#platforms` — 海外平台介绍（Amazon/eBay/TikTok/YouTube/X/Walmart）
- `#rates` — 汇率咨询（实时汇率 + 历史走势弹窗）

### 流式传输
- `POST /analyze-stream` → SSE 事件流，每完成一个节点推送结果
- 前端 `fetch` + `ReadableStream` 逐步骤渲染 + Toast 通知

### 知识库（9 大品类）
智能手表、小家电、服装、健身器材、玩具、美妆个护、宠物用品、汽车配件、手办潮玩
每个品类含：市场数据（美/欧）+ 竞品数据（5 个竞品）

### RAG 相关性降级
- 检索时使用 `similarity_search_with_relevance_scores()` 获取相关性分数
- 低于阈值 0.45 则判定品类不匹配，跳过 RAG 数据，使用 LLM 内置知识
- 降级提示显示在数据来源区（灰色斜体），不影响主结果

---

## 🔌 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | SPA 前端页面 |
| `/upload` | POST | 上传产品资料文件（PDF/DOCX/TXT/MD/JSON） |
| `/analyze` | POST | 旧版同步分析（向后兼容） |
| `/analyze-stream` | POST | **新版流式分析（推荐）** |
| `/api/rates` | GET | 实时汇率（30 分钟缓存，13 种货币） |
| `/api/rates/history` | GET | 历史汇率 + 7 日线性预测 |

---

## 🐛 已知问题 / 待办

### 高优先级
- [ ] **移动端适配** — 目前只有 1 条 `@media` 规则，手机体验差。需要重构媒体查询、触控目标 44px+、进度条圆点化
- [ ] **图片 OCR** — 不支持图片上传，需要接入 PaddleOCR 或 Tesseract

### 中优先级
- [ ] **知识库动态扩展** — 目前是预置 9 个品类，可以考虑接入百度搜索实现未命中品类的实时数据补充
- [ ] **多轮对话** — 目前每次分析独立，不支持追问和迭代优化
- [ ] **导出报告** — 支持 PDF/Word 导出分析结果

### 低优先级
- [ ] 接入真实 Amazon/Google Trends API
- [ ] 接入 Shopify/TikTok Shop API 实现自动发布
- [ ] 多用户支持 + 历史记录
- [ ] PWA 离线支持

---

## ⚠️ 踩坑记录（开发前必读）

### 1. 模板花括号转义（已修复）
`.format()` 渲染的 Prompt 模板中，字面花括号必须用 `{{}}` 而不是 `{}`，否则会被解析为占位符报错，`format_prompt` 会降级返回未填充的原始模板，导致 LLM 收到混乱指令。

### 2. SPA 路由初始化（已修复）
`Ctrl+F5` 后浏览器会恢复上次 session 的 hash，导致 `navigate()` 从未被调用，所有页面 `display:none`。修复方案：脚本末尾始终主动调用一次 `navigate()`。

### 3. LLM 免责声明（已修复）
当 Prompt 含"如果数据不足请如实说明"时，LLM 会输出"建议通过市场调研补充数据"的空话。应改为"即使没有数据也必须完成分析并输出标准 JSON"。

### 4. 进度条不更新（已修复）
最早版本是同步请求，用户需等待 1 分钟后才看到结果。已改为 SSE 流式逐步推送。

### 5. 标签页不可见（已修复）
`tabsSection` 初始为 `className = "tabs"`（`display:none`），从未切换为 `"tabs active"`，结果数据在 DOM 中但用户看不到。

---

## 💡 扩展方向

- **知识库**：按 `categories.json` 索引组织，支持按品类动态加载
- **前端**：可提取为独立 React/Vue 项目，后端只提供 API
- **AI 增强**：接入多轮对话、报告对比、批量分析
- **部署**：可 Docker 化部署，配置环境变量即可运行

---

## 📞 相关文件

- 完整开发日志：`docs/work-log.md`
- 项目档案（答辩用）：`docs/profile.md`
- 项目记忆索引：`docs/MEMORY.md`
- 配置文件：`config.py`（阈值、路径、模型参数集中管理）
- 应用 README：`ai-export-demo/README.md`
