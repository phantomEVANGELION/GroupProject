"""Workflow 节点函数 —— 5 个节点的具体实现

每个 node 的签名统一：
    node_func(state: WorkflowState) -> WorkflowState

约定：
- 节点处理完后返回更新后的 state
- 异常被捕获后写入 state["errors"]，不影响后续节点执行
- JSON 解析失败时有容错降级
"""

import json
import os
import re
import traceback
from typing import Optional

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

import config
from rag.chroma_client import (
    add_documents,
    similarity_search,
    similarity_search_with_relevance_scores,
    get_collection_count,
    reset_collection,
)
from rag.loader import load_document, split_documents
from rag.prompts import (
    PRODUCT_ANALYSIS_PROMPT,
    MARKET_ANALYSIS_PROMPT,
    COMPETITOR_ANALYSIS_PROMPT,
    STRATEGY_PROMPT,
    CONTENT_GENERATION_PROMPT,
    format_prompt,
)
from workflow.state import WorkflowState


# ========== LLM 调用工具 ==========

def _get_llm(temperature: float = 0.3) -> ChatOpenAI:
    """获取 DeepSeek 驱动的 LLM 实例"""
    return ChatOpenAI(
        model=config.LLM_MODEL_NAME,
        temperature=temperature,
        openai_api_key=config.DEEPSEEK_API_KEY,
        openai_api_base=config.DEEPSEEK_API_BASE,
        timeout=config.LLM_TIMEOUT,
    )


def _call_llm(prompt: str, temperature: float = 0.3) -> str:
    """调用 LLM 并返回原始文本内容"""
    llm = _get_llm(temperature=temperature)
    response = llm.invoke(prompt)
    return response.content


def _safe_parse_json(text: str) -> tuple[Optional[dict], str]:
    """多层 JSON 解析容错。

    返回:
        (parsed_dict, raw_text)
    解析失败时 parsed_dict 为 None，raw_text 保留供降级展示。
    """
    # 第 1 层：直接解析
    text = text.strip()
    try:
        return json.loads(text), text
    except json.JSONDecodeError:
        pass

    # 第 2 层：提取 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate), candidate
        except json.JSONDecodeError:
            pass

    # 第 3 层：提取最外层的 { ... }（处理 AI 可能在前后加了解释文字的情况）
    brace_match = re.search(r'(\{[\s\S]*\})', text)
    if brace_match:
        candidate = brace_match.group(1).strip()
        try:
            return json.loads(candidate), candidate
        except json.JSONDecodeError:
            pass

    # 第 4 层：json_repair 修复
    try:
        from json_repair import repair_json
        fixed = repair_json(text)
        return json.loads(fixed), text
    except Exception:
        pass

    # 全部失败，返回 None
    return None, text


def _collect_sources(docs: list[Document]) -> list[str]:
    """从检索结果中提取唯一的源文件名"""
    seen = set()
    sources = []
    for doc in docs:
        src = doc.metadata.get("source", "未知来源")
        if src not in seen:
            seen.add(src)
            sources.append(src)
    return sources


