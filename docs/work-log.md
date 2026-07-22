---
name: work-log
description: AI 跨境出海运营助手 Demo 开发工作日志
metadata:
  type: project
---

# 开发工作日志

## 存档点：26315d9（当前最新）

### 项目概况
AI 跨境出海运营助手 Demo — FastAPI + LangGraph + RAG(ChromaDB) + DeepSeek LLM
面向中小制造企业出海场景，实现产品分析到营销内容生成的完整闭环。

---

### 改动零：Gradio UI 替换为 FastAPI + 纯前端 SPA（架构级重构）

> 这是项目最根本的架构决策，后续所有改动都基于此架构。

#### 最初设计（已废弃）
最初使用 **Gradio**（`gradio_api` 端点）作为前端框架，通过 Gradio 的 generator 机制实现逐步更新。当时的设计是：
- `app.py` 中嵌入了 Gradio 的 Blocks/Interface
- 前端通过 Gradio 内置的 API 路由（`/gradio_api/call/`、`/gradio_api/predict`）与后端交互
- 工作流通过 `yield` 逐步骤输出结果到 Gradio 前端
- 技术栈参考了 Gradio 5.50.0 的 generator 流式更新模式
- `README.md` 中的架构图、技术栈说明均基于此设计（已过时）
- `test_api2.py` 是当时用来测试 Gradio API 调用的脚本（残存遗留文件）

#### 遇到的问题
1. **Gradio 与 LangGraph 配合不佳** — Gradio 的 generator 机制在复杂工作流场景下不稳定，多步骤状态传递容易丢失
2. **前端响应不可控** — Gradio 在长时间分析过程中出现白屏、无响应现象，用户体验差
3. **UI 定制空间小** — Gradio 的组件化 UI 难以满足多 Tab 嵌套子 Tab、复杂数据表格等展示需求
4. **API 耦合度高** — Gradio 内置 API 层不够灵活，调试困难

#### 新架构（当前方案）
完全抛弃 Gradio，改用 **FastAPI + 纯原生 HTML/CSS/JavaScript SPA**：

| 维度 | 旧方案（Gradio） | 新方案（FastAPI + SPA） |
|------|----------------|----------------------|
| **Web 框架** | Gradio（内含 FastAPI） | 纯 FastAPI + Uvicorn |
| **前端** | Gradio 组件渲染 | 原生 HTML/CSS/JS，零框架依赖 |
| **流式** | Gradio generator（yield） | SSE（Server-Sent Events） |
| **路由** | Gradio 内置 Tab 切换 | Hash 路由（`#home/#analyze/...`） |
| **多页面** | 不支持 | 4 页面 SPA（首页/分析/平台/汇率） |
| **定制性** | 受限的组件 API | 完全自由 |
| **API 层** | `/gradio_api/*` 自动生成 | 自定义 RESTful API |
| **部署** | 依赖 Gradio 运行时 | 标准 FastAPI 应用 |

#### 涉及的文件
- **重写**: `app.py` — 从 Gradio Blocks 改为 FastAPI + 完整前端 SPA
- **新增**: `app_format.py` — 新增格式化模块（旧方案中格式逻辑内嵌在 Gradio 回调中）
- **遗留（待清理）**: `test_api2.py` 为 Gradio 测试脚本（不影响运行，未删除供参考）

#### 教训
Gradio 适合快速原型验证，但一旦工作流逻辑复杂、前端展示要求高，应当尽早切换到标准 Web 框架。SSE 流式推送比 Gradio 的 generator 机制更稳定可控，且纯 HTML 前端提供了完全自由的展示能力。

---

### 改动一：SSE 流式进度 + 逐步骤渲染 + 通知动画
- 新增 `/analyze-stream` SSE 端点，后端每完成一个节点立即推送结果
- 前端 `fetch` + `ReadableStream` 流式读取，逐步渲染 5 个 Tab
- 每步完成后弹出 Toast 通知动画（"✅ 产品分析生成完毕！"等）
- 保留旧 `/analyze` 端点向后兼容
- **涉及文件**: `app.py`

### 改动二：品类匹配 + RAG 相关性降级
- `chroma_client.py` 新增 `similarity_search_with_relevance_scores()` 函数
- `market_node` 和 `competitor_node` 检索后检查相关性分数与阈值（0.45）
- 低于阈值时跳过 RAG 数据，使用 LLM 内置知识兜底
- Prompt 模板同步增强，指示 LLM 在数据不相关时自行推理
- 品类降级提示从错误框移至数据来源区（灰色斜体）
- **涉及文件**: `workflow/nodes.py`, `rag/chroma_client.py`, `rag/prompts.py`, `app_format.py`

### 改动三：输出格式 HTML 化
- `app_format.py` 全部 Markdown 输出改为原生 HTML
- 新增表格、置信度标签、市场条目卡片、内容代码块等样式
- 修复：tabsSection 初始状态为 `display:none` 导致结果不可见

### 改动四：知识库扩展（9 大品类）
- 原有智能手表保留
- 新增 8 个品类：小家电、服装、健身器材、玩具、美妆个护、宠物用品、汽车配件、手办潮玩
- 每品类包含市场数据文件（美欧市场规模/消费者/认证/风险）和竞品数据文件（5 个竞品）
- 共 16 个新文件，824 行新增内容
- 所有品类实测通过：市场和竞品双双命中 ✅
- **涉及文件**: `knowledge_base/market/*.md`, `knowledge_base/competitors/*.json`

