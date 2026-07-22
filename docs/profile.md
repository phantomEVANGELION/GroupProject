# AI 跨境出海运营助手 - 项目摘要

> 用途: AI 助手的项目上下文，交代技术架构与关键文件

## 一句话

FastAPI + LangGraph + ChromaDB(RAG) + DeepSeek LLM 的跨境出海运营分析工具。输入产品信息，自动完成产品分析、市场洞察、竞品对比、营销策略、文案编写(中英双语)、综合报告(含物流) 6 步流水线。

## 技术栈

- 后端: FastAPI + Uvicorn
- 工作流: LangGraph StateGraph 6 节点 DAG (LangChain >= 0.2)
- 向量库: ChromaDB 本地持久化, 3 个 collection (market / competitor / product)
- Embedding: BAAI/bge-small-zh-v1.5 (本地 CPU 推理, ~33MB, 降级 OpenAI Compatible)
- LLM: DeepSeek deepseek-chat (OpenAI 兼容接口), 温度 0.3(分析) / 0.5(内容)
- 前端: 原生 HTML/CSS/JS SPA, Hash 路由 4 页面, 零框架依赖
- 流式: SSE /analyze-stream, fetch + ReadableStream 逐步骤渲染
- 文档解析: PyMuPDF / python-docx, 支持 PDF/DOCX/TXT/MD/JSON

## 工作流 (6 步)

每步模式: RAG 检索 -> Prompt 组装 -> LLM 调用 -> JSON 容错解析

1. product_node - 产品分类/卖点/用户画像/痛点 (检索 product_kb = 上传文件)
2. market_node - 目标市场推荐/规模/头部企业/认证/展会 (检索 market_kb, 相关性降级)
3. competitor_node - 竞品对比/差异化机会/改进建议 (检索 competitor_kb, 相关性降级)
4. strategy_node - 品牌定位/渠道推荐/内容策略 (聚合前 3 步, LLM 推理)
5. content_node - Amazon Listing/TikTok 脚本/开发信/直播话术 (中英双语)
6. comprehensive_node - 摘要/物流运输建议/综合建议 (检索物流知识库)

## RAG 降级

similarity_search_with_relevance_scores() 获取相关性分数, 阈值 0.45 (config.py 中 RAG_SCORE_THRESHOLD)。低于阈值判定品类不匹配, 跳过 RAG 数据, Prompt 改为"基于你自身的行业知识分析", 来源区灰色斜体标注。

## JSON 容错 (4 层)

LLM 输出解析: 直接 json.loads() -> ```json 代码块提取 -> 最外层 {} 提取 -> json_repair 自动修复。全部失败则文本降级。

## 知识库

9 大品类预置: 智能手表/小家电/服装/健身器材/玩具/美妆个护/宠物用品/汽车配件/手办潮玩。每品类含市场数据 MD 文件(美/欧市场规模/消费者/认证/展会/风险) + 竞品数据 JSON 文件(5 个竞品)。另有独立物流知识库 international_logistics.md。

## API 端点

| 端点 | 说明 |
|------|------|
| GET / | SPA 首页 |
| POST /upload | 文件上传, 返回路径列表 |
| POST /analyze | 同步分析 (向后兼容) |
| POST /analyze-stream | SSE 流式分析 (推荐) |
| GET /api/rates | 实时汇率, 30 分钟缓存, 13 种货币 |
| GET /api/rates/history | 近 12 月历史汇率 + 线性回归 7 日预测 |

## 文件结构

```
ai-export-demo/
  app.py                  - FastAPI 入口 + SPA 前端 (4 页面内嵌)
  app_format.py           - dict -> HTML 格式化
  config.py               - 全局配置 (API Key/阈值/路径)
  workflow/
    graph.py              - LangGraph 图定义
    state.py              - WorkflowState TypedDict
    nodes.py              - 6 节点函数 (核心业务)
  rag/
    chroma_client.py      - ChromaDB 管理 + Embedding 加载
    loader.py             - 文档加载器 (PDF/DOCX/TXT/MD/JSON)
    prompts.py            - Prompt 模板 + format_prompt()
  knowledge_base/
    market/               - 市场数据 (11 个 MD 文件)
    competitors/          - 竞品数据 (9 个 JSON 文件)
  init_knowledge_base.py  - 知识库初始化
  data/chroma_db/         - ChromaDB 持久化 (gitignored)
```

## 踩坑记录 (必读)

1. 模板花括号转义: .format() 中字面花括号必须用 {{}}, 否则 KeyError 降级返回未填充原始模板
2. SPA 路由初始化: 脚本末尾必须主动调用 navigate(), 不能依赖 hashchange 事件
3. LLM 免责声明: Prompt 不能写"如果数据不足请如实说明", 应改为"即使没有数据也必须输出标准 JSON"
4. Gradio 废弃: 原用 Gradio 因白屏无响应弃用, 改为 FastAPI + 纯前端 SPA
5. 标签页不可见: tabsSection 初始 className="tabs" (display:none), 需切换为 "tabs active"

## 运行方式

cd ai-export-demo && python app.py -> http://127.0.0.1:7860
首次启动自动下载 BGE Embedding 模型并初始化 ChromaDB。
