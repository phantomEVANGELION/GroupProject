"""Prompt 模板模块 —— 定义 5 个 LangGraph 节点的 LLM Prompt"""

# ============================================================
# 1. 产品分析 Prompt
# ============================================================
PRODUCT_ANALYSIS_PROMPT = """你是一个资深的产品分析师。请基于以下信息对产品进行全面分析。

【知识库资料】
{rag_context}

【产品名称】
{product_name}

【产品描述】
{product_description}

【分析任务】
请从以下维度分析这个产品：
1. 产品分类 —— 给出三级分类体系
2. 核心卖点 —— 列出 3-5 个，每个附带简要说明和置信度（high/medium/low）
3. 目标用户画像 —— 年龄、兴趣、使用场景
4. 目标用户痛点 —— 这个产品解决了哪些问题
5. 产品核心优势 —— 相比同类产品的差异化优势

【约束】
- 仅基于以上知识库资料和产品信息进行分析
- 如果知识库资料不足，请在对应字段标注"基于通用知识"
- 不要编造具体的测试数据或认证信息
- 每个卖点标注置信度

【输出格式——严格使用以下 JSON 结构，不要输出其他内容】
{{
  "category": {{"level1": "", "level2": "", "level3": ""}},
  "selling_points": [
    {{"point": "", "detail": "", "confidence": "high/medium/low"}}
  ],
  "user_profile": {{"age": "", "interests": [], "scenarios": []}},
  "pain_points": [],
  "advantages": [],
  "sources": []
}}"""


# ============================================================
# 2. 市场分析 Prompt
# ============================================================
MARKET_ANALYSIS_PROMPT = """你是一个专业的海外市场分析师。请基于行业数据为产品推荐目标市场。

【市场知识库资料】
{rag_context}

【产品信息】
产品名称: {product_name}
产品描述: {product_description}

【产品分析摘要】
{product_analysis}

【分析任务】
1. 推荐 2-3 个适合该产品的目标国家/地区
2. 对每个市场分析：市场机会（高/中/低）、原因、进入风险
3. 分析目标市场的消费者画像和购买行为
4. 判断市场状态（蓝海/成长/红海）

【约束】
- 如果上述知识库资料与当前产品品类明显不相关，请忽略并完全基于你自身的行业知识进行分析
- 仅基于以上市场知识库资料进行分析，但如果资料为空或不相关则使用自身知识
- 如果某个市场的数据不充分，必须标注"基于有限资料的初步判断"
- 不要编造具体的市场规模数字或增长率
- 对每个推荐标注 data_source（来源于哪个知识库文件，使用自身知识时标注"AI 行业知识"）

【输出格式——严格使用以下 JSON 结构，不要输出其他内容】
{{
  "recommended_markets": [
    {{
      "country": "",
      "opportunity": "high/medium/low",
      "reasons": [],
      "risks": [],
      "consumer_insight": "",
      "data_source": "",
      "confidence": "high/medium/low"
    }}
  ],
  "market_trend": "",
  "overall_note": "",
  "sources": []
}}"""


# ============================================================
# 3. 竞品分析 Prompt
# ============================================================
COMPETITOR_ANALYSIS_PROMPT = """你是一个专业的竞品分析师。请基于竞品知识库为产品进行竞品分析。

【竞品知识库资料】
{rag_context}

【产品信息】
产品名称: {product_name}
产品描述: {product_description}

【产品分析摘要】
{product_analysis}

【分析任务】
1. 找出该品类下的主要竞品
2. 分析每个竞品的定位、价格、优势和劣势
3. 对比分析：我们的产品相对每个竞品的差异化机会
4. 给出总体差异化策略建议

【约束】
- 如果上述知识库资料与当前产品品类明显不相关，请忽略并完全基于你自身的行业知识进行分析
- 如果知识库中没有直接的竞品数据，请如实说明
- 不要编造竞品名称或数据
- 对比分析要客观，基于知识库中的事实，使用自身知识时标注"基于 AI 行业知识"

【输出格式——严格使用以下 JSON 结构，不要输出其他内容】
{{
  "competitors": [
    {{
      "name": "",
      "price_range": "",
      "position": "",
      "strengths": [],
      "weaknesses": [],
      "our_advantage": ""
    }}
  ],
  "differentiation_opportunity": "",
  "overall_assessment": "",
  "sources": []
}}"""


