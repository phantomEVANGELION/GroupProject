"""AI 客服 Agent"""

import random
import config
from langchain_openai import ChatOpenAI
from rag.chroma_client import similarity_search

COLLECTION_STORE = "store_kb"


def fetch_sales_data() -> dict:
    """
    获取当前销量数据。
    真实场景: 调用 Amazon SP-API / Shopify Admin API
    TODO: 接入真实 API 时替换此函数内容
    """
    return {
        "today_revenue": random.randint(500, 3000),
        "today_orders": random.randint(5, 50),
        "monthly_revenue": random.randint(15000, 80000),
        "pending_messages": random.randint(1, 8),
        "currency": "USD",
    }


def fetch_customer_queues() -> list[dict]:
    """获取正在排队的顾客消息列表（模拟）"""
    customers = [
        {
            "id": "c001",
            "name": "张三",
            "status": "online",
            "last_message": "你好，请问这款手表支持iOS吗？",
            "time": "2分钟前",
            "product": "X100 智能运动手表",
        },
        {
            "id": "c002",
            "name": "Alice",
            "status": "offline",
            "last_message": "Does this watch support GPS?",
            "time": "15分钟前",
            "product": "X100 Pro",
        },
        {
            "id": "c003",
            "name": "John",
            "status": "online",
            "last_message": "Do you have a discount for bulk orders?",
            "time": "刚刚",
            "product": "X100 Mini",
        },
    ]
    return customers


def generate_reply(customer_message: str, product_context: str = "") -> str:
    """基于产品知识库自动生成客服回复"""
    try:
        docs = similarity_search(COLLECTION_STORE, product_context or customer_message, k=3)
        context = "\n".join([doc.page_content for doc in docs])
    except Exception:
        context = ""

    llm = ChatOpenAI(
        model=config.LLM_MODEL_NAME,
        temperature=0.3,
        openai_api_key=config.DEEPSEEK_API_KEY,
        openai_api_base=config.DEEPSEEK_API_BASE,
        timeout=config.LLM_TIMEOUT,
    )

    prompt = f"""你是一个跨境电商客服，需要回复顾客的咨询。

店铺产品信息：
{context}

顾客消息：{customer_message}

要求：
1. 回复要礼貌、专业
2. 基于产品实际情况回答
3. 如果不确定，请引导顾客联系人工客服
4. 回复使用顾客消息的相同语言
5. 不要承诺无法保证的事情（如具体物流时间）

回复："""

    try:
        result = llm.invoke(prompt)
        return result.content
    except Exception:
        return "您好，感谢您的咨询！我会尽快为您查询相关信息，稍后给您回复。如有紧急需求，请联系我们的在线客服。"
