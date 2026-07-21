"""AI 跨境出海运营助手 · Demo
FastAPI + 纯 HTML 前端 → LangGraph Workflow → RAG → LLM
"""

import json
import os
import sys
import time
import traceback
import asyncio

# 确保在项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from contextlib import asynccontextmanager
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

from rag.chroma_client import get_collection_count
import config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：按需初始化知识库
    print("\n📚 检查知识库状态...")
    try:
        if get_collection_count(config.COLLECTION_MARKET) == 0:
            init_market_kb()
        else:
            print("  ✅ 市场知识库已存在，跳过初始化")
        if get_collection_count(config.COLLECTION_COMPETITOR) == 0:
            init_competitor_kb()
        else:
            print("  ✅ 竞品知识库已存在，跳过初始化")
    except Exception as e:
        print(f"  ⚠️ 知识库检查失败（首次运行会自动初始化）: {e}")
    yield
    # 关闭时（如有必要）
    print("👋 应用关闭")

app = FastAPI(title="AI 跨境出海运营助手", lifespan=lifespan)


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
                  margin-bottom: 10px; color: #94a3b8; flex-wrap: wrap; }
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
.sub-tabs { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
.sub-tab-btn { padding: 6px 14px; border: 1px solid #e2e8f0; border-radius: 6px;
               background: white; font-size: 13px; cursor: pointer; color: #64748b; }
.sub-tab-btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }
.sub-tab-content { display: none; }
.sub-tab-content.active { display: block; }

/* ---- 结果卡片 ---- */
.result-card { background: white; border-radius: 12px; padding: 20px;
               border: 1px solid #e2e8f0; margin: 8px 0; }
.result-card h3 { font-size: 16px; margin-bottom: 12px; color: #0f172a;
                  border-left: 3px solid #3b82f6; padding-left: 10px; }
.result-card h4 { font-size: 14px; margin: 12px 0 6px; color: #334155; }
.result-card ul { padding-left: 20px; margin: 8px 0; }
.result-card li { margin: 4px 0; line-height: 1.5; }
.result-card p { margin: 6px 0; }
.result-card .detail { color: #64748b; font-size: 13px; }

/* ---- 表格 ---- */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 10px 12px; border: 1px solid #e2e8f0; text-align: left; }
th { background: #f8fafc; font-weight: 600; color: #475569; white-space: nowrap; }
td { vertical-align: top; }

/* ---- 置信度标签 ---- */
.badge { display: inline-block; font-size: 11px; padding: 2px 8px;
         border-radius: 10px; margin-left: 6px; vertical-align: middle; }
.badge-high { background: #dcfce7; color: #166534; }
.badge-medium { background: #fef9c3; color: #854d0e; }
.badge-low { background: #fee2e2; color: #991b1b; }

/* ---- 市场条目 ---- */
.market-item { background: #f8fafc; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
.market-item h4 { margin-top: 0; }
.data-source { font-size: 12px; color: #94a3b8; font-style: italic; margin-top: 4px; }

/* ---- 内容块 ---- */
.content-block { background: white; border-radius: 12px; padding: 20px;
                 border: 1px solid #e2e8f0; margin: 8px 0; }
.content-block h3 { font-size: 15px; margin-bottom: 10px; color: #0f172a;
                    border-left: 3px solid #10b981; padding-left: 10px; }
.script-block { background: #f8fafc; border-radius: 8px; padding: 16px;
                font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.email-body { background: #f8fafc; border-radius: 8px; padding: 16px;
              font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.email-subject { background: #f1f5f9; border-radius: 6px; padding: 8px 12px;
                 font-family: monospace; font-size: 14px; }
.amazon-title { font-size: 16px; font-weight: 600; color: #0f172a; }
.hashtags { color: #3b82f6; font-size: 13px; }

/* ---- 通用 ---- */
.sources { font-size: 12px; color: #94a3b8; margin-top: 12px; padding-top: 8px;
           border-top: 1px solid #e2e8f0; }
.sources .fallback { color: #b0b8c4; font-style: italic; font-size: 11px; }
blockquote { background: #f1f5f9; border-left: 4px solid #3b82f6; border-radius: 4px;
             padding: 12px 16px; margin: 8px 0; color: #475569; font-size: 14px; }
.empty-state { color: #94a3b8; padding: 20px; text-align: center; }
.error-box { background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px;
             padding: 12px; margin: 8px 0; font-size: 13px; color: #b91c1c; }
.footer { text-align: center; padding: 20px 0; font-size: 12px; color: #94a3b8; }

/* ---- Toast 通知 ---- */
#notificationContainer { position: fixed; top: 20px; right: 20px; z-index: 9999;
                         display: flex; flex-direction: column; gap: 8px; pointer-events: none; }
.toast { background: #10b981; color: white; padding: 12px 24px; border-radius: 10px;
         font-weight: 600; font-size: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
         transform: translateX(120%); transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
         max-width: 320px; pointer-events: auto; }
.toast.show { transform: translateX(0); }
.toast-error { background: #ef4444; }

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

<div id="notificationContainer"></div>

<script>
const TAB_NAMES = ["📋 产品分析","🌍 市场分析","⚔️ 竞品分析","🎯 营销策略","✍️ 内容生成"];
const NOTIFY_MSG = {
    1: "✅ 产品分析生成完毕！",
    2: "🌍 市场分析生成完毕！",
    3: "⚔️ 竞品分析生成完毕！",
    4: "🎯 营销策略生成完毕！",
    5: "✍️ 内容生成生成完毕！"
};
const STEP_NAMES = ["产品分析", "市场分析", "竞品分析", "营销策略", "内容生成"];

// ========== Toast 通知 ==========
function showNotification(msg, isError) {
    const container = document.getElementById("notificationContainer");
    const toast = document.createElement("div");
    toast.className = "toast" + (isError ? " toast-error" : "");
    toast.textContent = msg;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

// ========== 示例加载 ==========
function loadSample() {
    document.getElementById("productName").value = "X100 智能运动手表";
    document.getElementById("productDesc").value =
        "IP68防水 · 7天超长续航 · 24小时健康监测（心率/血氧/睡眠）\n" +
        "铝合金表壳 · 1.43英寸AMOLED屏幕 · 蓝牙5.3\n" +
        "GPS运动轨迹追踪 · 100+运动模式 · 兼容iOS/Android\n" +
        "磁吸充电 · 仅重52g · 支持支付宝/微信离线支付";
}

// ========== 进度条 ==========
function setProgress(step) {
    const pct = Math.min(Math.round((step - 1) / 5 * 100), 100);
    document.getElementById("progressFill").style.width = pct + "%";

    const labels = ["等待开始...", "📋 正在分析产品资料...", "🌍 正在分析市场数据...",
                    "⚔️ 正在分析竞品信息...", "🎯 正在制定营销策略...",
                    "✍️ 正在生成营销内容...", "✅ 分析完成！"];
    document.getElementById("progressText").textContent = labels[Math.min(step, 6)] || "";

    for (let i = 1; i <= 5; i++) {
        const el = document.getElementById("s" + i);
        if (i < step) {
            el.className = "done";
            el.innerHTML = "✅ " + STEP_NAMES[i - 1];
        } else if (i === step) {
            el.className = "current";
            el.innerHTML = "🔄 " + STEP_NAMES[i - 1];
        } else {
            el.className = "";
            el.innerHTML = "⬜ " + STEP_NAMES[i - 1];
        }
    }
}

function showError(msg) {
    document.getElementById("errorBox").style.display = "block";
    document.getElementById("errorBox").textContent = "⚠️ " + msg;
    showNotification("⚠️ " + msg, true);
}

// ========== 构建空 Tab 骨架 ==========
function buildTabStructure() {
    const tabHeaders = document.getElementById("tabHeaders");
    const tabContents = document.getElementById("tabContents");
    tabHeaders.innerHTML = "";
    tabContents.innerHTML = "";

    TAB_NAMES.forEach(function(name, i) {
        const btn = document.createElement("button");
        btn.className = "tab-btn" + (i === 0 ? " active" : "");
        btn.textContent = name;
        btn.onclick = function() { switchTab(i); };
        tabHeaders.appendChild(btn);

        const div = document.createElement("div");
        div.className = "tab-content" + (i === 0 ? " active" : "");
        div.innerHTML = '<p class="empty-state">⏳ 等待分析结果...</p>';
        tabContents.appendChild(div);
    });
}

// ========== 渲染单个 Tab ==========
function renderTabContent(index, html) {
    const container = document.getElementById("tabContents");
    const contentDiv = container.children[index];
    if (!contentDiv) return;

    if (index === 4 && typeof html === "object") {
        contentDiv.innerHTML = "";
        const subNames = ["Amazon Listing", "TikTok 脚本", "开发信", "直播话术"];
        const subKeys = ["amazon", "tiktok", "email", "live"];

        const subNav = document.createElement("div");
        subNav.className = "sub-tabs";

        const subContainer = document.createElement("div");

        subNames.forEach(function(sname, si) {
            const sbtn = document.createElement("button");
            sbtn.className = "sub-tab-btn" + (si === 0 ? " active" : "");
            sbtn.textContent = sname;
            sbtn.onclick = function() { switchSubTab(si); };
            subNav.appendChild(sbtn);

            const sdiv = document.createElement("div");
            sdiv.className = "sub-tab-content" + (si === 0 ? " active" : "");
            sdiv.innerHTML = html[subKeys[si]] || '<p class="empty-state">（无内容）</p>';
            subContainer.appendChild(sdiv);
        });

        contentDiv.appendChild(subNav);
        contentDiv.appendChild(subContainer);
    } else if (typeof html === "string" && html.trim().length > 0) {
        contentDiv.innerHTML = html;
    } else {
        contentDiv.innerHTML = '<p class="empty-state">（分析结果为空）</p>';
    }
}

// ========== 流式事件处理 ==========
function handleStreamEvent(event) {
    var step = event.step;
    if (step === 6) {
        document.getElementById("analyzeBtn").disabled = false;
        setProgress(6);
        if (event.errors && event.errors.length > 0) {
            var errDiv = document.createElement("div");
            errDiv.className = "error-box";
            errDiv.textContent = "⚠️ 执行警告（不影响已生成的结果）: " + event.errors.join("; ");
            document.getElementById("tabContents").appendChild(errDiv);
        }
        return;
    }

    // 更新进度（当前步骤已完成，指向下一步）
    setProgress(step + 1);

    // 通知
    var msg = NOTIFY_MSG[step];
    if (msg) showNotification(msg);

    // 渲染对应 tab
    renderTabContent(step - 1, event.html);
}

// ========== 开始分析（流式） ==========
async function startAnalysis() {
    var name = document.getElementById("productName").value.trim();
    var desc = document.getElementById("productDesc").value.trim();
    if (!name && !desc) { showError("请填写产品名称或描述"); return; }

    document.getElementById("errorBox").style.display = "none";
    document.getElementById("analyzeBtn").disabled = true;
    document.getElementById("progressSection").className = "progress active";
    document.getElementById("tabsSection").className = "tabs active";

    document.getElementById("tabContents").innerHTML = "";
    document.getElementById("tabHeaders").innerHTML = "";

    buildTabStructure();
    setProgress(1);

    try {
        var resp = await fetch("/analyze-stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product_name: name, product_description: desc })
        });

        if (!resp.ok) {
            var errText = await resp.text();
            showError("分析失败: " + errText.slice(0, 200));
            document.getElementById("analyzeBtn").disabled = false;
            return;
        }

        var reader = resp.body.getReader();
        var decoder = new TextDecoder();
        var buffer = "";

        while (true) {
            var result = await reader.read();
            if (result.done) break;

            buffer += decoder.decode(result.value, { stream: true });
            var parts = buffer.split("\n");
            buffer = parts.pop();

            for (var j = 0; j < parts.length; j++) {
                var line = parts[j].trim();
                if (line.startsWith("data: ")) {
                    try {
                        var eventData = JSON.parse(line.slice(6));
                        handleStreamEvent(eventData);
                    } catch (e) {
                        console.warn("Event parse:", e);
                    }
                }
            }
        }
    } catch (e) {
        showError("网络错误: " + e.message);
        document.getElementById("analyzeBtn").disabled = false;
    }
}

// ========== Tab 切换 ==========
function switchTab(index) {
    var btns = document.querySelectorAll(".tab-btn");
    for (var i = 0; i < btns.length; i++) {
        btns[i].className = "tab-btn" + (i === index ? " active" : "");
    }
    var contents = document.querySelectorAll(".tab-content");
    for (var i = 0; i < contents.length; i++) {
        contents[i].className = "tab-content" + (i === index ? " active" : "");
    }
}

function switchSubTab(index) {
    var nav = document.querySelector(".sub-tabs");
    if (!nav) return;
    var btns = nav.querySelectorAll(".sub-tab-btn");
    for (var i = 0; i < btns.length; i++) {
        btns[i].className = "sub-tab-btn" + (i === index ? " active" : "");
    }
    var container = nav.nextElementSibling;
    if (!container) return;
    var contents = container.querySelectorAll(".sub-tab-content");
    for (var i = 0; i < contents.length; i++) {
        contents[i].className = "sub-tab-content" + (i === index ? " active" : "");
    }
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
    """（向后兼容）运行完整分析工作流，一次性返回格式化的结果"""
    data = await request.json()
    product_name = data.get("product_name", "")
    product_description = data.get("product_description", "")

    state = create_initial_state(
        product_name=product_name or "未知产品",
        product_description=product_description or "",
    )

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


@app.post("/analyze-stream")
async def analyze_stream(request: Request):
    """SSE 流式分析 —— 每完成一个节点就推送结果到前端"""
    data = await request.json()
    product_name = data.get("product_name", "")
    product_description = data.get("product_description", "")

    state = create_initial_state(
        product_name=product_name or "未知产品",
        product_description=product_description or "",
    )

    async def event_generator():
        nonlocal state
        loop = asyncio.get_event_loop()
        steps = [
            ("product", product_node, format_product),
            ("market", market_node, format_market),
            ("competitor", competitor_node, format_competitor),
            ("strategy", strategy_node, format_strategy),
            ("content", content_node, None),
        ]

        for i, (name, node_func, format_func) in enumerate(steps, 1):
            try:
                state = await loop.run_in_executor(None, node_func, state)
            except Exception as e:
                state["errors"].append(f"{name}_node 异常: {traceback.format_exc()}")

            if i == 5:  # 内容节点 —— 特殊处理，返回带子标签的对象
                html = {
                    "amazon": format_content_section(state, "amazon"),
                    "tiktok": format_content_section(state, "tiktok"),
                    "email": format_content_section(state, "email"),
                    "live": format_content_section(state, "live"),
                }
            else:
                html = format_func(state) if format_func else ""

            event = {"step": i, "html": html, "errors": state.get("errors", [])}
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # 最终完成事件
        final = {"step": 6, "status": "complete", "errors": state.get("errors", [])}
        yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ================================================================
# 启动
# ================================================================

if __name__ == "__main__":
    print("\n🚀 启动 AI 跨境出海运营助手 Demo...")
    print(f"   地址: http://127.0.0.1:7860")
    print()
    uvicorn.run(app, host="127.0.0.1", port=7860)
