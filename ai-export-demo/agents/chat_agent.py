"""AI 聊天 Agent"""

import json
import os
from typing import Optional
from langchain_openai import ChatOpenAI
import config
from rag.chroma_client import similarity_search

COLLECTION_STORE = "store_kb"


def _get_llm():
    return ChatOpenAI(
        model=config.LLM_MODEL_NAME,
        temperature=0.5,
        openai_api_key=config.DEEPSEEK_API_KEY,
        openai_api_base=config.DEEPSEEK_API_BASE,
        timeout=config.LLM_TIMEOUT,
    )


def _build_system_prompt() -> str:
    """从 store_kb 检索店铺信息，构建 system prompt"""
    try:
        docs = similarity_search(COLLECTION_STORE, "店铺产品 公司信息", k=5)
        context = "\n".join([doc.page_content for doc in docs])
    except Exception:
        context = "（暂无店铺配置信息）"

    return f"""你是一个跨境电商运营助手，帮助卖家分析产品、制定策略、优化销售。

当前店铺信息：
{context}

你可以回答关于产品、市场、定价、营销、物流等方面的问题。
如果用户问的问题你不确定，请如实说"建议进一步分析"，不要编造数据。
回答要简洁、具体、可操作。"""


def chat(message: str, history: list[dict] = None) -> str:
    """处理聊天消息，返回 AI 回复"""
    llm = _get_llm()
    system_prompt = _build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-10:])  # 保留最近 10 轮
    messages.append({"role": "user", "content": message})

    try:
        result = llm.invoke(messages)
        return result.content
    except Exception as e:
        return f"（AI 回复失败: {e}）"
