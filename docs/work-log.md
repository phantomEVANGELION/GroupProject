---
name: work-log
description: AI 跨境出海运营助手 Demo 开发工作日志
metadata:
  type: project
---

# 开发工作日志

## 存档点：b7f10d9（当前最新）

### 项目概况
AI 跨境出海运营助手 Demo — FastAPI + LangGraph + RAG(ChromaDB) + DeepSeek LLM
面向中小制造企业出海场景，实现产品分析到营销内容生成的完整闭环。

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

### 技术要点
- **RAG 相关性阈值**: 0.45（`config.py` 中 `RAG_SCORE_THRESHOLD` 参数）
- **Embedding 模型**: BAAI/bge-small-zh-v1.5（本地 CPU），自动降级 OpenAI Compatible
- **流式传输**: FastAPI `StreamingResponse` + SSE 格式
- **JSON 容错**: 4 层降级解析（直接解析 → 代码块提取 → 花括号提取 → json_repair 修复）

### 回退方式
```bash
git reset --hard <commit-hash>
```
主要存档点：`b7f10d9`（最新）、`7dcd840`（知识库扩展）、`9442d7c`（三项重大改动）、`bd79dc1`（初始项目）