# ============================================================
# 节点 1：产品分析（Product Analysis）
# ============================================================
def product_node(state: WorkflowState) -> WorkflowState:
    """产品分析节点。

    1. 如果有上传文件，加载 → 切分 → 存入 product_kb
    2. 从 product_kb 检索产品相关信息
    3. LLM 分析：分类、卖点、用户画像、痛点
    4. 更新 state
    """
    product_name = state.get("product_name", "")
    product_description = state.get("product_description", "")
    uploaded_files = state.get("uploaded_files", [])

    if not product_name:
        state["errors"].append("product_node: 缺少产品名称")

    # ---- 1. 处理上传文件 ----
    all_chunks: list[Document] = []

    # 清空 product_kb，防止旧数据干扰（只在有文件时执行一次）
    if uploaded_files:
        try:
            reset_collection(config.COLLECTION_PRODUCT)
        except Exception as e:
            state["errors"].append(f"product_node: 重置知识库失败: {e}")

    for file_path in uploaded_files:
        if not os.path.exists(file_path):
            state["errors"].append(f"product_node: 文件不存在 {file_path}")
            continue
        try:
            chunks = load_document(file_path)
            split_chunks = split_documents(chunks)
            all_chunks.extend(split_chunks)
        except Exception as e:
            state["errors"].append(f"product_node: 文件处理失败 {os.path.basename(file_path)}: {e}")

    # 如果有文件 chunk，存入 ChromaDB
    sources_from_files = []
    if all_chunks:
        try:
            add_documents(config.COLLECTION_PRODUCT, all_chunks)
            sources_from_files = _collect_sources(all_chunks)
        except Exception as e:
            state["errors"].append(f"product_node: ChromaDB 写入失败: {e}")

    # ---- 2. 从 product_kb 检索 ----
    rag_docs: list[Document] = []
    try:
        query = f"{product_name} {product_description[:200]}"
        rag_docs = similarity_search(config.COLLECTION_PRODUCT, query, k=config.RAG_TOP_K)
    except Exception as e:
        state["errors"].append(f"product_node: 检索失败: {e}")

    # ---- 3. 准备 RAG 上下文 ----
    rag_context = ""
    for i, doc in enumerate(rag_docs):
        src = doc.metadata.get("source", "未知")
        rag_context += f"[片段 {i+1}] (来源: {src})\n{doc.page_content}\n\n"

    if not rag_context.strip():
        rag_context = "（用户未上传产品资料，请基于产品名称和描述进行分析）"

    # 合并来源
    all_sources = sources_from_files + _collect_sources(rag_docs)
    all_sources = list(dict.fromkeys(all_sources))  # 去重保持顺序

    # ---- 4. 调用 LLM ----
    prompt = format_prompt(
        PRODUCT_ANALYSIS_PROMPT,
        rag_context=rag_context,
        product_name=product_name,
        product_description=product_description,
    )

    try:
        raw_output = _call_llm(prompt, temperature=config.LLM_TEMPERATURE_ANALYSIS)
        parsed, raw = _safe_parse_json(raw_output)

        if parsed:
            # 注入 sources
            if "sources" not in parsed or not parsed["sources"]:
                parsed["sources"] = all_sources
            state["product_analysis"] = parsed
        else:
            state["errors"].append("product_node: JSON 解析失败，使用文本降级")
            state["product_analysis"] = {
                "category": {"level1": "", "level2": "", "level3": ""},
                "selling_points": [{"point": "（JSON 解析失败）", "detail": raw[:200], "confidence": "low"}],
                "user_profile": {},
                "pain_points": [],
                "advantages": [],
                "sources": all_sources,
                "_raw_fallback": True,
            }
    except Exception as e:
        state["errors"].append(f"product_node: LLM 调用失败: {e}")
        state["product_analysis"] = {
            "category": {"level1": "", "level2": "分析失败", "level3": ""},
            "selling_points": [],
            "user_profile": {},
            "pain_points": [],
            "advantages": [],
            "sources": all_sources,
        }

    state["product_sources"] = all_sources
    return state


# ============================================================
# 节点 2：市场分析（Market Analysis）
# ============================================================
def market_node(state: WorkflowState) -> WorkflowState:
    """市场分析节点。

    1. 从 market_kb 检索品类相关市场数据
    2. 通过相关性分数判断数据是否与产品品类匹配
    3. 不匹配时降级到 LLM 内置知识
    4. LLM 分析：推荐目标国家、市场机会、风险
    """
    product_name = state.get("product_name", "")
    product_analysis = state.get("product_analysis", {}) or {}

    # 从产品分析中提取品类信息用于检索
    category = product_analysis.get("category", {})
    level2 = category.get("level2", "") if isinstance(category, dict) else ""
    level1 = category.get("level1", "") if isinstance(category, dict) else ""

    # ---- 1. 检索市场知识库（带相关性分数） ----
    rag_docs: list[Document] = []
    rag_scores: list[float] = []
    try:
        query = f"{level1} {level2} {product_name} 市场分析 出口"
        docs_with_scores = similarity_search_with_relevance_scores(
            config.COLLECTION_MARKET, query, k=config.RAG_TOP_K
        )

        if len(docs_with_scores) < 2:
            docs_with_scores = similarity_search_with_relevance_scores(
                config.COLLECTION_MARKET, f"{product_name} 海外市场", k=config.RAG_TOP_K
            )

        rag_docs = [d for d, _ in docs_with_scores]
        rag_scores = [s for _, s in docs_with_scores]
    except Exception as e:
        state["errors"].append(f"market_node: 检索失败: {e}")

    # ---- 2. 判断检索结果是否匹配品类 ----
    max_score = max(rag_scores) if rag_scores else 0.0
    is_relevant = max_score >= config.RAG_SCORE_THRESHOLD if rag_docs else False

    # ---- 3. 准备 RAG 上下文 ----
    if is_relevant:
        rag_context = ""
        for i, doc in enumerate(rag_docs):
            src = doc.metadata.get("source", "未知")
            rag_context += f"[片段 {i+1}] (来源: {src})\n{doc.page_content}\n\n"
        sources = _collect_sources(rag_docs)
    else:
        rag_context = (
            "（本地知识库中暂无该品类的市场数据。请完全基于你自身的行业知识进行分析，\n"
            "覆盖目标市场推荐、消费者洞察、市场趋势等维度。\n"
            "对于每项结论，请标注可信度：高/中/低。不要编造具体数据。）"
        )
        sources = ["AI 行业知识（本地知识库暂无该品类数据）"]

    # ---- 3. 调用 LLM ----
    product_analysis_str = json.dumps(product_analysis, ensure_ascii=False, indent=2)
    prompt = format_prompt(
        MARKET_ANALYSIS_PROMPT,
        rag_context=rag_context,
        product_name=product_name,
        product_description=state.get("product_description", ""),
        product_analysis=product_analysis_str,
    )

    try:
        raw_output = _call_llm(prompt, temperature=config.LLM_TEMPERATURE_ANALYSIS)
        parsed, raw = _safe_parse_json(raw_output)

        if parsed:
            if "sources" not in parsed or not parsed["sources"]:
                parsed["sources"] = sources
            state["market_analysis"] = parsed
        else:
            state["errors"].append("market_node: JSON 解析失败，使用文本降级")
            state["market_analysis"] = {
                "recommended_markets": [],
                "market_trend": "分析失败",
                "overall_note": raw[:300],
                "sources": sources,
            }
    except Exception as e:
        state["errors"].append(f"market_node: LLM 调用失败: {e}")
        state["market_analysis"] = {
            "recommended_markets": [],
            "market_trend": "分析失败",
            "overall_note": str(e),
            "sources": sources,
        }

    state["market_sources"] = sources
    return state


