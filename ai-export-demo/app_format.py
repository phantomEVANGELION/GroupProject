"""结果格式化函数 —— 将 Workflow 输出的 dict 转为 Markdown 字符串"""

import json


def _sources_footer(sources: list) -> str:
    if not sources:
        return ""
    src_str = "、".join(sources)
    return f"\n\n---\n📎 **数据来源**: {src_str}"


def format_product(state: dict) -> str:
    pa = state.get("product_analysis")
    if not pa:
        return ""

    md = ""
    cat = pa.get("category", {})
    if isinstance(cat, dict):
        levels = [cat.get(k, "") for k in ("level1", "level2", "level3")]
        levels = [l for l in levels if l]
        if levels:
            md += f"### 产品分类\n\n**{'  →  '.join(levels)}**\n\n"

    points = pa.get("selling_points", [])
    if points:
        md += "### 核心卖点\n\n"
        for p in points:
            if isinstance(p, dict):
                conf = p.get("confidence", "medium")
                icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
                md += f"- **{p.get('point', '')}** {icon}\n"
                detail = p.get("detail", "")
                if detail:
                    md += f"  - {detail}\n"
        md += "\n"

    profile = pa.get("user_profile", {})
    if isinstance(profile, dict) and any(profile.values()):
        md += "### 目标用户画像\n\n"
        age = profile.get("age", "")
        if age:
            md += f"- **年龄**: {age}\n"
        interests = profile.get("interests", [])
        if interests:
            md += f"- **兴趣**: {'、'.join(interests)}\n"
        scenarios = profile.get("scenarios", [])
        if scenarios:
            md += f"- **使用场景**: {'、'.join(scenarios)}\n"
        md += "\n"

    pains = pa.get("pain_points", [])
    if pains:
        md += "### 用户痛点\n\n"
        for p in pains:
            md += f"- {p}\n"
        md += "\n"

    advs = pa.get("advantages", [])
    if advs:
        md += "### 产品核心优势\n\n"
        for a in advs:
            md += f"- {a}\n"
        md += "\n"

    sources = pa.get("sources", state.get("product_sources", []))
    md += _sources_footer(sources)
    return md or "（分析结果为空）"


def format_market(state: dict) -> str:
    ma = state.get("market_analysis")
    if not ma:
        return ""

    md = ""
    note = ma.get("overall_note", "")
    if note:
        md += f"> {note}\n\n"

    markets = ma.get("recommended_markets", [])
    if markets:
        md += "### 推荐目标市场\n\n"
        for m in markets:
            if not isinstance(m, dict):
                continue
            country = m.get("country", "未知")
            opp = m.get("opportunity", "medium")
            opp_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(opp, "⚪")
            conf = m.get("confidence", "")
            conf_tag = f" (置信度: {conf})" if conf else ""
            md += f"#### {opp_icon} {country}{conf_tag}\n\n"

            reasons = m.get("reasons", [])
            if reasons:
                md += "**推荐原因:**\n" + "\n".join(f"- {r}" for r in reasons) + "\n\n"
            risks = m.get("risks", [])
            if risks:
                md += "**进入风险:**\n" + "\n".join(f"- {r}" for r in risks) + "\n\n"
            insight = m.get("consumer_insight", "")
            if insight:
                md += f"**消费者洞察:** {insight}\n\n"
            ds = m.get("data_source", "")
            if ds:
                md += f"*数据来源: {ds}*\n\n"

    trend = ma.get("market_trend", "")
    if trend:
        md += f"### 市场判断\n\n**{trend}**\n\n"

    sources = ma.get("sources", state.get("market_sources", []))
    md += _sources_footer(sources)
    return md or "（分析结果为空）"


def format_competitor(state: dict) -> str:
    ca = state.get("competitor_analysis")
    if not ca:
        return ""

    md = ""
    assessment = ca.get("overall_assessment", "")
    if assessment:
        md += f"> {assessment}\n\n"

    competitors = ca.get("competitors", [])
    if competitors:
        md += "### 竞品对比\n\n"
        md += "| 竞品 | 价格区间 | 定位 | 优势 | 劣势 | 我们的机会 |\n"
        md += "|------|---------|------|------|------|-----------|\n"
        for c in competitors:
            if not isinstance(c, dict):
                continue
            md += f"| {c.get('name','未知')} "
            md += f"| {c.get('price_range','-')} "
            md += f"| {c.get('position','-')} "
            md += f"| {'、'.join(c.get('strengths',[]))[:60]} "
            md += f"| {'、'.join(c.get('weaknesses',[]))[:60]} "
            md += f"| {c.get('our_advantage','-')[:60]} |\n"
        md += "\n"

    diff = ca.get("differentiation_opportunity", "")
    if diff:
        md += f"### 差异化机会\n\n**{diff}**\n\n"

    sources = ca.get("sources", state.get("competitor_sources", []))
    md += _sources_footer(sources)
    return md or "（分析结果为空）"