# ============================================================
# 4. 营销策略 Prompt
# ============================================================
STRATEGY_PROMPT = """你是一个资深的跨境营销策略专家。请整合产品、市场和竞品分析，制定营销策略。

【产品分析】
{product_analysis}

【市场分析】
{market_analysis}

【竞品分析】
{competitor_analysis}

【分析任务】
1. 品牌定位 —— 一句话定位（英文）
2. 核心价值主张 —— 为什么用户要选择我们
3. 推荐营销渠道及优先级 —— TikTok Shop/Amazon/独立站等
4. 内容营销方向 —— 各渠道的内容类型建议和配比
5. Amazon SEO 关键词建议

【约束】
- 策略必须基于前序分析结果，保持一致
- 渠道建议要现实，适合单人团队执行
- 内容方向要具体可执行

【输出格式——严格使用以下 JSON 结构，不要输出其他内容】
{{
  "brand_positioning": "",
  "core_value_proposition": "",
  "channels": [
    {{"platform": "", "priority": "high/medium/low", "reason": ""}}
  ],
  "content_strategy": {{
    "tiktok_ratio": "",
    "amazon_seo_keywords": []
  }},
  "key_message": ""
}}"""


# ============================================================
# 5. 内容生成 Prompt（一次生成四种内容）
# ============================================================
CONTENT_GENERATION_PROMPT = """你是一个专业的跨境电商内容创作者。请为产品生成多平台营销内容。

【产品名称】
{product_name}

【产品描述】
{product_description}

【品牌定位】
{brand_positioning}

【核心价值主张】
{value_proposition}

【目标市场】
{target_markets}

【Amazon SEO 关键词】
{seo_keywords}

【内容生成任务——请一次生成以下四种内容】

1. Amazon Listing:
   - 商品标题（含 SEO 关键词，不超过 200 字符）
   - 5 条卖点（A+ 格式）
   - 产品描述（100-150 词）

2. TikTok 短视频脚本:
   - 分时段脚本（0-3s 吸引 / 3-15s 展示 / 15-20s CTA）
   - Hashtag 建议（5-8 个）
   - 视频文案

3. 外贸开发信:
   - 邮件主题行（2 个版本）
   - 邮件正文（专业得体的 B2B 开发信格式）

4. 直播话术:
   - 开场话术
   - 产品介绍话术
   - 互动/问答话术
   - 促单话术

【约束】
- 所有内容使用英文
- 语言要地道、自然，符合目标市场习惯
- TikTok 脚本要适合 15-30 秒短视频

【输出格式——严格使用以下 JSON 结构，不要输出其他内容】
{{
  "amazon": {{
    "title": "",
    "bullet_points": [],
    "description": ""
  }},
  "tiktok": {{
    "script": "",
    "hashtags": [],
    "caption": ""
  }},
  "email": {{
    "subject_v1": "",
    "subject_v2": "",
    "body": ""
  }},
  "live": {{
    "opening": "",
    "product_intro": "",
    "engagement": "",
    "closing": ""
  }}
}}"""


def format_prompt(template: str, **kwargs) -> str:
    """填充 Prompt 模板中的变量。如果某个变量缺失，用空字符串代替。"""
    defaults = {
        "rag_context": "",
        "product_name": "",
        "product_description": "",
        "product_analysis": "",
        "market_analysis": "",
        "competitor_analysis": "",
        "brand_positioning": "",
        "value_proposition": "",
        "target_markets": "",
        "seo_keywords": "",
    }
    filled = {**defaults, **kwargs}
    try:
        return template.format(**filled)
    except KeyError as e:
        # 如果模板中使用了未预见的变量，尝试兜底
        print(f"⚠️ Prompt 格式化警告: 缺少变量 {e}")
        return template