### 改动五：界面文案调整
- "内容生成" 全部替换为 "文案编写"（进度条/Tab名/通知）
- 营销策略 Prompt 增加中文约束，渠道和策略全部输出中文
- 内容生成 Prompt 改为中英双语输出（英文原版 + 中文翻译）
- **涉及文件**: `app.py`, `rag/prompts.py`

---

### 改动六：文件上传支持
- 新增 `/upload` POST 端点，支持 PDF/DOCX/TXT/MD/JSON 文件上传
- 前端输入区增加文件选择 UI（虚线拖拽区 + 文件标签列表 + 移除功能）
- `analyze-stream` 和 `analyze` 端点现在接收 `uploaded_files` 参数
- 修复 `product_node` 中 `reset_collection` 在循环内导致多文件上传失效的 bug
- 图片格式暂不支持（需 OCR），上传时会返回明确错误提示
- **涉及文件**: `app.py`, `workflow/nodes.py`

---

### 改动七：SPA 多页面前端重构
- 新增导航栏：首页 / 全面产品分析 / 海外平台介绍 / 实时汇率
- Hash 路由 SPA 架构，4 个页面通过 `#home` / `#analyze` / `#platforms` / `#rates` 切换
- **首页**: Hero 大标题 + 项目介绍 + 核心功能卡片 + 三步上手引导 + "开始使用"按钮
- **分析页**: 原有页面完整保留，未做改动
- **海外平台介绍**: Amazon / eBay / TikTok / YouTube / X / Walmart 六个平台卡片，含品牌色图标、描述、运营建议
- **实时汇率**: `/api/rates` 端点，30 分钟缓存，展示 13 种货币兑 USD + CNY 换算
- **涉及文件**: `app.py`

---

### 改动八：汇率历史走势弹窗（折线图 + 分析 + 预测）
- 导航栏和页面标题"实时汇率"改为"汇率咨询"
- 点击任一汇率卡片弹出居中 Modal，显示近 12 月折线图（Canvas 自绘，零依赖）
- 折线图含：面积填充、网格线、月度标签、统计摘要（最高/最低/变动%）
- 新增 `/api/rates/history` 端点，从 Frankfurter API 获取历史数据
- 后端线性回归生成 7 日预测，前端以虚线绘制在图表右侧
- 文字分析：趋势描述、波动评估、预测说明
- 预测仅供参考标注
- **涉及文件**: `app.py`

---

### 改动九：市场/竞品分析增强 + 综合报告（物流运输）
- 市场分析新增：市场规模（美/欧/全球）、头部企业及份额、准入限制与认证、重要行业展会
- 竞品分析新增：产品改进建议（含影响/投入评级）
- 新增第 6 个节点"综合报告"：汇总前 5 步精华 + 物流运输分析（海运/空运对比、运费参考、货代选择建议）
- 新增物流知识库 `international_logistics.md`（航线运费、船公司、清关关税参考数据）
- 新增 `format_comprehensive` 格式函数（摘要 + 关键数据卡片 + 运输建议 + 综合建议）
- 工作流从 5 步扩展为 6 步，前端进度条/Tab/通知全部同步更新
- **涉及文件**: `rag/prompts.py`, `app_format.py`, `workflow/nodes.py`, `workflow/graph.py`, `workflow/state.py`, `app.py`, `knowledge_base/market/international_logistics.md`

---

### 遇到的坑与解决方案

#### 🕳️ 坑 1：模板花括号转义导致竞品分析乱码
- **现象**: 竞品分析输出"收纳盒"等无意义内容
- **原因**: `prompts.py` 中 JSON 输出示例使用了单花括号 `{}`，Python `str.format()` 将其解析为占位符，引发 `KeyError → format_prompt` 降级返回未填充的原始模板 → LLM 收到混乱指令
- **解决**: 将单花括号改为双花括号 `{{}}` 转义
- **教训**: 凡是用 `.format()` 渲染的模板中，字面花括号必须用 `{{` `}}`

#### 🕳️ 坑 2：Ctrl+F5 刷新后首页按钮无响应
- **现象**: 硬刷新后点击"开始使用"按钮无反应，需手动点击导航栏后才正常
- **原因**: 浏览器恢复上一次 session 的 hash（如 `#analyze`），`location.hash` 不为空 → `if (!location.hash) location.hash = "home"` 不执行 → `navigate()` 从未被调用 → 所有 `page` 均为 `display:none`
- **解决**: 脚本末尾始终调用一次 `navigate()`，无论 hash 是否已设置
- **教训**: 路由初始化不能依赖 `hashchange` 事件，需主动调用导航函数

#### 🕳️ 坑 3：LLM 输出免责声明代替分析
- **现象**: 降级到 LLM 知识时输出"建议通过市场调研补充竞品信息"等空话
- **原因**: Prompt 约束中含"如果数据不足请如实说明"，LLM 照做
- **解决**: 改为"即使没有数据也必须完成分析并输出标准 JSON"，在 sources 区标注而非正文声明

---

### 技术要点
- **RAG 相关性阈值**: 0.45（`config.py` 中 `RAG_SCORE_THRESHOLD` 参数）
- **Embedding 模型**: BAAI/bge-small-zh-v1.5（本地 CPU），自动降级 OpenAI Compatible
- **流式传输**: FastAPI `StreamingResponse` + SSE 格式
- **JSON 容错**: 4 层降级解析（直接解析 → 代码块提取 → 花括号提取 → json_repair 修复）

### 回退方式
```bash
git reset --hard <commit-hash>
```
主要存档点：`26315d9`（最新导航修复）、`68acf6c`（综合报告）、`f9a9675`（SPA重构）、`7dcd840`（知识库扩展）、`9442d7c`（三项重大改动）、`bd79dc1`（初始项目）
