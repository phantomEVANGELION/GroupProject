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

    prompt = f"""你是一个跨境电商社交媒体运营专家。请为以下产品生成推广帖子。

【当前推广产品】
{product_name or "智能运动手表"}

【店铺信息】
{context if context.strip() else "暂无详细店铺信息，请基于产品名称和通用知识生成。"}

店铺产品信息：
{context}

【强制要求 - 必须严格执行】
1. **X (Twitter)**：字数 ≤ 280 字符（中文约 40-60 字），**纯文字**，不加 emoji，像新闻快讯/产品公告，用短句和感叹号。必须包含 3-4 个话题标签。
   示例风格："X100智能手表发布！7天续航，AMOLED屏幕，IP68防水。运动数据精准，健康监测全面。适合所有健身爱好者。#SmartWatch #FitnessTech"

2. **Facebook**：字数 150-250 字（中文），**必须加 emoji**，像品牌故事/软文推荐，有开头、中间、结尾三段式结构。有号召性语言（如"点击链接"、"立即购买"）。
   示例风格："🏃 跑步爱好者看过来！我们花了两年时间打造的 X100 智能手表，终于来了。它不仅仅是一块手表，更是你运动路上的私人教练。精准的 GPS 定位，7天超长续航，让你一次充电跑遍全城。无论是晨跑还是夜跑，IP68 防水都能应对。现在下单，还有专属优惠等着你！点击下方链接了解更多吧！👇"

3. **Instagram**：字数 80-120 字（中文），**必须加 emoji**，像视觉种草文案，强调生活方式、画面感、感受。使用 5-8 个话题标签。
   示例风格："✨ 戴上 X100，感受每一公里的心跳。🏃‍♂️ 从晨光到夜色，它记录的不只是运动数据，更是我坚持的每一步。❤️ 轻巧、防水、续航超长，简直是我的完美搭档！你也想要这样的运动伙伴吗？ #WearableTech #RunningLife"

【输出格式】
{{
  "x_post": "（X/Twitter 帖子，纯文字，不加emoji，含话题标签）",
  "facebook_post": "（Facebook 帖子，加emoji，150-250字，故事结构）",
  "instagram_post": "（Instagram 帖子，加emoji，80-120字，种草风格）",
  "hashtags": ["#通用标签1", "#通用标签2"],
  "best_platform": "x/facebook/instagram",
  "reasoning": "选择该平台的原因"
}}

⚠️ 重要提醒：三篇内容绝对不能一样！每篇从不同角度切入，字数、语气、结构都要有明显差异。X 偏硬核公告，Facebook 偏品牌故事，Instagram 偏视觉种草。"""
    
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