# ============================================================
# 节点 3：竞品分析（Competitor Analysis）
# ============================================================
def competitor_node(state: WorkflowState) -> WorkflowState:
    """竞品分析节点。

    1. 从 competitor_kb 检索品类对应竞品数据
    2. 通过相关性分数判断数据是否与产品品类匹配
    3. 不匹配时降级到 LLM 内置知识
    4. LLM 对比分析：竞品定位、优劣势、差异化机会
    """
    product_name = state.get("product_name", "")
    product_analysis = state.get("product_analysis", {}) or {}

    category = product_analysis.get("category", {})
    level2 = category.get("level2", "") if isinstance(category, dict) else ""
    level1 = category.get("level1", "") if isinstance(category, dict) else ""

    # ---- 1. 检索竞品知识库（带相关性分数） ----
    rag_docs: list[Document] = []
    rag_scores: list[float] = []
    try:
        query = f"{level1} {level2} {product_name} 竞品"
        docs_with_scores = similarity_search_with_relevance_scores(
            config.COLLECTION_COMPETITOR, query, k=config.RAG_TOP_K
        )

        if len(docs_with_scores) < 2:
            docs_with_scores = similarity_search_with_relevance_scores(
                config.COLLECTION_COMPETITOR, f"{product_name} 竞品对比", k=config.RAG_TOP_K
            )

        rag_docs = [d for d, _ in docs_with_scores]
        rag_scores = [s for _, s in docs_with_scores]
    except Exception as e:
        state["errors"].append(f"competitor_node: 检索失败: {e}")

    # ---- 2. 判断检索结果是否匹配品类 ----
    max_score = max(rag_scores) if rag_scores else 0.0
    is_relevant = max_score >= config.RAG_SCORE_THRESHOLD if rag_docs else False

    # ---- 3. 准备 RAG 上下文 ----
    if is_relevant:
        rag_context = ""
        for i, doc in enumerate(rag_docs):
            src = doc.metadata.get("source", "未知")
            rag_context += f"[片段 {i+1}] (来源: {src})\n{doc.page_content}\n\n"
        sources = _collect_sources(rag_docs)
    else:
        rag_context = (
            "（本地知识库中暂无该品类的竞品数据。请完全基于你自身的行业知识进行分析，\n"
            "覆盖该品类的主要品牌、价格区间、定位、优势和劣势等维度。\n"
            "对于每项结论，请标注可信度：高/中/低。不要编造不存在的品牌或数据。）"
        )
        sources = ["AI 行业知识（本地知识库暂无该品类数据）"]

    # ---- 3. 调用 LLM ----
    product_analysis_str = json.dumps(product_analysis, ensure_ascii=False, indent=2)
    prompt = format_prompt(
        COMPETITOR_ANALYSIS_PROMPT,
        rag_context=rag_context,
        product_name=product_name,
        product_description=state.get("product_description", ""),
        product_analysis=product_analysis_str,
    )

    try:
        raw_output = _call_llm(prompt, temperature=config.LLM_TEMPERATURE_ANALYSIS)
        parsed, raw = _safe_parse_json(raw_output)

        if parsed:
            if "sources" not in parsed or not parsed["sources"]:
                parsed["sources"] = sources
            state["competitor_analysis"] = parsed
        else:
            state["errors"].append("competitor_node: JSON 解析失败，使用文本降级")
            state["competitor_analysis"] = {
                "competitors": [],
                "differentiation_opportunity": "分析失败",
                "overall_assessment": raw[:300],
                "sources": sources,
            }
    except Exception as e:
        state["errors"].append(f"competitor_node: LLM 调用失败: {e}")
        state["competitor_analysis"] = {
            "competitors": [],
            "differentiation_opportunity": "分析失败",
            "overall_assessment": str(e),
            "sources": sources,
        }

    state["competitor_sources"] = sources
    return state


