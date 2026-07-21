"""AI 跨境出海运营助手 · Demo
FastAPI + 纯 HTML 前端 → LangGraph Workflow → RAG → LLM
"""

import json
import os
import sys
import time
import traceback

# 确保在项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn

from workflow.state import create_initial_state
from workflow.nodes import (
    product_node, market_node, competitor_node,
    strategy_node, content_node,
)
from init_knowledge_base import init_market_kb, init_competitor_kb
from app_format import (
    format_product, format_market, format_competitor,
    format_strategy, format_content_section,
)

app = FastAPI(title="AI 跨境出海运营助手")


# ================================================================
# 页面 HTML
# ================================================================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 跨境出海运营助手 · Demo</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #f8fafc; color: #1e293b; line-height: 1.6; }
.container { max-width: 1000px; margin: 0 auto; padding: 20px; }
.header { text-align: center; padding: 20px 0; }
.header h1 { font-size: 1.8em; color: #0f172a; }
.header p { color: #64748b; font-size: 0.9em; }
.flow { display: flex; justify-content: center; gap: 6px; padding: 12px 0;
        font-size: 13px; color: #64748b; flex-wrap: wrap; }
.flow span { white-space: nowrap; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 8px 0; }

.input-section { background: white; border-radius: 12px; padding: 20px;
                  border: 1px solid #e2e8f0; margin: 12px 0; }
.input-row { display: flex; gap: 16px; }
.input-col { flex: 1; }
label { display: block; font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #334155; }
input, textarea { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1;
                  border-radius: 8px; font-size: 14px; outline: none; transition: border-color .2s; }
input:focus, textarea:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
textarea { resize: vertical; font-family: inherit; }
.actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.btn { padding: 10px 24px; border: none; border-radius: 8px; font-size: 15px;
       font-weight: 600; cursor: pointer; transition: all .2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-secondary { background: #e2e8f0; color: #334155; }
.btn-secondary:hover:not(:disabled) { background: #cbd5e1; }

.progress { display: none; margin: 12px 0; }
.progress.active { display: block; }
.progress-bar { height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg,#3b82f6,#10b981);
                 border-radius: 3px; transition: width .5s; }
.progress-text { font-size: 14px; color: #475569; margin-top: 8px; text-align: center; }
.progress-steps { display: flex; justify-content: center; gap: 6px; font-size: 13px;
                  margin-bottom: 10px; color: #94a3b8; }
.progress-steps .done { color: #10b981; }
.progress-steps .current { color: #3b82f6; font-weight: 600; }

.tabs { display: none; margin-top: 12px; }
.tabs.active { display: block; }
.tab-header { display: flex; gap: 4px; border-bottom: 2px solid #e2e8f0; margin-bottom: 16px;
              overflow-x: auto; }
.tab-btn { padding: 10px 16px; border: none; background: none; font-size: 14px;
           font-weight: 500; color: #64748b; cursor: pointer; white-space: nowrap;
           border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab-btn:hover { color: #334155; }
.tab-btn.active { color: #3b82f6; border-bottom-color: #3b82f6; }
.tab-content { display: none; }
.tab-content.active { display: block; }
.sub-tabs { display: flex; gap: 4px; margin-bottom: 12px; }
.sub-tab-btn { padding: 6px 14px; border: 1px solid #e2e8f0; border-radius: 6px;
               background: white; font-size: 13px; cursor: pointer; color: #64748b; }
.sub-tab-btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }
.sub-tab-content { display: none; }
.sub-tab-content.active { display: block; }

.result-card { background: white; border-radius: 12px; padding: 20px;
               border: 1px solid #e2e8f0; margin: 8px 0; }
.result-card h3 { font-size: 16px; margin-bottom: 12px; color: #0f172a; }
.result-card h4 { font-size: 14px; margin: 12px 0 6px; color: #334155; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 8px 10px; border: 1px solid #e2e8f0; text-align: left; }
th { background: #f8fafc; font-weight: 600; color: #475569; }
.sources { font-size: 12px; color: #94a3b8; margin-top: 12px; padding-top: 8px;
           border-top: 1px solid #e2e8f0; }
.error-box { background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px;
             padding: 12px; margin: 8px 0; font-size: 13px; color: #b91c1c; }
.footer { text-align: center; padding: 20px 0; font-size: 12px; color: #94a3b8; }
.copy-btn { float: right; padding: 4px 10px; font-size: 12px; border: 1px solid #e2e8f0;
            border-radius: 4px; background: white; cursor: pointer; color: #64748b; }
.copy-btn:hover { background: #f1f5f9; }
.markdown-body ul, .markdown-body ol { padding-left: 20px; margin: 8px 0; }
.markdown-body li { margin: 4px 0; }
@media (max-width: 700px) { .input-row { flex-direction: column; } }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>🌍 AI 跨境出海运营助手</h1>
<p>AI-powered Export Marketing Assistant · Demo</p>
</div>
<div class="flow">
<span>📄 产品资料</span><span>→</span><span>📚 RAG 知识检索</span>
<span>→</span><span>🤖 AI 分析</span><span>→</span><span>🎯 营销策略</span>
<span>→</span><span>✍️ 内容生成</span>
</div>
<hr>

<div class="input-section">
<div class="input-row">
<div class="input-col">
<label>产品名称</label>
<input id="productName" placeholder="例如: X100 智能运动手表" value="X100 智能运动手表">
</div>
</div>
<div class="input-row" style="margin-top:8px">
<div class="input-col">
<label>产品描述</label>
<textarea id="productDesc" rows="4" placeholder="请描述产品核心功能、规格...">IP68防水 · 7天超长续航 · 24小时健康监测（心率/血氧/睡眠）
铝合金表壳 · 1.43英寸AMOLED屏幕 · 蓝牙5.3 · GPS运动轨迹追踪
100+运动模式 · 兼容iOS/Android · 磁吸充电 · 仅重52g</textarea>
</div>
</div>
<div class="actions">
<button class="btn btn-secondary" onclick="loadSample()">📂 加载示例产品</button>
<button class="btn btn-primary" id="analyzeBtn" onclick="startAnalysis()">🚀 开始全面分析</button>
</div>
</div>

<div class="progress" id="progressSection">
<div class="progress-steps" id="progressSteps">
<span id="s1">⬜ 产品分析</span><span>→</span>
<span id="s2">⬜ 市场分析</span><span>→</span>
<span id="s3">⬜ 竞品分析</span><span>→</span>
<span id="s4">⬜ 营销策略</span><span>→</span>
<span id="s5">⬜ 内容生成</span>
</div>
<div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
<div class="progress-text" id="progressText">等待开始...</div>
</div>

<div class="tabs" id="tabsSection">
<div class="tab-header" id="tabHeaders"></div>
<div id="tabContents"></div>
</div>

<div id="errorBox" class="error-box" style="display:none"></div>

<div class="footer">
⚠️ AI 辅助分析 · 基于预置知识库生成 · 仅供 Demo 演示参考
</div>
</div>

<script>
const TAB_NAMES = ["📋 产品分析","🌍 市场分析","⚔️ 竞品分析","🎯 营销策略","✍️ 内容生成"];
const SUB_TABS = {
    4: ["🛒 Amazon","🎬 TikTok","📧 开发信","📺 直播话术"]
};

function loadSample() {
    document.getElementById("productName").value = "X100 智能运动手表";
    document.getElementById("productDesc").value =
        "IP68防水 · 7天超长续航 · 24小时健康监测（心率/血氧/睡眠）\n" +
        "铝合金表壳 · 1.43英寸AMOLED屏幕 · 蓝牙5.3\n" +
        "GPS运动轨迹追踪 · 100+运动模式 · 兼容iOS/Android\n" +
        "磁吸充电 · 仅重52g · 支持支付宝/微信离线支付";
}

function setProgress(step) {
    const steps = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0];
    const labels = ["","📋 正在分析产品资料...","🌍 正在分析市场数据...",
                    "⚔️ 正在分析竞品信息...","🎯 正在制定营销策略...",
                    "✍️ 正在生成营销内容...","✅ 分析完成！"];
    const pct = step >= 6 ? 100 : Math.round((step-1)/5*100);
    document.getElementById("progressFill").style.width = pct + "%";
    document.getElementById("progressText").textContent = labels[step] || "";
    for (let i = 1; i <= 5; i++) {
        const el = document.getElementById("s"+i);
        if (i < step) { el.className = "done"; el.innerHTML = "✅ " + TAB_NAMES[i-1].replace(/^.. /,""); }
        else if (i === step) { el.className = "current"; el.innerHTML = "🔄 " + TAB_NAMES[i-1].replace(/^.. /,""); }
        else { el.className = ""; el.innerHTML = "⬜ " + TAB_NAMES[i-1].replace(/^.. /,""); }
    }
}

function showError(msg) {
    document.getElementById("errorBox").style.display = "block";
    document.getElementById("errorBox").textContent = "⚠️ " + msg;
}

async function startAnalysis() {
    const name = document.getElementById("productName").value.trim();
    const desc = document.getElementById("productDesc").value.trim();
    if (!name && !desc) { showError("请填写产品名称或描述"); return; }

    document.getElementById("errorBox").style.display = "none";
    document.getElementById("analyzeBtn").disabled = true;
    document.getElementById("progressSection").className = "progress active";
    document.getElementById("tabsSection").className = "tabs";
    document.getElementById("tabContents").innerHTML = "";

    setProgress(1);

    try {
        const resp = await fetch("/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({product_name: name, product_description: desc})
        });
        if (!resp.ok) {
            const err = await resp.text();
            showError("分析失败: " + err.slice(0,200));
            document.getElementById("analyzeBtn").disabled = false;
            return;
        }
        const result = await resp.json();
        renderResults(result);
    } catch (e) {
        showError("网络错误: " + e.message);
        document.getElementById("analyzeBtn").disabled = false;
    }
}

function renderResults(result) {
    setProgress(6);
    document.getElementById("analyzeBtn").disabled = false;
    document.getElementById("tabsSection").className = "tabs active";

    const tabs = result.tabs || [];
    const errors = result.errors || [];
    const tabHeaders = document.getElementById("tabHeaders");
    const tabContents = document.getElementById("tabContents");
    tabHeaders.innerHTML = "";
    tabContents.innerHTML = "";

    TAB_NAMES.forEach((name, i) => {
        const btn = document.createElement("button");
        btn.className = "tab-btn" + (i === 0 ? " active" : "");
        btn.textContent = name;
        btn.onclick = () => switchTab(i);
        tabHeaders.appendChild(btn);

        const content = document.createElement("div");
        content.className = "tab-content" + (i === 0 ? " active" : "");
        content.dataset.index = i;

        if (i === 4 && tabs[i]) {
            // Content tab: show sub-tabs
            const subTabNames = ["Amazon Listing", "TikTok 脚本", "开发信", "直播话术"];
            const subKeys = ["amazon", "tiktok", "email", "live"];
            const subNav = document.createElement("div");
            subNav.className = "sub-tabs";
            subNav.id = "subTabNav";
            content.appendChild(subNav);

            const subContainer = document.createElement("div");
            subContainer.id = "subTabContainer";

            subTabNames.forEach((sname, si) => {
                const sbtn = document.createElement("button");
                sbtn.className = "sub-tab-btn" + (si === 0 ? " active" : "");
                sbtn.textContent = sname;
                sbtn.onclick = () => switchSubTab(si);
                subNav.appendChild(sbtn);

                const sdiv = document.createElement("div");
                sdiv.className = "sub-tab-content" + (si === 0 ? " active" : "");
                sdiv.innerHTML = tabs[i][subKeys[si]] || "<p>（无内容）</p>";
                subContainer.appendChild(sdiv);
            });
            content.appendChild(subContainer);
        } else if (tabs[i]) {
            const card = document.createElement("div");
            card.className = "result-card markdown-body";
            card.innerHTML = tabs[i];
            content.appendChild(card);
        } else {
            content.innerHTML = "<p style='color:#94a3b8;padding:20px;'>（分析结果为空）</p>";
        }

        tabContents.appendChild(content);
    });

    if (errors.length > 0) {
        const errDiv = document.createElement("div");
        errDiv.className = "error-box";
        errDiv.textContent = "⚠️ 执行警告（不影响已生成的结果）: " + errors.join("; ");
        tabContents.appendChild(errDiv);
    }
}

function switchTab(index) {
    document.querySelectorAll(".tab-btn").forEach((b,i) => b.className = "tab-btn" + (i===index?" active":""));
    document.querySelectorAll(".tab-content").forEach((c,i) => c.className = "tab-content" + (i===index?" active":""));
}

function switchSubTab(index) {
    const nav = document.getElementById("subTabNav");
    if (!nav) return;
    nav.querySelectorAll(".sub-tab-btn").forEach((b,i) => b.className = "sub-tab-btn" + (i===index?" active":""));
    const container = document.getElementById("subTabContainer");
    if (!container) return;
    container.querySelectorAll(".sub-tab-content").forEach((c,i) => c.className = "sub-tab-content" + (i===index?" active":""));
}
</script>
</body>
</html>"""


# ================================================================
# API 端点
# ================================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/analyze")
async def analyze(request: Request):
    """运行完整分析工作流，返回格式化的 Markdown 结果"""
    data = await request.json()
    product_name = data.get("product_name", "")
    product_description = data.get("product_description", "")

    state = create_initial_state(
        product_name=product_name or "未知产品",
        product_description=product_description or "",
    )

    # 顺序执行 5 个节点
    for name, func in [
        ("product", product_node),
        ("market", market_node),
        ("competitor", competitor_node),
        ("strategy", strategy_node),
        ("content", content_node),
    ]:
        try:
            state = func(state)
        except Exception as e:
            state["errors"].append(f"{name}_node 异常: {traceback.format_exc()}")

    errors = state.get("errors", [])

    # 格式化结果
    tabs = [
        format_product(state),
        format_market(state),
        format_competitor(state),
        format_strategy(state),
        {
            "amazon": format_content_section(state, "amazon"),
            "tiktok": format_content_section(state, "tiktok"),
            "email": format_content_section(state, "email"),
            "live": format_content_section(state, "live"),
        },
    ]

    return {"tabs": tabs, "errors": errors}


# ================================================================
# 启动
# ================================================================

if __name__ == "__main__":
    print("\n🚀 启动 AI 跨境出海运营助手 Demo...")
    print(f"   地址: http://127.0.0.1:7860")
    print()
    uvicorn.run(app, host="127.0.0.1", port=7860)
