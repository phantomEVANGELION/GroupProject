"""AI 营销发帖 Agent"""

import json
import os
import re
from datetime import datetime
from langchain_openai import ChatOpenAI
import config
from rag.chroma_client import similarity_search

COLLECTION_STORE = "store_kb"
PUBLISH_LOG_PATH = os.path.join(config.BASE_DIR, "data", "publish_log.jsonl")


def _log_publish(platform: str, content: str, status: str):
    """记录发布行为到日志文件"""
    os.makedirs(os.path.dirname(PUBLISH_LOG_PATH), exist_ok=True)
    entry = {
        "platform": platform,
        "content": content[:200],
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }
    with open(PUBLISH_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _safe_parse_json(text: str) -> dict:
    """简单的 JSON 容错解析"""
    text = text.strip()
    try:
        return json.loads(text)
    except:
        pass
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    return {}


def generate_post(product_name: str = "") -> dict:
    """基于店铺产品信息生成社交媒体帖子"""
    try:
        docs = similarity_search(COLLECTION_STORE, product_name or "推广 产品", k=5)
        context = "\n".join([doc.page_content for doc in docs])
    except Exception:
        context = "（暂无产品信息）"

    llm = ChatOpenAI(
        model=config.LLM_MODEL_NAME,
        temperature=0.5,
        openai_api_key=config.DEEPSEEK_API_KEY,
        openai_api_base=config.DEEPSEEK_API_BASE,
        timeout=config.LLM_TIMEOUT,
    )

    prompt = f"""你是一个跨境电商社交媒体运营，需要为产品生成推广帖子。

店铺产品信息：
{context}

请生成以下内容（用 JSON 格式返回）：
1. x_post: X/Twitter 风格的帖子（≤280字符，带话题标签）
2. facebook_post: Facebook 风格的帖子（较长，可带 emoji，带产品链接描述）
3. instagram_post: Instagram 风格的帖子（简短，视觉化描述，带话题标签）
4. hashtags: 推荐的话题标签列表（5-8个）
5. best_platform: 最适合首发此帖的平台（x/facebook/instagram）
6. reasoning: 选择该平台的原因

{{
  "x_post": "",
  "facebook_post": "",
  "instagram_post": "",
  "hashtags": [],
  "best_platform": "",
  "reasoning": ""
}}"""

    try:
        result = llm.invoke(prompt).content
        parsed = _safe_parse_json(result)
        if parsed:
            return parsed
    except Exception:
        pass

    return {
        "x_post": f"Discover the future of wearable tech! {product_name or 'Our latest product'} is here. #TechWear",
        "facebook_post": f"We are excited to announce {product_name or 'our new product'}! Check it out now.",
        "instagram_post": f"The future is wearable. ✨ #{product_name.replace(' ', '') if product_name else 'NewProduct'}",
        "hashtags": ["#TechWear", "#SmartWatch", "#WearableTech"],
        "best_platform": "x",
        "reasoning": "Generate failed, using defaults.",
    }


def publish(platform: str, content: str) -> dict:
    """
    发布内容到指定社交平台。
    真实场景: 调用各平台 API
    TODO: 接入真实 API 时替换
    """
    platform_map = {
        "x": "X (Twitter)",
        "facebook": "Facebook",
        "instagram": "Instagram",
    }
    platform_name = platform_map.get(platform, platform)

    if config.ENABLE_SOCIAL_PUBLISH:
        _log_publish(platform, content, "published")
        return {"status": "published", "platform": platform_name, "message": f"已发布到 {platform_name}"}
    else:
        _log_publish(platform, content, "simulated")
        return {"status": "simulated", "platform": platform_name, "message": f"✅ 模拟发布到 {platform_name}（配置开启后执行真实发布）"}
