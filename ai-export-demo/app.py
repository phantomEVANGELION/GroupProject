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

# ========== 文件上传配置 ==========
UPLOAD_DIR = os.path.join(config.BASE_DIR, "data", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".json", ".yaml", ".yml"}

# ========== 汇率缓存 ==========
_rates_cache = {"data": None, "timestamp": 0}
RATES_CACHE_TTL = 1800  # 30 分钟

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
          padding: 0 20px; }
.navbar .logo { font-weight: 700; font-size: 16px; color: #0f172a;
                text-decoration: none; display: flex; align-items: center; gap: 6px; }
.navbar .logo:hover { color: #3b82f6; }
.nav-links { display: flex; gap: 4px; margin-left: auto; }
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
</style>
</head>
<body>

<!-- ==================== Navbar ==================== -->
<nav class="navbar">
  <a href="#home" class="logo">🌍 您的跨境电商助手</a>
  <div class="nav-links">
    <a href="#home">首页</a>
    <a href="#analyze">全面产品分析</a>
    <a href="#platforms">海外平台介绍</a>
    <a href="#rates">实时汇率</a>
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
<span id="s5">⬜ 文案编写</span>
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
<div class="header"><h1>💱 实时汇率</h1><p>主要货币兑美元汇率（每 30 分钟自动更新）</p></div>
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
            html += '<div class="rate-item">';
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

// ==================== Analysis Page (existing) ====================
const TAB_NAMES = ["📋 产品分析","🌍 市场分析","⚔️ 竞品分析","🎯 营销策略","✍️ 文案编写"];
const NOTIFY_MSG = {
    1: "✅ 产品分析生成完毕！",
    2: "🌍 市场分析生成完毕！",
    3: "⚔️ 竞品分析生成完毕！",
    4: "🎯 营销策略生成完毕！",
    5: "✍️ 文案编写完毕！"
};
const STEP_NAMES = ["产品分析", "市场分析", "竞品分析", "营销策略", "文案编写"];

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
    const pct = Math.min(Math.round((step - 1) / 5 * 100), 100);
    document.getElementById("progressFill").style.width = pct + "%";
    const labels = ["等待开始...", "📋 正在分析产品资料...", "🌍 正在分析市场数据...",
                    "⚔️ 正在分析竞品信息...", "🎯 正在制定营销策略...",
                    "✍️ 正在编写营销文案...", "✅ 分析完成！"];
    document.getElementById("progressText").textContent = labels[Math.min(step, 6)] || "";
    for (let i = 1; i <= 5; i++) {
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
