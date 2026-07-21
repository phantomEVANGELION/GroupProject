"""结果格式化函数 —— 将 Workflow 输出的 dict 转为 HTML 字符串"""

import json


def _sources_footer(sources: list) -> str:
    if not sources:
        return ""
    # 将 AI 知识降级提示用浅色斜体包裹
    parts = []
    for s in sources:
        if "AI 行业知识" in s:
            parts.append(f'<span class="fallback">{s}</span>')
        else:
            parts.append(s)
    src_str = "、".join(parts)
    return f'<hr><p class="sources">📎 <strong>数据来源</strong>: {src_str}</p>'


def _confidence_badge(conf: str) -> str:
    icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
    label = {"high": "高", "medium": "中", "low": "低"}.get(conf, conf)
    return f'<span class="badge badge-{conf}">{icon} 置信度{label}</span>'


def format_product(state: dict) -> str:
    pa = state.get("product_analysis")
    if not pa:
        return ""

    html = ""

    cat = pa.get("category", {})
    if isinstance(cat, dict):
        levels = [cat.get(k, "") for k in ("level1", "level2", "level3")]
        levels = [l for l in levels if l]
        if levels:
            html += '<div class="result-card">'
            html += "<h3>产品分类</h3>"
            html += f'<p class="category-path"><strong>{"  →  ".join(levels)}</strong></p>'
            html += "</div>"

    points = pa.get("selling_points", [])
    if points:
        html += '<div class="result-card">'
        html += "<h3>核心卖点</h3><ul>"
        for p in points:
            if isinstance(p, dict):
                conf = p.get("confidence", "medium")
                html += "<li>"
                html += f"<strong>{p.get('point', '')}</strong> {_confidence_badge(conf)}"
                detail = p.get("detail", "")
                if detail:
                    html += f"<br><span class='detail'>{detail}</span>"
                html += "</li>"
        html += "</ul></div>"

    profile = pa.get("user_profile", {})
    if isinstance(profile, dict) and any(profile.values()):
        html += '<div class="result-card">'
        html += "<h3>目标用户画像</h3>"
        age = profile.get("age", "")
        if age:
            html += f"<p><strong>年龄</strong>: {age}</p>"
        interests = profile.get("interests", [])
        if interests:
            html += f"<p><strong>兴趣</strong>: {'、'.join(interests)}</p>"
        scenarios = profile.get("scenarios", [])
        if scenarios:
            html += f"<p><strong>使用场景</strong>: {'、'.join(scenarios)}</p>"
        html += "</div>"

    pains = pa.get("pain_points", [])
    if pains:
        html += '<div class="result-card">'
        html += "<h3>用户痛点</h3><ul>"
        for p in pains:
            html += f"<li>{p}</li>"
        html += "</ul></div>"

    advs = pa.get("advantages", [])
    if advs:
        html += '<div class="result-card">'
        html += "<h3>产品核心优势</h3><ul>"
        for a in advs:
            html += f"<li>{a}</li>"
        html += "</ul></div>"

    sources = pa.get("sources", state.get("product_sources", []))
    html += _sources_footer(sources)
    return html or '<p class="empty-state">（分析结果为空）</p>'


