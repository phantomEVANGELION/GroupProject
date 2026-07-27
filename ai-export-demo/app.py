"""AI 跨境出海运营助手 · Demo
FastAPI + 纯 HTML 前端 → LangGraph Workflow → RAG → LLM
"""

import json
import os
import sys
import time
import traceback
import asyncio
import urllib.request
from datetime import date, timedelta

# 确保在项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from contextlib import asynccontextmanager
import shutil
import uvicorn

from workflow.state import create_initial_state
from workflow.nodes import (
    product_node, market_node, competitor_node,
    strategy_node, content_node, comprehensive_node,
)
from init_knowledge_base import init_market_kb, init_competitor_kb
from app_format import (
    format_product, format_market, format_competitor,
    format_strategy, format_content_section,
    format_comprehensive,
)

from agents import chat_agent, cs_agent, social_agent
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

# ========== 文件上传配置 ==========
UPLOAD_DIR = os.path.join(config.BASE_DIR, "data", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".json", ".yaml", ".yml"}

# ========== 汇率缓存 ==========
_rates_cache = {"data": None, "timestamp": 0}
RATES_CACHE_TTL = 1800  # 30 分钟


# ================================================================
# 页面 HTML
# ================================================================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>您的跨境电商助手</title>
<style>
/* ========== Reset & Base ========== */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #f8fafc; color: #1e293b; line-height: 1.6; }
.container { max-width: 1000px; margin: 0 auto; padding: 20px; }
.page { display: none; }
.page.active { display: block; }

/* ========== Navbar ========== */
.navbar { position: fixed; top: 0; left: 0; right: 0; height: 56px; z-index: 1000;
          background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
          border-bottom: 1px solid #e2e8f0; display: flex; align-items: center;
          justify-content: center; padding: 0 20px; }
.navbar .logo { position: absolute; left: 20px; font-weight: 700; font-size: 16px; color: #0f172a;
                text-decoration: none; display: flex; align-items: center; gap: 6px; }