# ============================================================
# 节点 4：营销策略（Strategy）
# ============================================================
def strategy_node(state: WorkflowState) -> WorkflowState:
    """营销策略节点。

    聚合产品、市场、竞品分析结果，LLM 制定营销策略。
    本节点不检索 RAG，仅做聚合推理。
    """
    product_analysis = state.get("product_analysis", {}) or {}
    market_analysis = state.get("market_analysis", {}) or {}
    competitor_analysis = state.get("competitor_analysis", {}) or {}

    prompt = format_prompt(
        STRATEGY_PROMPT,
        product_analysis=json.dumps(product_analysis, ensure_ascii=False, indent=2),
        market_analysis=json.dumps(market_analysis, ensure_ascii=False, indent=2),
        competitor_analysis=json.dumps(competitor_analysis, ensure_ascii=False, indent=2),
    )

    try:
        raw_output = _call_llm(prompt, temperature=config.LLM_TEMPERATURE_ANALYSIS)
        parsed, raw = _safe_parse_json(raw_output)

        if parsed:
            state["strategy"] = parsed
        else:
            state["errors"].append("strategy_node: JSON 解析失败，使用文本降级")
            state["strategy"] = {
                "brand_positioning": "",
                "core_value_proposition": "",
                "channels": [],
                "content_strategy": {},
                "key_message": raw[:300],
            }
    except Exception as e:
        state["errors"].append(f"strategy_node: LLM 调用失败: {e}")
        state["strategy"] = {
            "brand_positioning": "分析失败",
            "core_value_proposition": str(e),
            "channels": [],
            "content_strategy": {},
            "key_message": "",
        }

    return state


# ============================================================
# 节点 5：内容生成（Content Generation）
# ============================================================
def content_node(state: WorkflowState) -> WorkflowState:
    """内容生成节点。

    一次 LLM 调用生成四种内容：
    - Amazon Listing
    - TikTok 脚本
    - 开发信（Email）
    - 直播话术（Live）
    """
    strategy = state.get("strategy", {}) or {}

    brand_positioning = strategy.get("brand_positioning", "")
    value_proposition = strategy.get("core_value_proposition", "")
    channels = strategy.get("channels", [])
    content_strategy = strategy.get("content_strategy", {})

    # 提取目标市场
    market_analysis = state.get("market_analysis", {}) or {}
    markets = market_analysis.get("recommended_markets", [])
    target_markets = ", ".join([m.get("country", "") for m in markets if isinstance(m, dict)])

    # 提取 SEO 关键词
    seo_keywords = ""
    if isinstance(content_strategy, dict):
        keywords = content_strategy.get("amazon_seo_keywords", [])
        if isinstance(keywords, list):
            seo_keywords = ", ".join(keywords)

    prompt = format_prompt(
        CONTENT_GENERATION_PROMPT,
        product_name=state.get("product_name", ""),
        product_description=state.get("product_description", ""),
        brand_positioning=brand_positioning,
        value_proposition=value_proposition,
        target_markets=target_markets or "美国市场",
        seo_keywords=seo_keywords or "smart watch, fitness tracker",
    )

    try:
        raw_output = _call_llm(prompt, temperature=config.LLM_TEMPERATURE_CONTENT)
        parsed, raw = _safe_parse_json(raw_output)

        if parsed:
            state["contents"] = parsed
        else:
            state["errors"].append("content_node: JSON 解析失败，使用文本降级")
            state["contents"] = {
                "amazon": {"title": "", "bullet_points": [], "description": raw[:500]},
                "tiktok": {"script": "", "hashtags": [], "caption": ""},
                "email": {"subject_v1": "", "subject_v2": "", "body": ""},
                "live": {"opening": "", "product_intro": "", "engagement": "", "closing": ""},
            }
    except Exception as e:
        state["errors"].append(f"content_node: LLM 调用失败: {e}")
        state["contents"] = {
            "amazon": {"title": "内容生成失败", "bullet_points": [], "description": str(e)},
            "tiktok": {"script": "", "hashtags": [], "caption": ""},
            "email": {"subject_v1": "", "subject_v2": "", "body": ""},
            "live": {"opening": "", "product_intro": "", "engagement": "", "closing": ""},
        }

    return state