def format_market(state: dict) -> str:
    ma = state.get("market_analysis")
    if not ma:
        return ""

    html = ""

    note = ma.get("overall_note", "")
    if note:
        html += f"<blockquote>{note}</blockquote>"

    markets = ma.get("recommended_markets", [])
    if markets:
        html += '<div class="result-card">'
        html += "<h3>推荐目标市场</h3>"
        for m in markets:
            if not isinstance(m, dict):
                continue
            country = m.get("country", "未知")
            opp = m.get("opportunity", "medium")
            opp_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(opp, "⚪")
            conf = m.get("confidence", "")
            conf_tag = f' <span class="badge badge-{conf}">(置信度: {conf})</span>' if conf else ""

            html += f'<div class="market-item">'
            html += f"<h4>{opp_icon} {country}{conf_tag}</h4>"

            reasons = m.get("reasons", [])
            if reasons:
                html += "<p><strong>推荐原因:</strong></p><ul>"
                for r in reasons:
                    html += f"<li>{r}</li>"
                html += "</ul>"

            risks = m.get("risks", [])
            if risks:
                html += "<p><strong>进入风险:</strong></p><ul>"
                for r in risks:
                    html += f"<li>{r}</li>"
                html += "</ul>"

            insight = m.get("consumer_insight", "")
            if insight:
                html += f"<p><strong>消费者洞察:</strong> {insight}</p>"

            ds = m.get("data_source", "")
            if ds:
                html += f'<p class="data-source">数据来源: {ds}</p>'

            html += "</div>"
        html += "</div>"

    trend = ma.get("market_trend", "")
    if trend:
        html += f'<div class="result-card"><h3>市场判断</h3><p class="trend"><strong>{trend}</strong></p></div>'

    sources = ma.get("sources", state.get("market_sources", []))
    html += _sources_footer(sources)
    return html or '<p class="empty-state">（分析结果为空）</p>'


def format_competitor(state: dict) -> str:
    ca = state.get("competitor_analysis")
    if not ca:
        return ""

    html = ""

    assessment = ca.get("overall_assessment", "")
    if assessment:
        html += f"<blockquote>{assessment}</blockquote>"

    competitors = ca.get("competitors", [])
    if competitors:
        html += '<div class="result-card">'
        html += "<h3>竞品对比</h3>"
        html += '<div class="table-wrap"><table>'
        html += "<thead><tr>"
        html += "<th>竞品</th><th>价格区间</th><th>定位</th><th>优势</th><th>劣势</th><th>我们的机会</th>"
        html += "</tr></thead><tbody>"
        for c in competitors:
            if not isinstance(c, dict):
                continue
            html += "<tr>"
            html += f"<td><strong>{c.get('name', '未知')}</strong></td>"
            html += f"<td>{c.get('price_range', '-')}</td>"
            html += f"<td>{c.get('position', '-')}</td>"
            html += f"<td>{'、'.join(c.get('strengths', []))[:60]}</td>"
            html += f"<td>{'、'.join(c.get('weaknesses', []))[:60]}</td>"
            html += f"<td>{c.get('our_advantage', '-')[:60]}</td>"
            html += "</tr>"
        html += "</tbody></table></div>"
        html += "</div>"

    diff = ca.get("differentiation_opportunity", "")
    if diff:
        html += f'<div class="result-card"><h3>差异化机会</h3><p><strong>{diff}</strong></p></div>'

    sources = ca.get("sources", state.get("competitor_sources", []))
    html += _sources_footer(sources)
    return html or '<p class="empty-state">（分析结果为空）</p>'


def format_strategy(state: dict) -> str:
    st = state.get("strategy")
    if not st:
        return ""

    html = ""

    positioning = st.get("brand_positioning", "")
    if positioning:
        html += '<div class="result-card">'
        html += "<h3>品牌定位</h3>"
        html += f"<p><strong>{positioning}</strong></p>"
        html += "</div>"

    vp = st.get("core_value_proposition", "")
    if vp:
        html += '<div class="result-card">'
        html += "<h3>核心价值主张</h3>"
        html += f"<p>{vp}</p>"
        html += "</div>"

    km = st.get("key_message", "")
    if km:
        html += '<div class="result-card">'
        html += "<h3>关键传播信息</h3>"
        html += f"<p>{km}</p>"
        html += "</div>"

    channels = st.get("channels", [])
    if channels:
        html += '<div class="result-card">'
        html += "<h3>推荐营销渠道</h3>"
        html += '<div class="table-wrap"><table>'
        html += "<thead><tr><th>平台</th><th>优先级</th><th>理由</th></tr></thead><tbody>"
        for ch in channels:
            if not isinstance(ch, dict):
                continue
            pri = ch.get("priority", "medium")
            pri_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(pri, "⚪")
            html += "<tr>"
            html += f"<td>{pri_icon} {ch.get('platform', '未知')}</td>"
            html += f"<td>{pri}</td>"
            html += f"<td>{ch.get('reason', '-')}</td>"
            html += "</tr>"
        html += "</tbody></table></div>"
        html += "</div>"

    cs = st.get("content_strategy", {})
    if isinstance(cs, dict) and cs:
        html += '<div class="result-card">'
        html += "<h3>内容策略</h3>"
        ratio = cs.get("tiktok_ratio", "")
        if ratio:
            html += f"<p><strong>TikTok 内容配比</strong>: {ratio}</p>"
        keywords = cs.get("amazon_seo_keywords", [])
        if keywords:
            html += f"<p><strong>Amazon SEO 关键词</strong>: {'、'.join(keywords)}</p>"
        html += "</div>"

    return html or '<p class="empty-state">（策略结果为空）</p>'


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
    html = ""
    title = data.get("title", "")
    if title:
        html += '<div class="content-block">'
        html += f"<h3>商品标题</h3>"
        html += f'<p class="amazon-title">{title}</p>'
        html += "</div>"

    bullets = data.get("bullet_points", [])
    if bullets:
        html += '<div class="content-block">'
        html += "<h3>核心卖点</h3><ul>"
        for b in bullets:
            html += f"<li>{b}</li>"
        html += "</ul></div>"

    desc = data.get("description", "")
    if desc:
        html += '<div class="content-block">'
        html += "<h3>产品描述</h3>"
        html += f"<p>{desc}</p>"
        html += "</div>"

    return html or '<p class="empty-state">（内容为空）</p>'