.navbar .logo:hover { color: #3b82f6; }
.nav-links { display: flex; gap: 4px; }
.nav-links a { text-decoration: none; padding: 8px 14px; border-radius: 8px;
               font-size: 14px; color: #64748b; transition: all .2s; white-space: nowrap; }
.nav-links a:hover { background: #f1f5f9; color: #334155; }
.nav-links a.active { background: #3b82f6; color: white; }
body { padding-top: 56px; }

/* ========== Homepage (Hero) ========== */
.hero { text-align: center; padding: 60px 20px 40px;
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
        border-radius: 16px; color: white; margin: 0 0 32px; }
.hero h1 { font-size: 2.4em; margin-bottom: 12px; letter-spacing: -0.5px; }
.hero p { font-size: 1.05em; color: rgba(255,255,255,0.75); max-width: 600px; margin: 0 auto 8px; }
.hero .subtitle { font-size: 0.95em; color: rgba(255,255,255,0.6); margin-bottom: 28px; }
.hero .btn-hero { display: inline-block; padding: 14px 40px; border-radius: 12px;
                  background: #3b82f6; color: white; font-size: 17px; font-weight: 700;
                  text-decoration: none; transition: all .2s; }
.hero .btn-hero:hover { background: #2563eb; transform: translateY(-2px);
                         box-shadow: 0 8px 25px rgba(59,130,246,0.3); }
.hero .hero-hint { font-size: 13px; color: rgba(255,255,255,0.45); margin-top: 16px; }

/* ---- Features ---- */
.section-title { text-align: center; font-size: 1.5em; margin-bottom: 24px; color: #0f172a; }
.features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }
.feature-card { background: white; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0;
                text-align: center; }
.feature-card .icon { font-size: 2em; margin-bottom: 12px; }
.feature-card h3 { font-size: 1.05em; margin-bottom: 8px; color: #0f172a; }
.feature-card p { font-size: 14px; color: #64748b; }

/* ---- Guide Steps ---- */
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }
.step-card { background: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0;
             display: flex; gap: 14px; align-items: flex-start; }
.step-num { width: 32px; height: 32px; border-radius: 50%; background: #3b82f6; color: white;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 14px; flex-shrink: 0; }
.step-card h4 { font-size: 15px; margin-bottom: 4px; color: #0f172a; }
.step-card p { font-size: 13px; color: #64748b; }

/* ---- Homepage description ---- */
.home-desc { background: white; border-radius: 12px; padding: 28px; border: 1px solid #e2e8f0;
             margin-bottom: 32px; }
.home-desc h3 { font-size: 1.1em; margin-bottom: 12px; color: #0f172a; }
.home-desc p { font-size: 14px; color: #475569; margin-bottom: 8px; line-height: 1.7; }
.home-desc ul { padding-left: 20px; margin: 8px 0; }
.home-desc li { font-size: 14px; color: #475569; margin: 4px 0; }

/* ========== Platforms Page ========== */
.platform-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }
.platform-card { background: white; border-radius: 14px; border: 1px solid #e2e8f0;
                 overflow: hidden; transition: box-shadow .2s; }
.platform-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
.platform-header { padding: 20px; display: flex; align-items: center; gap: 14px; }
.platform-icon { width: 44px; height: 44px; border-radius: 10px; display: flex;
                 align-items: center; justify-content: center; font-size: 22px;
                 color: white; flex-shrink: 0; }
.platform-info { flex: 1; }
.platform-info h3 { font-size: 16px; margin-bottom: 2px; }
.platform-info .tag { font-size: 11px; color: #94a3b8; }
.platform-body { padding: 0 20px 20px; font-size: 14px; color: #475569; line-height: 1.7; }
.platform-body p { margin-bottom: 6px; }
.platform-body ul { padding-left: 18px; margin: 4px 0; }
.platform-body li { font-size: 13px; margin: 3px 0; }

/* ========== Rates Page ========== */
.rates-card { background: white; border-radius: 12px; border: 1px solid #e2e8f0; padding: 24px;
              margin: 20px 0; }
.rates-header { display: flex; justify-content: space-between; align-items: center;
                margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.rates-header h3 { font-size: 16px; color: #0f172a; }
.rates-header .updated { font-size: 12px; color: #94a3b8; }
.rates-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
              gap: 10px; }
.rate-item { background: #f8fafc; border-radius: 8px; padding: 12px 14px;
             border: 1px solid #e2e8f0; }
.rate-item .pair { font-size: 12px; color: #94a3b8; margin-bottom: 2px; }
.rate-item .value { font-size: 18px; font-weight: 700; color: #0f172a; }
.rate-item .change { font-size: 11px; color: #10b981; }
.rates-refresh { text-align: center; margin-top: 16px; }
.rates-refresh .btn { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;
                      padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 13px; }
.rates-refresh .btn:hover { background: #e2e8f0; }

/* ---- Rate Modal ---- */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                 background: rgba(0,0,0,0.45); z-index: 2000;
                 display: none; align-items: center; justify-content: center;
                 backdrop-filter: blur(2px); }
.modal-overlay.active { display: flex; }
.modal { background: white; border-radius: 16px; padding: 28px;
         max-width: 720px; width: 92%; max-height: 88vh;
         overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2);
         position: relative; animation: modalIn .25s ease; }
@keyframes modalIn { from { opacity:0; transform:scale(.95) translateY(10px); } to { opacity:1; transform:scale(1) translateY(0); } }
.modal-close { position: absolute; top: 16px; right: 20px; border: none;
               background: none; font-size: 24px; cursor: pointer; color: #94a3b8;
               line-height: 1; padding: 4px; }
.modal-close:hover { color: #ef4444; }
.modal h2 { font-size: 18px; color: #0f172a; margin-bottom: 4px; }
.modal .sub { font-size: 13px; color: #94a3b8; margin-bottom: 16px; }
.modal .chart-wrap { width: 100%; height: 280px; margin: 16px 0; position: relative; }
.modal .chart-wrap canvas { width: 100%; height: 100%; }
.rate-item { cursor: pointer; transition: box-shadow .2s, transform .15s; }
.rate-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); transform: translateY(-1px); }
.rate-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 12px 0; }
.stat-box { background: #f8fafc; border-radius: 8px; padding: 10px; text-align: center; }
.stat-box .label { font-size: 11px; color: #94a3b8; }
.stat-box .val { font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 2px; }
.stat-box .val.up { color: #10b981; }
.stat-box .val.down { color: #ef4444; }
.rate-analysis { background: #f8fafc; border-radius: 10px; padding: 14px 18px; margin: 12px 0;
                 font-size: 14px; color: #475569; line-height: 1.7; }
.rate-analysis strong { color: #0f172a; }
.rate-forecast-note { font-size: 12px; color: #94a3b8; text-align: center; margin-top: 8px; }

/* ========== Analysis Page (existing) ========== */
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
.result-card { background: white; border-radius: 12px; padding: 20px;
               border: 1px solid #e2e8f0; margin: 8px 0; }
.result-card h3 { font-size: 16px; margin-bottom: 12px; color: #0f172a;
                  border-left: 3px solid #3b82f6; padding-left: 10px; }
.result-card h4 { font-size: 14px; margin: 12px 0 6px; color: #334155; }
.result-card ul { padding-left: 20px; margin: 8px 0; }
.result-card li { margin: 4px 0; line-height: 1.5; }
.result-card p { margin: 6px 0; }
.result-card .detail { color: #64748b; font-size: 13px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 10px 12px; border: 1px solid #e2e8f0; text-align: left; }
th { background: #f8fafc; font-weight: 600; color: #475569; white-space: nowrap; }
td { vertical-align: top; }
.badge { display: inline-block; font-size: 11px; padding: 2px 8px;
         border-radius: 10px; margin-left: 6px; vertical-align: middle; }
.badge-high { background: #dcfce7; color: #166534; }
.badge-medium { background: #fef9c3; color: #854d0e; }
.badge-low { background: #fee2e2; color: #991b1b; }
.market-item { background: #f8fafc; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
.market-item h4 { margin-top: 0; }
.data-source { font-size: 12px; color: #94a3b8; font-style: italic; margin-top: 4px; }
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
.sources { font-size: 12px; color: #94a3b8; margin-top: 12px; padding-top: 8px;
           border-top: 1px solid #e2e8f0; }
.sources .fallback { color: #b0b8c4; font-style: italic; font-size: 11px; }
blockquote { background: #f1f5f9; border-left: 4px solid #3b82f6; border-radius: 4px;
             padding: 12px 16px; margin: 8px 0; color: #475569; font-size: 14px; }
.empty-state { color: #94a3b8; padding: 20px; text-align: center; }
.error-box { background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px;
             padding: 12px; margin: 8px 0; font-size: 13px; color: #b91c1c; }

/* ---- File Upload ---- */
.file-upload-row { margin-top: 12px; }
.file-upload-area { background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 10px;
                   padding: 14px 18px; margin-top: 4px; transition: border-color .2s; }
.file-upload-area:hover { border-color: #3b82f6; }
.btn-file { padding: 8px 18px; border: 1px solid #cbd5e1; border-radius: 6px;
            background: white; font-size: 13px; cursor: pointer; color: #475569; }
.btn-file:hover { background: #f1f5f9; border-color: #3b82f6; color: #3b82f6; }
.file-hint { font-size: 12px; color: #94a3b8; margin-left: 10px; }
.file-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.file-tag { display: inline-flex; align-items: center; gap: 6px;
            background: #e2e8f0; border-radius: 6px; padding: 4px 10px;
            font-size: 12px; color: #334155; }
.file-tag .remove { cursor: pointer; color: #94a3b8; font-weight: bold; }
.file-tag .remove:hover { color: #ef4444; }

/* ---- Toast ---- */
#notificationContainer { position: fixed; top: 20px; right: 20px; z-index: 9999;
                         display: flex; flex-direction: column; gap: 8px; pointer-events: none; }
.toast { background: #10b981; color: white; padding: 12px 24px; border-radius: 10px;
         font-weight: 600; font-size: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
         transform: translateX(120%); transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
         max-width: 320px; pointer-events: auto; }
.toast.show { transform: translateX(0); }
.toast-error { background: #ef4444; }
.footer { text-align: center; padding: 20px 0; font-size: 12px; color: #94a3b8; }

@media (max-width: 700px) {
  .input-row { flex-direction: column; }
  .features { grid-template-columns: 1fr; }
  .steps { grid-template-columns: 1fr; }
  .platform-grid { grid-template-columns: 1fr; }
  .hero h1 { font-size: 1.6em; }
  .hero { padding: 40px 16px 30px; }
  .nav-links a { padding: 6px 10px; font-size: 13px; }
}
/* Agent 工作台样式 */
.agent-btn.active {
  color: white !important;
  background: #1e293b !important;
  border-left-color: #3b82f6 !important;
}
.agent-btn:hover {
  background: #1e293b !important;
  color: #e2e8f0 !important;
}
.stat-box .val { font-size: 20px; font-weight: 700; color: #0f172a; }
.stat-box .label { font-size: 12px; color: #94a3b8; }
.customer-item { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; cursor: pointer; }
.customer-item:hover { background: #f1f5f9; }
.customer-item .status { display: inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
.status.online { background:#10b981; }
.status.offline { background:#94a3b8; }
</style>
</head>
<body>

<!-- ==================== Navbar ==================== -->
<nav class="navbar">
  <a href="#home" class="logo">🌍 您的跨境电商助手</a>
  <div class="nav-links">
    <a href="#home">首页</a>
    <a href="#analyze">全面产品分析</a>
    <a href="#workspace">Agent工作台</a>
    <a href="#platforms">海外平台介绍</a>
    <a href="#rates">汇率咨询</a>
  </div>
</nav>

<!-- ==================== Page: Home ==================== -->
<div id="page-home" class="page active">
<div class="container">
  <div class="hero">
    <h1>🌍 您的跨境电商助手</h1>
    <p class="subtitle">AI-powered Export Marketing Assistant</p>
    <p>从产品分析到营销内容生成，AI 驱动的一站式解决方案</p>
    <p>面向中小制造企业与个人卖家，助力中国品牌高效出海</p>
    <div style="margin-top:28px"><a href="#analyze" class="btn-hero">🚀 开始使用 →</a></div>
    <p class="hero-hint">无需注册 · 输入产品信息即可开始 · 全程 AI 驱动</p>
  </div>

  <div class="home-desc">
    <h3>🤖 什么是您的跨境电商助手？</h3>
    <p>这是一个面向中小制造企业和跨境电商卖家的 AI 运营工具。你只需要输入产品名称和描述，系统就能自动完成从市场分析到营销内容生成的全流程——就像有一个专业的跨境运营团队在为你工作。</p>
    <p><strong>核心能力：</strong></p>
    <ul>
      <li><strong>产品智能分析</strong> — AI 自动分类、提炼核心卖点、构建用户画像、定位用户痛点</li>
      <li><strong>全球市场洞察</strong> — 覆盖 9 大品类 × 美欧市场数据，智能判断目标市场机会与风险</li>
      <li><strong>竞品策略对比</strong> — 识别主要竞品、分析优劣势、挖掘差异化切入点</li>
      <li><strong>营销策略生成</strong> — 品牌定位、渠道建议、内容方向一站式输出</li>
      <li><strong>多平台内容创作</strong> — 自动生成 Amazon Listing、TikTok 脚本、外贸开发信、直播话术（中英双语）</li>
    </ul>
  </div>

  <h3 class="section-title">核心功能</h3>
  <div class="features">
    <div class="feature-card">
      <div class="icon">📊</div>
      <h3>智能产品分析</h3>
      <p>AI 自动完成产品分类、卖点提炼、用户画像和痛点分析，精准定位产品优势</p>
    </div>
    <div class="feature-card">
      <div class="icon">🌏</div>
      <h3>全球市场洞察</h3>
      <p>基于 9 大品类行业知识库，智能匹配目标市场，分析竞争格局和进入策略</p>
    </div>
    <div class="feature-card">
      <div class="icon">✍️</div>
      <h3>多平台文案编写</h3>
      <p>自动生成中英双语的 Amazon 详情、TikTok 脚本、B2B 开发信和直播话术</p>
    </div>
  </div>

  <h3 class="section-title">三步上手</h3>
  <div class="steps">
    <div class="step-card">
      <div class="step-num">1</div>
      <div><h4>输入产品信息</h4><p>填写产品名称和描述，或上传 PDF/DOCX 产品资料</p></div>
    </div>
    <div class="step-card">
      <div class="step-num">2</div>
      <div><h4>AI 自动分析</h4><p>系统依次完成产品、市场、竞品、策略分析，实时推送进度</p></div>
    </div>
    <div class="step-card">
      <div class="step-num">3</div>
      <div><h4>获取营销方案</h4><p>查阅分析报告，直接使用生成的营销内容，快速启动海外推广</p></div>
    </div>
  </div>
</div>
</div>

<!-- ==================== Page: Analyze ==================== -->
<div id="page-analyze" class="page">
<div class="container">
<div class="header">
<h1>🌍 AI 跨境出海运营助手</h1>
<p>AI-powered Export Marketing Assistant · Demo</p>
</div>
<div class="flow">
<span>📄 产品资料</span><span>→</span><span>📚 RAG 知识检索</span>
<span>→</span><span>🤖 AI 分析</span><span>→</span><span>🎯 营销策略</span>
<span>→</span><span>✍️ 文案编写</span>
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
<div class="file-upload-row">
<label>上传产品资料（可选）</label>
<div class="file-upload-area">
<input type="file" id="fileInput" multiple accept=".pdf,.docx,.txt,.md,.json" hidden>
<button class="btn btn-file" onclick="document.getElementById('fileInput').click()">📎 选择文件</button>
<span class="file-hint">支持 PDF / DOCX / TXT / MD / JSON</span>
<div id="fileList" class="file-list"></div>
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
<span id="s5">⬜ 文案编写</span><span>→</span>
<span id="s6">⬜ 综合报告</span>
</div>
<div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
<div class="progress-text" id="progressText">等待开始...</div>
</div>

<div class="tabs" id="tabsSection">
<div class="tab-header" id="tabHeaders"></div>
<div id="tabContents"></div>
</div>

<div id="errorBox" class="error-box" style="display:none"></div>

<div class="footer">⚠️ AI 辅助分析 · 基于预置知识库生成 · 仅供 Demo 演示参考</div>
</div>
</div>
<!-- ==================== Page: Workspace ==================== -->
<div id="page-workspace" class="page">
<div class="container">
  <div class="header"><h1>🛠️ Agent 工作台</h1><p>选择左侧 Agent 开始操作</p></div>
  <div style="display:flex; gap:20px; margin-top:16px;">
    <!-- 侧边栏 -->
    <div style="width:200px; flex-shrink:0; background:#0f172a; border-radius:12px; padding:12px 0; color:white; height:fit-content;">
      <button onclick="switchAgent('analysis')" class="agent-btn active" data-agent="analysis" style="display:block; width:100%; padding:14px 20px; background:transparent; border:none; color:#94a3b8; text-align:left; font-size:14px; cursor:pointer; border-left:3px solid transparent;">🤖 分析助手</button>
      <button onclick="switchAgent('chat')" class="agent-btn" data-agent="chat" style="display:block; width:100%; padding:14px 20px; background:transparent; border:none; color:#94a3b8; text-align:left; font-size:14px; cursor:pointer; border-left:3px solid transparent;">💬 AI 聊天</button>
      <button onclick="switchAgent('customer-service')" class="agent-btn" data-agent="customer-service" style="display:block; width:100%; padding:14px 20px; background:transparent; border:none; color:#94a3b8; text-align:left; font-size:14px; cursor:pointer; border-left:3px solid transparent;">🛒 客服助手</button>
      <button onclick="switchAgent('marketing')" class="agent-btn" data-agent="marketing" style="display:block; width:100%; padding:14px 20px; background:transparent; border:none; color:#94a3b8; text-align:left; font-size:14px; cursor:pointer; border-left:3px solid transparent;">📣 营销助手</button>
    </div>
    <!-- 右侧工作区 -->
    <div style="flex:1; background:white; border-radius:12px; padding:20px; border:1px solid #e2e8f0; min-height:400px;">
      <!-- 分析助手 -->
      <div id="agent-analysis" class="agent-content" style="display:block;">
        <h3>🤖 分析助手</h3>
        <p>使用原有的"全面产品分析"功能进行深度市场分析。</p>
        <a href="#analyze" class="btn btn-primary" style="display:inline-block; margin-top:12px;">前往分析页面 →</a>
      </div>
      <!-- AI 聊天 -->
      <div id="agent-chat" class="agent-content" style="display:none;">
        <h3>💬 AI 聊天</h3>
        <div id="chatMessages" style="height:300px; overflow-y:auto; border:1px solid #e2e8f0; border-radius:8px; padding:12px; margin-bottom:12px; background:#f8fafc;">
          <div class="chat-bot" style="text-align:left; margin:8px 0; background:white; padding:10px; border-radius:8px; max-width:80%; display:inline-block; border:1px solid #e2e8f0;">你好！我是你的跨境电商助手，有什么可以帮你？</div>
        </div>
        <div style="display:flex; gap:8px;">
          <input type="text" id="chatInput" placeholder="输入消息..." style="flex:1; padding:10px; border:1px solid #cbd5e1; border-radius:8px;">
          <button onclick="sendChatMessage()" class="btn btn-primary">发送</button>
        </div>
      </div>
      <!-- 客服助手 -->
      <div id="agent-customer-service" class="agent-content" style="display:none;">
        <h3>🛒 客服助手</h3>
        <div id="csStats" style="display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap;">
          <div class="stat-box" style="background:#f8fafc; padding:12px 20px; border-radius:8px; border:1px solid #e2e8f0; flex:1; min-width:120px;"><div class="label">今日收入</div><div class="val" id="csRevenue">$0</div></div>
          <div class="stat-box" style="background:#f8fafc; padding:12px 20px; border-radius:8px; border:1px solid #e2e8f0; flex:1; min-width:120px;"><div class="label">今日订单</div><div class="val" id="csOrders">0</div></div>
          <div class="stat-box" style="background:#f8fafc; padding:12px 20px; border-radius:8px; border:1px solid #e2e8f0; flex:1; min-width:120px;"><div class="label">待处理消息</div><div class="val" id="csPending">0</div></div>
        </div>
        <div style="display:flex; gap:16px;">
          <div style="width:200px; flex-shrink:0; border-right:1px solid #e2e8f0; padding-right:12px;">
            <h4 style="font-size:14px;">顾客列表</h4>
            <div id="csCustomerList"></div>
          </div>
          <div style="flex:1;">
            <div id="csChatWindow" style="border:1px solid #e2e8f0; border-radius:8px; padding:12px; min-height:150px; background:#f8fafc;">
              <p class="empty-state">选择一位顾客查看对话</p>
            </div>
            <div style="margin-top:8px; display:flex; gap:8px;">
              <input type="text" id="csReplyInput" placeholder="输入回复..." style="flex:1; padding:8px; border:1px solid #cbd5e1; border-radius:6px;">
              <button onclick="csSendReply()" class="btn btn-primary" style="padding:8px 16px; font-size:13px;">发送</button>
              <button onclick="csGenerateReply()" class="btn btn-secondary" style="padding:8px 16px; font-size:13px;">✨ AI 生成回复</button>
            </div>
          </div>
        </div>
      </div>
      <!-- 营销助手 -->
      <div id="agent-marketing" class="agent-content" style="display:none;">
        <h3>📣 营销助手</h3>
        <div style="display:flex; gap:12px; margin-bottom:12px;">
          <input type="text" id="marketingProduct" placeholder="输入产品名称..." style="flex:1; padding:10px; border:1px solid #cbd5e1; border-radius:8px;" value="X100 智能运动手表">
          <button onclick="generateSocialPost()" class="btn btn-primary">生成帖子</button>
        </div>
        <div id="postPreview" style="border:1px solid #e2e8f0; border-radius:8px; padding:16px; background:#f8fafc; min-height:150px;">
          <p class="empty-state">点击"生成帖子"预览内容</p>
        </div>
        <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
          <button onclick="publishTo('x')" class="btn btn-secondary" style="background:#000; color:white;">𝕏 发布到 X</button>
          <button onclick="publishTo('facebook')" class="btn btn-secondary" style="background:#1877f2; color:white;">📘 发布到 Facebook</button>
          <button onclick="publishTo('instagram')" class="btn btn-secondary" style="background:#e4405f; color:white;">📸 发布到 Instagram</button>
        </div>
      </div>
    </div>
  </div>
</div>
</div>

<!-- ==================== Page: Platforms ==================== -->
<div id="page-platforms" class="page">
<div class="container">
<div class="header"><h1>🌐 海外平台介绍</h1><p>主流跨境电商与社交媒体平台概览</p></div>
<div class="platform-grid">
  <div class="platform-card">
    <div class="platform-header">
      <div class="platform-icon" style="background:#FF9900">🛒</div>
      <div class="platform-info"><h3>Amazon</h3><span class="tag">全球最大电商平台</span></div>
    </div>
    <div class="platform-body">
      <p>Amazon 是全球最大的跨境电商平台，覆盖北美、欧洲、亚太等 20+ 国家市场。年 GMV 超 5000 亿美元，是出海卖家的首选渠道。</p>
      <ul>
        <li><strong>核心优势</strong>：Prime 会员体系带来高转化率，FBA 物流解决跨境配送痛点</li>
        <li><strong>适合品类</strong>：3C 电子、家居、运动户外、美妆个护</li>
        <li><strong>入驻门槛</strong>：月租 $39.99，专业卖家账户不限品类</li>
        <li><strong>运营要点</strong>：Listing 优化、PPC 广告、Review 管理为核心技能</li>
      </ul>
    </div>
  </div>
  <div class="platform-card">
    <div class="platform-header">
      <div class="platform-icon" style="background:#E5322D">🏷️</div>
      <div class="platform-info"><h3>eBay</h3><span class="tag">全球老牌 C2C/B2C 平台</span></div>
    </div>
    <div class="platform-body">
      <p>eBay 是全球最早的电商平台之一，以拍卖和固定价格模式运营，在二手商品和收藏品领域具有独特优势。</p>
      <ul>
        <li><strong>核心优势</strong>：入驻门槛低，适合小卖家起步，品类限制少</li>
        <li><strong>适合品类</strong>：汽配零件、收藏品、电子产品、二手商品</li>
        <li><strong>入驻门槛</strong>：个人卖家免费，店铺订阅 $21.95/月起</li>
        <li><strong>运营要点</strong>：拍卖玩法适合稀缺品，定价策略比 Amazon 更灵活</li>
      </ul>
    </div>
  </div>
  <div class="platform-card">
    <div class="platform-header">
      <div class="platform-icon" style="background:#000000">🎵</div>
      <div class="platform-info"><h3>TikTok Shop</h3><span class="tag">短视频社交电商新势力</span></div>
    </div>
    <div class="platform-body">
      <p>TikTok Shop 将短视频内容与电商购物深度融合，2024 年全球 GMV 超 200 亿美元，是增长最快的社交电商平台。</p>
      <ul>
        <li><strong>核心优势</strong>：内容驱动爆款，流量获取成本低于 Amazon</li>
        <li><strong>适合品类</strong>：服装、美妆、新奇特小商品、家居好物</li>
        <li><strong>入驻门槛</strong>：美国站需美国公司或合作 TikTok 达人带货</li>
        <li><strong>运营要点</strong>：短视频内容质量决定转化，达人合作是关键杠杆</li>
      </ul>
    </div>
  </div>
  <div class="platform-card">
    <div class="platform-header">
      <div class="platform-icon" style="background:#FF0000">▶️</div>
      <div class="platform-info"><h3>YouTube</h3><span class="tag">全球最大视频平台</span></div>
    </div>
    <div class="platform-body">
      <p>YouTube 是全球最大的视频内容平台，月活用户超 25 亿。深度产品评测和开箱视频对购买决策影响巨大。</p>
      <ul>
        <li><strong>核心优势</strong>：长视频深度展示产品，SEO 长尾流量稳定，内容生命周期长</li>
        <li><strong>适合品类</strong>：科技产品、美妆教程、工具器械、户外装备</li>
        <li><strong>变现方式</strong>：YouTube Shopping 联盟营销，品牌合作推广</li>
        <li><strong>运营要点</strong>：产品评测视频是入局最佳切入点，注重搜索关键词优化</li>
      </ul>
    </div>
  </div>
  <div class="platform-card">
    <div class="platform-header">
      <div class="platform-icon" style="background:#000000">𝕏</div>
      <div class="platform-info"><h3>X (Twitter)</h3><span class="tag">实时社交与品牌传播平台</span></div>
    </div>
    <div class="platform-body">
      <p>X 是全球重要的实时社交平台，在品牌建设、客户服务和行业影响力方面具有独特价值。日活用户约 2.5 亿。</p>
      <ul>
        <li><strong>核心优势</strong>：实时互动强，行业 KOL 密度高，危机公关必备</li>
        <li><strong>适合品类</strong>：科技品牌、DTC 品牌、企业服务、潮牌</li>
        <li><strong>运营方式</strong>：品牌账号矩阵 + 行业话题参与 + 客户服务</li>
        <li><strong>运营要点</strong>：品牌人格化表达，善用 Trending Topics 借势营销</li>
      </ul>
    </div>
  </div>
  <div class="platform-card">
    <div class="platform-header">
      <div class="platform-icon" style="background:#0071CE">⭐</div>
      <div class="platform-info"><h3>Walmart</h3><span class="tag">美国最大零售巨头电商平台</span></div>
    </div>
    <div class="platform-body">
      <p>Walmart 是美国最大的零售商，其电商平台近年快速增长，线上 GMV 已超 500 亿美元，成为中国卖家的新蓝海。</p>
      <ul>
        <li><strong>核心优势</strong>：线下门店网络支撑 O2O 能力，竞争程度低于 Amazon</li>
        <li><strong>适合品类</strong>：家居、家电、运动户外、宠物用品</li>
        <li><strong>入驻门槛</strong>：邀请制 + 审核制，需美国公司或 Walmart 认可</li>
        <li><strong>运营要点</strong>：WFS 物流（类似 Amazon FBA）可提高曝光和转化</li>
      </ul>
    </div>
  </div>
</div>
<div class="footer">数据来源：各平台官方公开数据 · 仅供参考</div>
</div>
</div>

<!-- ==================== Page: Rates ==================== -->
<div id="page-rates" class="page">
<div class="container">
<div class="header"><h1>💱 汇率咨询</h1><p>主要货币兑美元汇率（每 30 分钟自动更新）· 点击任一货币查看历史走势</p></div>
<div class="rates-card">
  <div class="rates-header">
    <h3>💵 汇率表（基准: USD）</h3>
    <span class="updated" id="ratesUpdateTime">加载中...</span>
  </div>
  <div class="rates-grid" id="ratesGrid">
    <div class="rate-item" style="grid-column:1/-1;text-align:center;color:#94a3b8;">正在获取汇率数据...</div>
  </div>
  <div class="rates-refresh">
    <button class="btn" onclick="fetchRates()">🔄 手动刷新</button>
  </div>
</div>
<div class="footer">汇率数据来源: ExchangeRate-API · 仅供参考，实际交易以银行报价为准</div>
</div>
</div>

<!-- ==================== Rate Detail Modal ==================== -->
<div class="modal-overlay" id="rateModal">
  <div class="modal">
    <button class="modal-close" onclick="closeRateModal()">✕</button>
    <h2 id="rateModalTitle">USD/CNY</h2>
    <p class="sub" id="rateModalSub">近 12 个月走势</p>
    <div class="chart-wrap"><canvas id="rateChart"></canvas></div>
    <div class="rate-stats" id="rateStats"></div>
    <div class="rate-analysis" id="rateAnalysis">⏳ 分析加载中...</div>
    <div class="rate-forecast-note">📈 7 日预测基于线性趋势模型，仅供参考</div>
  </div>
</div>

<!-- ==================== Toast ==================== -->
<div id="notificationContainer"></div>

<script>
// ==================== Hash Router ====================
function navigate() {
    var hash = location.hash.slice(1) || "home";
    document.querySelectorAll(".page").forEach(function(p) { p.classList.remove("active"); });
    var page = document.getElementById("page-" + hash);
    if (page) page.classList.add("active");
    document.querySelectorAll(".nav-links a").forEach(function(a) {
        a.classList.remove("active");
        if (a.getAttribute("href") === "#" + hash) a.classList.add("active");
    });
}
window.addEventListener("hashchange", navigate);
if (!location.hash) location.hash = "home";
navigate(); // 确保首次加载时执行导航，即使用户的 hash 与预期不同

// ==================== Rates Page ====================
var RATES_CACHE = null;
async function fetchRates() {
    var grid = document.getElementById("ratesGrid");
    var timeEl = document.getElementById("ratesUpdateTime");
    if (!grid) return;
    grid.innerHTML = '<div class="rate-item" style="grid-column:1/-1;text-align:center;color:#94a3b8;">⏳ 获取中...</div>';
    try {
        var resp = await fetch("/api/rates");
        var data = await resp.json();
        if (data.error) { grid.innerHTML = '<div class="rate-item" style="grid-column:1/-1;text-align:center;color:#ef4444;">❌ ' + data.error + '</div>'; return; }
        var html = "";
        var cny = data.rates["CNY"];
        var currencies = [
            {code:"CNY",name:"人民币",flag:"🇨🇳"},
            {code:"EUR",name:"欧元",flag:"🇪🇺"},
            {code:"GBP",name:"英镑",flag:"🇬🇧"},
            {code:"JPY",name:"日元",flag:"🇯🇵"},
            {code:"KRW",name:"韩元",flag:"🇰🇷"},
            {code:"HKD",name:"港币",flag:"🇭🇰"},
            {code:"AUD",name:"澳元",flag:"🇦🇺"},
            {code:"CAD",name:"加元",flag:"🇨🇦"},
            {code:"SGD",name:"新加坡元",flag:"🇸🇬"},
            {code:"MYR",name:"马来西亚林吉特",flag:"🇲🇾"},
            {code:"THB",name:"泰铢",flag:"🇹🇭"},
            {code:"VND",name:"越南盾",flag:"🇻🇳"},
            {code:"TWD",name:"新台币",flag:"🇹🇼"}
        ];
        for (var i = 0; i < currencies.length; i++) {
            var c = currencies[i];
            var val = data.rates[c.code];
            if (!val) continue;
            var cnyVal = cny ? (val / cny).toFixed(c.code === "JPY" || c.code === "KRW" || c.code === "VND" ? 0 : 4) : "-";
            var usdVal = val.toFixed(c.code === "JPY" || c.code === "KRW" || c.code === "VND" ? 2 : 4);
            html += '<div class="rate-item" onclick="showRateDetail(\'' + c.code + '\',\'' + c.name + '\')">';
            html += '  <div class="pair">' + c.flag + ' ' + c.code + ' / ' + c.name + '</div>';
            html += '  <div class="value">' + usdVal + '</div>';
            html += '  <div class="change">≈ ' + cnyVal + ' CNY</div>';
            html += '</div>';
        }
        grid.innerHTML = html;
        if (data.updated_at) { timeEl.textContent = "上次更新: " + data.updated_at; }
    } catch(e) {
        grid.innerHTML = '<div class="rate-item" style="grid-column:1/-1;text-align:center;color:#ef4444;">❌ 获取失败: ' + e.message + '</div>';
    }
}
// Fetch rates on page show
var routerCheck = setInterval(function() {
    if (document.getElementById("page-rates").classList.contains("active") && !RATES_CACHE) {
        fetchRates(); RATES_CACHE = true;
    }
}, 500);

// ==================== Rate Detail Modal ====================
function showRateDetail(code, name) {
    var modal = document.getElementById("rateModal");
    document.getElementById("rateModalTitle").textContent = "USD / " + code;
    document.getElementById("rateModalSub").textContent = name + " · 近 12 个月走势";
    document.getElementById("rateAnalysis").textContent = "⏳ 加载中...";
    document.getElementById("rateStats").innerHTML = "";
    modal.classList.add("active");
    document.body.style.overflow = "hidden";

    fetch("/api/rates/history?target=" + code + "&months=12")
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) {
                document.getElementById("rateAnalysis").textContent = "❌ 获取失败: " + data.error;
                return;
            }
            if (!data.history || data.history.length < 2) {
                document.getElementById("rateAnalysis").textContent = "❌ 历史数据不足";
                return;
            }
            renderRateChart(data, code, name);
            renderRateStats(data.stats);
            renderRateAnalysis(data, code, name);
        })
        .catch(function(e) {
            document.getElementById("rateAnalysis").textContent = "❌ 网络错误: " + e.message;
        });
}

function closeRateModal() {
    document.getElementById("rateModal").classList.remove("active");
    document.body.style.overflow = "";
}

// Close on overlay click
document.addEventListener("click", function(e) {
    if (e.target.classList.contains("modal-overlay")) closeRateModal();
});
// Close on Escape
document.addEventListener("keydown", function(e) {
    if (e.key === "Escape") closeRateModal();
});

function renderRateChart(data, code, name) {
    var canvas = document.getElementById("rateChart");
    var rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";

    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height;
    var dpr = 2;
    ctx.scale(1, 1);

    var history = data.history || [];
    var forecast = data.forecast || [];

    // Find min/max
    var allVals = history.map(function(h) { return h.value; });
    if (forecast.length) allVals = allVals.concat(forecast.map(function(f) { return f.value; }));
    var minVal = Math.min.apply(null, allVals);
    var maxVal = Math.max.apply(null, allVals);
    var range = maxVal - minVal || 0.01;
    var pad = range * 0.15;
    var yMin = minVal - pad;
    var yMax = maxVal + pad;

    var margin = { top: 20 * dpr, right: 20 * dpr, bottom: 35 * dpr, left: 55 * dpr };
    var plotW = W - margin.left - margin.right;
    var plotH = H - margin.top - margin.bottom;

    function xPos(i, total) { return margin.left + (i / (total - 1 || 1)) * plotW; }
    function yPos(v) { return margin.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH; }

    // Clear
    ctx.clearRect(0, 0, W, H);

    // Grid lines
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 1 * dpr;
    var gridLines = 5;
    for (var g = 0; g <= gridLines; g++) {
        var y = margin.top + (g / gridLines) * plotH;
        ctx.beginPath(); ctx.moveTo(margin.left, y); ctx.lineTo(W - margin.right, y); ctx.stroke();
        var label = (yMax - (g / gridLines) * (yMax - yMin)).toFixed(4);
        ctx.fillStyle = "#94a3b8"; ctx.font = (11 * dpr) + "px sans-serif"; ctx.textAlign = "right";
        ctx.fillText(label, margin.left - 6 * dpr, y + 4 * dpr);
    }

    // X-axis labels (monthly)
    ctx.fillStyle = "#94a3b8"; ctx.font = (11 * dpr) + "px sans-serif"; ctx.textAlign = "center";
    var total = history.length;
    var step = Math.max(1, Math.floor(total / 10));
    for (var i = 0; i < total; i += step) {
        var x = xPos(i, total);
        var dateStr = history[i].date.slice(5, 10);
        ctx.fillText(dateStr, x, H - margin.bottom + 16 * dpr);
    }

    // Y-axis title
    ctx.save();
    ctx.translate(14 * dpr, margin.top + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = "#94a3b8"; ctx.font = (11 * dpr) + "px sans-serif"; ctx.textAlign = "center";
    ctx.fillText("USD / " + code, 0, 0);
    ctx.restore();

    // Draw area fill
    ctx.beginPath();
    ctx.moveTo(xPos(0, total), yPos(history[0].value));
    for (var i = 0; i < total; i++) { ctx.lineTo(xPos(i, total), yPos(history[i].value)); }
    ctx.lineTo(xPos(total - 1, total), yPos(history[total - 1].value));
    ctx.lineTo(xPos(total - 1, total), H - margin.bottom);
    ctx.lineTo(xPos(0, total), H - margin.bottom);
    ctx.closePath();
    var grad = ctx.createLinearGradient(0, margin.top, 0, H - margin.bottom);
    grad.addColorStop(0, "rgba(59,130,246,0.12)");
    grad.addColorStop(1, "rgba(59,130,246,0.01)");
    ctx.fillStyle = grad;
    ctx.fill();

    // Draw history line
    ctx.beginPath();
    ctx.moveTo(xPos(0, total), yPos(history[0].value));
    for (var i = 0; i < total; i++) { ctx.lineTo(xPos(i, total), yPos(history[i].value)); }
    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2 * dpr;
    ctx.lineJoin = "round";
    ctx.stroke();

    // Draw forecast (dashed)
    if (forecast.length > 0) {
        var fTotal = forecast.length;
        ctx.setLineDash([4 * dpr, 4 * dpr]);
        ctx.beginPath();
        ctx.moveTo(xPos(total - 1, total), yPos(history[total - 1].value));
        for (var i = 0; i < fTotal; i++) {
            var fx = W - margin.right + ((i + 1) / (fTotal + 1)) * (margin.right / 2);
            fx = Math.min(fx, W - margin.right);
            ctx.lineTo(fx, yPos(forecast[i].value));
        }
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 2 * dpr;
        ctx.stroke();
        ctx.setLineDash([]);

        // "预测" label
        ctx.fillStyle = "#f59e0b";
        ctx.font = (11 * dpr) + "px sans-serif";
        ctx.textAlign = "left";
        ctx.fillText("→ 7日预测", W - margin.right - 60 * dpr, margin.top + 14 * dpr);
    }
}

function renderRateStats(stats) {
    var html = "";
    var changeClass = (stats.change || 0) >= 0 ? "up" : "down";
    var changeSign = (stats.change || 0) >= 0 ? "+" : "";
    html += '<div class="stat-box"><div class="label">当前</div><div class="val">' + (stats.end || "-").toFixed(4) + '</div></div>';
    html += '<div class="stat-box"><div class="label">12月最高</div><div class="val">' + (stats.high || "-").toFixed(4) + '</div></div>';
    html += '<div class="stat-box"><div class="label">12月最低</div><div class="val">' + (stats.low || "-").toFixed(4) + '</div></div>';
    html += '<div class="stat-box"><div class="label ' + changeClass + '">变动</div><div class="val ' + changeClass + '">' + changeSign + (stats.change || 0).toFixed(2) + '%</div></div>';
    document.getElementById("rateStats").innerHTML = html;
}

function renderRateAnalysis(data, code, name) {
    var stats = data.stats || {};
    var history = data.history || [];
    var forecast = data.forecast || [];

    if (!stats || !history.length) {
        document.getElementById("rateAnalysis").textContent = "数据不足，无法生成分析";
        return;
    }

    var change = stats.change || 0;
    var direction = change >= 0 ? "升值" : "贬值";
    var dirEmoji = change >= 0 ? "📈" : "📉";
    var stability = "波动较大";
    var std = 0;
    var vals = history.map(function(h) { return h.value; });
    var mean = vals.reduce(function(a,b) { return a+b; }, 0) / vals.length;
    std = Math.sqrt(vals.reduce(function(s,v) { return s + (v-mean)*(v-mean); }, 0) / vals.length);
    var relStd = (std / mean * 100);
    if (relStd < 1) stability = "波动较小";
    else if (relStd < 3) stability = "波动适中";

    var trendDesc = "在过去 12 个月中，" + code + " (" + name + ") 兑美元整体呈";
    if (Math.abs(change) < 1) trendDesc += "基本持平的趋势";
    else if (Math.abs(change) < 5) trendDesc += "平稳" + (change > 0 ? "上升" : "下降") + "趋势，变动约 " + Math.abs(change).toFixed(1) + "%";
    else trendDesc += "明显" + (change > 0 ? "升值" : "贬值") + "趋势，变动约 " + Math.abs(change).toFixed(1) + "%";

    var forecastDesc = "";
    if (forecast.length > 0) {
        var fChange = ((forecast[forecast.length-1].value - history[history.length-1].value) / history[history.length-1].value * 100);
        var fDir = fChange >= 0 ? "小幅升值" : "小幅贬值";
        forecastDesc = " 根据线性趋势模型，未来 7 天预计" + fDir + "约 " + Math.abs(fChange).toFixed(1) + "%。";
    }

    var analysis = dirEmoji + " <strong>" + code + " " + direction + "</strong> · " + stability + " · 变动 " + Math.abs(change).toFixed(1) + "%<br><br>";
    analysis += trendDesc + "。" + forecastDesc + "<br><br>";
    analysis += "⚡ 最高 " + stats.high.toFixed(4) + "，最低 " + stats.low.toFixed(4) + "，均值 " + (stats.average || "").toFixed(4) + "。";

    document.getElementById("rateAnalysis").innerHTML = analysis;
}

// ==================== Analysis Page (existing) ====================
const TOTAL_STEPS = 6;
const TAB_NAMES = ["📋 产品分析","🌍 市场分析","⚔️ 竞品分析","🎯 营销策略","✍️ 文案编写","📋 综合报告"];
const NOTIFY_MSG = {
    1: "✅ 产品分析生成完毕！",
    2: "🌍 市场分析生成完毕！",
    3: "⚔️ 竞品分析生成完毕！",
    4: "🎯 营销策略生成完毕！",
    5: "✍️ 文案编写完毕！",
    6: "📋 综合报告生成完毕！"
};
const STEP_NAMES = ["产品分析", "市场分析", "竞品分析", "营销策略", "文案编写", "综合报告"];

function showNotification(msg, isError) {
    const container = document.getElementById("notificationContainer");
    const toast = document.createElement("div");
    toast.className = "toast" + (isError ? " toast-error" : "");
    toast.textContent = msg;
    container.appendChild(toast);
    requestAnimationFrame(function() { toast.classList.add("show"); });
    setTimeout(function() {
        toast.classList.remove("show");
        setTimeout(function() { toast.remove(); }, 400);
    }, 3000);
}

function loadSample() {
    document.getElementById("productName").value = "X100 智能运动手表";
    document.getElementById("productDesc").value =
        "IP68防水 · 7天超长续航 · 24小时健康监测（心率/血氧/睡眠）\n" +
        "铝合金表壳 · 1.43英寸AMOLED屏幕 · 蓝牙5.3\n" +
        "GPS运动轨迹追踪 · 100+运动模式 · 兼容iOS/Android\n" +
        "磁吸充电 · 仅重52g · 支持支付宝/微信离线支付";
}

function setProgress(step) {
    const pct = Math.min(Math.round((step - 1) / TOTAL_STEPS * 100), 100);
    document.getElementById("progressFill").style.width = pct + "%";
    const labels = ["等待开始...", "📋 正在分析产品资料...", "🌍 正在分析市场数据...",
                    "⚔️ 正在分析竞品信息...", "🎯 正在制定营销策略...",
                    "✍️ 正在编写营销文案...", "📋 正在生成综合报告...", "✅ 分析完成！"];
    document.getElementById("progressText").textContent = labels[Math.min(step, TOTAL_STEPS + 1)] || "";
    for (let i = 1; i <= TOTAL_STEPS; i++) {
        const el = document.getElementById("s" + i);
        if (i < step) { el.className = "done"; el.innerHTML = "✅ " + STEP_NAMES[i - 1]; }
        else if (i === step) { el.className = "current"; el.innerHTML = "🔄 " + STEP_NAMES[i - 1]; }
        else { el.className = ""; el.innerHTML = "⬜ " + STEP_NAMES[i - 1]; }
    }
}

function showError(msg) {
    document.getElementById("errorBox").style.display = "block";
    document.getElementById("errorBox").textContent = "⚠️ " + msg;
    showNotification("⚠️ " + msg, true);
}

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

function handleStreamEvent(event) {
    var step = event.step;
    if (step === TOTAL_STEPS + 1) {
        document.getElementById("analyzeBtn").disabled = false;
        setProgress(TOTAL_STEPS + 1);
        if (event.errors && event.errors.length > 0) {
            var errDiv = document.createElement("div");
            errDiv.className = "error-box";
            errDiv.textContent = "⚠️ 执行警告（不影响已生成的结果）: " + event.errors.join("; ");
            document.getElementById("tabContents").appendChild(errDiv);
        }
        return;
    }
    setProgress(step + 1);
    var msg = NOTIFY_MSG[step];
    if (msg) showNotification(msg);
    renderTabContent(step - 1, event.html);
}

// File upload
var uploadedFilePaths = [];
document.addEventListener("DOMContentLoaded", function() {
    var fi = document.getElementById("fileInput");
    if (fi) {
        fi.addEventListener("change", function() {
            var list = document.getElementById("fileList");
            if (!list) return;
            list.innerHTML = "";
            for (var i = 0; i < this.files.length; i++) {
                var tag = document.createElement("span");
                tag.className = "file-tag";
                tag.innerHTML = '📎 ' + this.files[i].name + ' <span class="remove" onclick="removeFile(' + i + ')">✕</span>';
                list.appendChild(tag);
            }
        });
    }
});

function removeFile(index) {
    var input = document.getElementById("fileInput");
    var dt = new DataTransfer();
    for (var i = 0; i < input.files.length; i++) {
        if (i !== index) dt.items.add(input.files[i]);
    }
    input.files = dt.files;
    input.dispatchEvent(new Event("change"));
}

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

    uploadedFilePaths = [];
    var fileInput = document.getElementById("fileInput");
    if (fileInput && fileInput.files.length > 0) {
        var formData = new FormData();
        for (var i = 0; i < fileInput.files.length; i++) {
            formData.append("files", fileInput.files[i]);
        }
        try {
            var uploadResp = await fetch("/upload", { method: "POST", body: formData });
            var uploadResult = await uploadResp.json();
            uploadedFilePaths = uploadResult.uploaded_files || [];
            if (uploadResult.errors && uploadResult.errors.length > 0) {
                showNotification("⚠️ " + uploadResult.errors[0], true);
            }
        } catch (e) {
            showNotification("⚠️ 文件上传失败: " + e.message, true);
        }
    }

    try {
        var resp = await fetch("/analyze-stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                product_name: name,
                product_description: desc,
                uploaded_files: uploadedFilePaths
            })
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
                    } catch (e) { console.warn("Event parse:", e); }
                }
            }
        }
    } catch (e) {
        showError("网络错误: " + e.message);
        document.getElementById("analyzeBtn").disabled = false;
    }
}

function switchTab(index) {
    var btns = document.querySelectorAll(".tab-btn");
    for (var i = 0; i < btns.length; i++) { btns[i].className = "tab-btn" + (i === index ? " active" : ""); }
    var contents = document.querySelectorAll(".tab-content");
    for (var i = 0; i < contents.length; i++) { contents[i].className = "tab-content" + (i === index ? " active" : ""); }
}

function switchSubTab(index) {
    var nav = document.querySelector(".sub-tabs");
    if (!nav) return;
    var btns = nav.querySelectorAll(".sub-tab-btn");
    for (var i = 0; i < btns.length; i++) { btns[i].className = "sub-tab-btn" + (i === index ? " active" : ""); }
    var container = nav.nextElementSibling;
    if (!container) return;
    var contents = container.querySelectorAll(".sub-tab-content");
    for (var i = 0; i < contents.length; i++) { contents[i].className = "sub-tab-content" + (i === index ? " active" : ""); }
}
// ==================== Agent 工作台 ====================
let currentAgent = 'analysis';
let selectedCustomer = null;
let chatHistory = [];

function switchAgent(agent) {
    document.querySelectorAll('.agent-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.agent-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('agent-' + agent).style.display = 'block';
    document.querySelector(`.agent-btn[data-agent="${agent}"]`).classList.add('active');
    currentAgent = agent;
    if (agent === 'customer-service') loadCustomerService();
}

// 聊天
async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    const chatDiv = document.getElementById('chatMessages');
    const userDiv = document.createElement('div');
    userDiv.className = 'chat-user';
    userDiv.style.textAlign = 'right';
    userDiv.style.margin = '8px 0';
    userDiv.innerHTML = `<span style="background:#3b82f6; color:white; padding:10px; border-radius:8px; display:inline-block; max-width:80%;">${msg}</span>`;
    chatDiv.appendChild(userDiv);
    chatDiv.scrollTop = chatDiv.scrollHeight;

    chatHistory.push({role: 'user', content: msg});
    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg, history: chatHistory})
        });
        const data = await resp.json();
        const reply = data.reply || '（无回复）';
        chatHistory.push({role: 'assistant', content: reply});
        const botDiv = document.createElement('div');
        botDiv.className = 'chat-bot';
        botDiv.style.textAlign = 'left';
        botDiv.style.margin = '8px 0';
        botDiv.innerHTML = `<span style="background:white; padding:10px; border-radius:8px; display:inline-block; max-width:80%; border:1px solid #e2e8f0;">${reply}</span>`;
        chatDiv.appendChild(botDiv);
        chatDiv.scrollTop = chatDiv.scrollHeight;
    } catch (e) {
        alert('发送失败: ' + e.message);
    }
}

// 客服
let csCustomers = [];

async function loadCustomerService() {
    try {
        const [salesRes, queueRes] = await Promise.all([
            fetch('/api/cs/sales', {method: 'POST'}),
            fetch('/api/cs/queue', {method: 'POST'})
        ]);
        const sales = (await salesRes.json()).data || {};
        const queue = (await queueRes.json()).data || [];
        document.getElementById('csRevenue').textContent = '$' + (sales.today_revenue || 0);
        document.getElementById('csOrders').textContent = sales.today_orders || 0;
        document.getElementById('csPending').textContent = sales.pending_messages || 0;
        csCustomers = queue;
        renderCustomerList(queue);
        if (queue.length) selectCustomer(queue[0].id);
    } catch (e) {
        console.error('加载客服数据失败:', e);
    }
}

function renderCustomerList(customers) {
    const list = document.getElementById('csCustomerList');
    list.innerHTML = '';
    customers.forEach(c => {
        const div = document.createElement('div');
        div.className = 'customer-item';
        div.innerHTML = `<span class="status ${c.status}"></span> ${c.name}<br><span style="font-size:12px;color:#94a3b8;">${c.last_message}</span>`;
        div.onclick = () => selectCustomer(c.id);
        list.appendChild(div);
    });
}

function selectCustomer(id) {
    selectedCustomer = csCustomers.find(c => c.id === id);
    if (!selectedCustomer) return;
    const win = document.getElementById('csChatWindow');
    win.innerHTML = `<div style="font-weight:bold;">${selectedCustomer.name}</div>
                     <div style="font-size:13px;color:#475569;margin:4px 0;">${selectedCustomer.last_message}</div>
                     <div style="font-size:12px;color:#94a3b8;">${selectedCustomer.time} · 产品: ${selectedCustomer.product}</div>`;
    document.getElementById('csReplyInput').value = '';
}

async function csGenerateReply() {
    if (!selectedCustomer) { alert('请先选择一位顾客'); return; }
    try {
        const resp = await fetch('/api/cs/reply', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: selectedCustomer.last_message, product: selectedCustomer.product})
        });
        const data = await resp.json();
        document.getElementById('csReplyInput').value = data.reply || '';
    } catch (e) {
        alert('生成回复失败: ' + e.message);
    }
}

function csSendReply() {
    const input = document.getElementById('csReplyInput');
    const reply = input.value.trim();
    if (!reply) return;
    alert('✅ 已发送回复给 ' + selectedCustomer.name + '：' + reply);
    input.value = '';
}

// 营销
let currentPost = null;

async function generateSocialPost() {
    const product = document.getElementById('marketingProduct').value.trim();
    if (!product) { alert('请输入产品名称'); return; }
    try {
        const resp = await fetch('/api/social/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({product_name: product})
        });
        const data = await resp.json();
        currentPost = data;
        let html = `<div style="margin-bottom:8px;"><strong>X (Twitter):</strong><br><textarea id="postX" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;" rows="2">${data.x_post || ''}</textarea></div>`;
        html += `<div style="margin-bottom:8px;"><strong>Facebook:</strong><br><textarea id="postFacebook" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;" rows="2">${data.facebook_post || ''}</textarea></div>`;
        html += `<div style="margin-bottom:8px;"><strong>Instagram:</strong><br><textarea id="postInstagram" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;" rows="2">${data.instagram_post || ''}</textarea></div>`;
        html += `<div style="font-size:12px;color:#94a3b8;">推荐平台: ${data.best_platform || 'x'} · ${data.reasoning || ''}</div>`;
        document.getElementById('postPreview').innerHTML = html;
    } catch (e) {
        alert('生成失败: ' + e.message);
    }
}

async function publishTo(platform) {
    let content = '';
    if (platform === 'x') content = document.getElementById('postX')?.value;
    else if (platform === 'facebook') content = document.getElementById('postFacebook')?.value;
    else if (platform === 'instagram') content = document.getElementById('postInstagram')?.value;
    if (!content) { alert('请先生成帖子或填写内容'); return; }
    try {
        const resp = await fetch('/api/social/publish', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({platform: platform, content: content})
        });
        const data = await resp.json();
        alert(data.message || '发布成功！');
    } catch (e) {
        alert('发布失败: ' + e.message);
    }
}

// 初始化工作台
if (document.getElementById('agent-analysis')) {
    switchAgent('analysis');
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


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """上传产品资料文件，保存到临时目录，返回文件路径列表"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    saved = []
    errors = []
    for file in files:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{file.filename}: 不支持的文件格式（支持 PDF/DOCX/TXT/MD/JSON）")
            continue
        safe_name = f"{int(time.time() * 1000)}_{file.filename}"
        save_path = os.path.join(UPLOAD_DIR, safe_name)
        try:
            with open(save_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved.append(save_path)
        except Exception as e:
            errors.append(f"{file.filename}: 保存失败 - {e}")
    return {"uploaded_files": saved, "errors": errors}


RATES_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

@app.get("/api/rates")
async def get_rates():
    """获取实时汇率（每 30 分钟缓存）"""
    now = time.time()
    if _rates_cache["data"] and now - _rates_cache["timestamp"] < RATES_CACHE_TTL:
        return _rates_cache["data"]

    try:
        loop = asyncio.get_event_loop()
        req = urllib.request.Request(
            RATES_API_URL,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=15)
        )
        raw = json.loads(resp.read().decode("utf-8"))
        rates = raw.get("rates", {})

        # 筛选常用货币
        curated = {
            "base": "USD",
            "rates": {
                "CNY": rates.get("CNY"),
                "EUR": rates.get("EUR"),
                "GBP": rates.get("GBP"),
                "JPY": rates.get("JPY"),
                "KRW": rates.get("KRW"),
                "HKD": rates.get("HKD"),
                "AUD": rates.get("AUD"),
                "CAD": rates.get("CAD"),
                "SGD": rates.get("SGD"),
                "MYR": rates.get("MYR"),
                "THB": rates.get("THB"),
                "VND": rates.get("VND"),
                "TWD": rates.get("TWD"),
            },
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        }
        _rates_cache["data"] = curated
        _rates_cache["timestamp"] = now
        return curated
    except Exception as e:
        if _rates_cache["data"]:
            _rates_cache["data"]["error_hint"] = f"更新失败: {e}"
            return _rates_cache["data"]
        return {"base": "USD", "rates": {}, "updated_at": "", "error": str(e)}


RATES_HISTORY_API = "https://api.frankfurter.app"

@app.get("/api/rates/history")
async def rates_history(target: str = "CNY", months: int = 12):
    """获取汇率历史数据（近 N 个月），含基本统计和线性预测"""
    loop = asyncio.get_event_loop()
    today = date.today()
    start = today - timedelta(days=months * 30)
    url = f"{RATES_HISTORY_API}/{start.isoformat()}..{today.isoformat()}?from=USD&to={target}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=15)
        )
        raw = json.loads(resp.read().decode("utf-8"))
        raw_rates = raw.get("rates", {})

        history = []
        for date_str in sorted(raw_rates.keys()):
            val = raw_rates[date_str].get(target)
            if val:
                history.append({"date": date_str, "value": round(val, 4)})

        if len(history) < 2:
            return {"target": target, "base": "USD", "history": history,
                    "stats": {}, "forecast": [], "error": "数据不足"}

        values = [h["value"] for h in history]
        stats = {
            "high": round(max(values), 4),
            "low": round(min(values), 4),
            "average": round(sum(values) / len(values), 4),
            "start": round(values[0], 4),
            "end": round(values[-1], 4),
            "change": round((values[-1] - values[0]) / values[0] * 100, 2),
        }

        # 线性回归预测 7 天
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den else 0
        intercept = y_mean - slope * x_mean
        forecast = []
        for i in range(1, 8):
            pred = slope * (n + i) + intercept
            forecast.append({"day": i, "value": round(pred, 4)})

        return {"target": target, "base": "USD", "history": history,
                "stats": stats, "forecast": forecast}
    except Exception as e:
        return {"target": target, "base": "USD", "history": [],
                "stats": {}, "forecast": [], "error": str(e)}

# ================================================================
# Agent 工作台 API
# ================================================================

@app.post("/api/chat")
async def chat_api(request: Request):
    """AI 聊天"""
    data = await request.json()
    message = data.get("message", "")
    history = data.get("history", [])
    reply = chat_agent.chat(message, history)
    return {"reply": reply}


@app.post("/api/cs/sales")
async def cs_sales():
    """获取客服销量数据（模拟）"""
    return {"data": cs_agent.fetch_sales_data()}


@app.post("/api/cs/queue")
async def cs_queue():
    """获取客服顾客队列（模拟）"""
    return {"data": cs_agent.fetch_customer_queues()}


@app.post("/api/cs/reply")
async def cs_reply(request: Request):
    """AI 生成客服回复"""
    data = await request.json()
    reply = cs_agent.generate_reply(
        data.get("message", ""),
        data.get("product", "")
    )
    return {"reply": reply}


@app.post("/api/social/generate")
async def social_generate(request: Request):
    """生成社交媒体帖子"""
    data = await request.json()
    post = social_agent.generate_post(data.get("product_name", ""))
    return post


@app.post("/api/social/publish")
async def social_publish(request: Request):
    """发布到社交平台（模拟）"""
    data = await request.json()
    result = social_agent.publish(data.get("platform", ""), data.get("content", ""))
    return result

@app.post("/analyze")
async def analyze(request: Request):
    """（向后兼容）运行完整分析工作流，一次性返回格式化的结果"""
    data = await request.json()
    product_name = data.get("product_name", "")
    product_description = data.get("product_description", "")
    uploaded_files = data.get("uploaded_files", [])

    state = create_initial_state(
        product_name=product_name or "未知产品",
        product_description=product_description or "",
        uploaded_files=uploaded_files,
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
        format_comprehensive(state),
    ]

    return {"tabs": tabs, "errors": errors}


@app.post("/analyze-stream")
async def analyze_stream(request: Request):
    """SSE 流式分析 —— 每完成一个节点就推送结果到前端"""
    data = await request.json()
    product_name = data.get("product_name", "")
    product_description = data.get("product_description", "")
    uploaded_files = data.get("uploaded_files", [])

    state = create_initial_state(
        product_name=product_name or "未知产品",
        product_description=product_description or "",
        uploaded_files=uploaded_files,
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
            ("comprehensive", comprehensive_node, format_comprehensive),
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
            elif i == 6:
                html = format_func(state) if format_func else ""
            else:
                html = format_func(state) if format_func else ""

            event = {"step": i, "html": html, "errors": state.get("errors", [])}
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # 最终完成事件
        final = {"step": 7, "status": "complete", "errors": state.get("errors", [])}
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