def format_strategy(state: dict) -> str:
    st = state.get("strategy")
    if not st:
        return ""

    md = ""
    positioning = st.get("brand_positioning", "")
    if positioning:
        md += f"### 品牌定位\n\n**{positioning}**\n\n"

    vp = st.get("core_value_proposition", "")
    if vp:
        md += f"### 核心价值主张\n\n{vp}\n\n"

    km = st.get("key_message", "")
    if km:
        md += f"### 关键传播信息\n\n{km}\n\n"

    channels = st.get("channels", [])
    if channels:
        md += "### 推荐营销渠道\n\n"
        md += "| 平台 | 优先级 | 理由 |\n"
        md += "|------|--------|------|\n"
        for ch in channels:
            if not isinstance(ch, dict):
                continue
            pri = ch.get("priority", "medium")
            pri_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(pri, "⚪")
            md += f"| {pri_icon} {ch.get('platform','未知')} | {pri} | {ch.get('reason','-')} |\n"
        md += "\n"

    cs = st.get("content_strategy", {})
    if isinstance(cs, dict) and cs:
        md += "### 内容策略\n\n"
        ratio = cs.get("tiktok_ratio", "")
        if ratio:
            md += f"- **TikTok 内容配比**: {ratio}\n"
        keywords = cs.get("amazon_seo_keywords", [])
        if keywords:
            md += f"- **Amazon SEO 关键词**: {'、'.join(keywords)}\n"
        md += "\n"

    return md or "（策略结果为空）"


def format_content_section(state: dict, section: str) -> str:
    contents = state.get("contents", {})
    if not contents:
        return ""

    data = contents.get(section, {})
    if not data:
        return ""

    formatters = {
        "amazon": _format_amazon,
        "tiktok": _format_tiktok,
        "email": _format_email,
        "live": _format_live,
    }

    fmt = formatters.get(section)
    return fmt(data) if fmt else ""


def _format_amazon(data: dict) -> str:
    md = ""
    title = data.get("title", "")
    if title:
        md += f"### 商品标题\n\n{title}\n\n"
    bullets = data.get("bullet_points", [])
    if bullets:
        md += "### 核心卖点\n\n" + "\n".join(f"- {b}" for b in bullets) + "\n\n"
    desc = data.get("description", "")
    if desc:
        md += "### 产品描述\n\n" + desc + "\n\n"
    return md or "（内容为空）"


def _format_tiktok(data: dict) -> str:
    md = ""
    script = data.get("script", "")
    if script:
        md += "### 视频脚本\n\n" + script + "\n\n"
    caption = data.get("caption", "")
    if caption:
        md += "### 视频文案\n\n" + caption + "\n\n"
    hashtags = data.get("hashtags", [])
    if hashtags:
        tag_str = " ".join(hashtags) if hashtags[0].startswith("#") else " ".join(f"#{h}" for h in hashtags)
        md += f"### Hashtag\n\n{tag_str}\n\n"
    return md or "（内容为空）"


def _format_email(data: dict) -> str:
    md = ""
    sv1 = data.get("subject_v1", "")
    if sv1:
        md += f"### 邮件主题 V1\n\n{sv1}\n\n"
    sv2 = data.get("subject_v2", "")
    if sv2:
        md += f"### 邮件主题 V2\n\n{sv2}\n\n"
    body = data.get("body", "")
    if body:
        md += "### 邮件正文\n\n" + body + "\n\n"
    return md or "（内容为空）"


def _format_live(data: dict) -> str:
    md = ""
    opening = data.get("opening", "")
    if opening:
        md += "### 🎬 开场话术\n\n" + opening + "\n\n"
    intro = data.get("product_intro", "")
    if intro:
        md += "### 📦 产品介绍话术\n\n" + intro + "\n\n"
    engagement = data.get("engagement", "")
    if engagement:
        md += "### 💬 互动话术\n\n" + engagement + "\n\n"
    closing = data.get("closing", "")
    if closing:
        md += "### 🛒 促单话术\n\n" + closing + "\n\n"
    return md or "（内容为空）"