def _format_tiktok(data: dict) -> str:
    html = ""
    script = data.get("script", "")
    if script:
        html += '<div class="content-block">'
        html += "<h3>视频脚本</h3>"
        html += f'<div class="script-block">{script}</div>'
        html += "</div>"

    caption = data.get("caption", "")
    if caption:
        html += '<div class="content-block">'
        html += "<h3>视频文案</h3>"
        html += f"<p>{caption}</p>"
        html += "</div>"

    hashtags = data.get("hashtags", [])
    if hashtags:
        tag_str = " ".join(hashtags) if hashtags[0].startswith("#") else " ".join(f"#{h}" for h in hashtags)
        html += '<div class="content-block">'
        html += "<h3>Hashtag</h3>"
        html += f'<p class="hashtags">{tag_str}</p>'
        html += "</div>"

    return html or '<p class="empty-state">（内容为空）</p>'


def _format_email(data: dict) -> str:
    html = ""
    sv1 = data.get("subject_v1", "")
    if sv1:
        html += '<div class="content-block">'
        html += "<h3>邮件主题 V1</h3>"
        html += f'<p class="email-subject">{sv1}</p>'
        html += "</div>"

    sv2 = data.get("subject_v2", "")
    if sv2:
        html += '<div class="content-block">'
        html += "<h3>邮件主题 V2</h3>"
        html += f'<p class="email-subject">{sv2}</p>'
        html += "</div>"

    body = data.get("body", "")
    if body:
        html += '<div class="content-block">'
        html += "<h3>邮件正文</h3>"
        html += f'<div class="email-body">{body}</div>'
        html += "</div>"

    return html or '<p class="empty-state">（内容为空）</p>'


def _format_live(data: dict) -> str:
    html = ""
    opening = data.get("opening", "")
    if opening:
        html += '<div class="content-block">'
        html += "<h3>🎬 开场话术</h3>"
        html += f'<div class="script-block">{opening}</div>'
        html += "</div>"

    intro = data.get("product_intro", "")
    if intro:
        html += '<div class="content-block">'
        html += "<h3>📦 产品介绍话术</h3>"
        html += f'<div class="script-block">{intro}</div>'
        html += "</div>"

    engagement = data.get("engagement", "")
    if engagement:
        html += '<div class="content-block">'
        html += "<h3>💬 互动话术</h3>"
        html += f'<div class="script-block">{engagement}</div>'
        html += "</div>"

    closing = data.get("closing", "")
    if closing:
        html += '<div class="content-block">'
        html += "<h3>🛒 促单话术</h3>"
        html += f'<div class="script-block">{closing}</div>'
        html += "</div>"

    return html or '<p class="empty-state">（内容为空）</p>'
