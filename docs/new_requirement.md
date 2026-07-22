# 新需求实现方案 —— AI 跨境出海运营工作台

> 阅读顺序：先读 HANDOVER.md 了解项目全貌 → 再读此文档了解改动方向
> 将此文档 + HANDOVER.md + profile.md 一起交给 Claude，即可直接开工

---

## 一、定位转变

```
从: AI 咨询分析师 — 用户填表 → AI 分析 → 用户看报告 (被动)
到: AI 运营工作台 — 用户下指令 → AI 执行操作 → 反馈结果 (主动)
```

## 二、整体方案概览

保留现有全部功能（首页、海外平台、汇率咨询），在导航栏新增"工作台"页面。工作台采用左侧 Agent 面板 + 右侧工作区布局，包含 4 个 Agent。

### 导航栏变化

```
首页 | Agent工作台(新增) | 海外平台介绍(原有) | 汇率咨询(原有)
```

首页的"开始使用"按钮链接到 #workspace 页面。

### 知识库新增

新增一个 `store_kb` ChromaDB collection，用于存储用户店铺配置信息。用户上传一份文档（如 `my_store.md`），包含以下内容，所有 Agent 基于此文档工作：

```markdown
# 我的店铺配置

## 店铺信息
- 店铺名称: TechWear 智能穿戴
- 主营品类: 智能手表、运动手环
- 店铺等级: 亚马逊专业卖家

## 产品列表
1. X100 智能运动手表 - $79 - IP68防水/7天续航/健康监测
2. X100 Mini 运动手环 - $39 - 轻量化/5天续航/心率监测
3. X100 Pro 旗舰手表 - $129 - AMOLED屏/GPS/100+运动模式

## 公司信息
- 公司名称: 深圳智造科技有限公司
- 团队规模: 15人
- 月产能: 5000台

## 资金情况
- 月营销预算: $3000
- 可承受单次推广: $500

## 账号信息 (虚拟)
- Amazon店铺: TechWear_Official
- X (Twitter): @TechWear_Global
- Facebook: /TechWearOfficial
- Instagram: @techwear_wearables
```

---

## 三、需求 1：Agent 工作台

### 效果描述

点击导航栏"Agent工作台"进入，左侧显示 4 个 Agent 按钮，点击切换右侧工作区内容。

### 前端实现

在 `app.py` 的 HTML_PAGE 中：

1. **新增页面** `<div id="page-workspace" class="page">`
2. **左侧面板**：4 个 Agent 按钮
   ```html
   <div class="agent-sidebar">
     <button onclick="switchAgent('analysis')">🤖 分析助手</button>
     <button onclick="switchAgent('chat')">💬 AI 聊天</button>
     <button onclick="switchAgent('customer-service')">🛒 客服助手</button>
     <button onclick="switchAgent('marketing')">📣 营销助手</button>
   </div>
   ```
3. **右侧工作区**：4 个对应的内容区，用 `display: none/block` 切换
4. 原有分析页面（`#analyze`）保留，可以在工作台的分析助手中复用或链接过去

**样式要求**：
- 侧边栏宽度 200px，深色背景，固定定位
- 按钮 hover 有高亮效果，点击保持 active 状态
- 右侧工作区填充剩余宽度
- 整体风格与现有 UI 保持一致（白/灰/蓝配色）

### 切换逻辑

```javascript
function switchAgent(agent) {
    // 隐藏所有 agent-content
    // 显示选中的 agent-content
    // 更新侧边栏按钮 active 状态
    // 首次进入对应 Agent 时执行初始化（如加载客服数据）
}
```

---

## 四、需求 2：AI 聊天功能

### 效果描述

一个类似 ChatGPT 的对话界面，用户可以直接与 AI 交流产品销售相关问题。AI 能基于店铺知识库（store_kb）和 DeepSeek 的自身知识回答。

### 后端实现

新增 `agents/chat_agent.py`：

```python
"""
AI 聊天 Agent

实现: 无状态对话，每次请求独立。
使用 deepseek-chat，system prompt 注入店铺知识库上下文。

API: POST /api/chat
请求: {"message": "用户消息", "history": [{"role": "user"/"assistant", "content": ""}]}
响应: {"reply": "AI 回复"}
"""

import json
import config
from langchain_openai import ChatOpenAI
from rag.chroma_client import similarity_search


COLLECTION_STORE = "store_kb"


def _get_llm():
    return ChatOpenAI(
        model=config.LLM_MODEL_NAME,
        temperature=0.5,
        openai_api_key=config.DEEPSEEK_API_KEY,
        openai_api_base=config.DEEPSEEK_API_BASE,
        timeout=config.LLM_TIMEOUT,
    )


def _build_system_prompt() -> str:
    """从 store_kb 检索店铺信息，构建 system prompt"""
    try:
        docs = similarity_search(COLLECTION_STORE, "店铺产品 公司信息", k=5)
        context = "\n".join([doc.page_content for doc in docs])
    except Exception:
        context = "（暂无店铺配置信息）"

    return f"""你是一个跨境电商运营助手，帮助卖家分析产品、制定策略、优化销售。
    
当前店铺信息：
{context}

你可以回答关于产品、市场、定价、营销、物流等方面的问题。
如果用户问的问题你不确定，请如实说"建议进一步分析"，不要编造数据。
回答要简洁、具体、可操作。"""


def chat(message: str, history: list[dict] = None) -> str:
    """处理聊天消息，返回 AI 回复"""
    llm = _get_llm()
    system_prompt = _build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-10:])  # 保留最近 10 轮
    messages.append({"role": "user", "content": message})

    try:
        result = llm.invoke(messages)
        return result.content
    except Exception as e:
        return f"（AI 回复失败: {e}）"
```

### 在 app.py 中新增 API：

```python
@app.post("/api/chat")
async def chat_api(request: Request):
    data = await request.json()
    message = data.get("message", "")
    history = data.get("history", [])
    reply = chat_agent.chat(message, history)
    return {"reply": reply}
```

### 前端实现

分析页右侧工作区中，AI 聊天面板包含：

```html
<div class="chat-messages" id="chatMessages">
  <!-- 消息气泡 -->
</div>
<div class="chat-input-row">
  <input type="text" id="chatInput" placeholder="输入消息...">
  <button onclick="sendChatMessage()">发送</button>
</div>
```

- 用户消息（蓝色气泡，右对齐）
- AI 回复（白色气泡，左对齐）
- 按 Enter 发送
- 发送时按钮禁用，显示加载动画

---

## 五、需求 3：AI 客服功能

### 效果描述

客服工作台展示"当前顾客咨询"列表，点击顾客可查看对话。对话中 AI 自动回复，同时显示"实时销量"数据。所有数据为模拟，但代码结构预留真实 API 接入点。

### 后端实现

新增 `agents/cs_agent.py`：

```python
"""
AI 客服 Agent

实现:
- fetch_sales_data() — 获取销量数据（模拟）
- fetch_customer_queues() — 获取排队顾客列表（模拟）
- generate_reply() — 基于产品知识库自动生成客服回复
- 所有函数预留真实 API 接入点（TODO 注释）

API: POST /api/cs/queue — 获取顾客队列
     POST /api/cs/reply — AI 生成回复
     POST /api/cs/sales — 获取销量数据
"""

import random
import config
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

    from langchain_openai import ChatOpenAI
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
```

### 在 app.py 中新增 API：

```python
@app.post("/api/cs/sales")
async def cs_sales():
    return {"data": cs_agent.fetch_sales_data()}

@app.post("/api/cs/queue")
async def cs_queue():
    return {"data": cs_agent.fetch_customer_queues()}

@app.post("/api/cs/reply")
async def cs_reply(request: Request):
    data = await request.json()
    reply = cs_agent.generate_reply(
        data.get("message", ""),
        data.get("product", "")
    )
    return {"reply": reply}
```

### 前端实现

客服工作台包含：

1. **顶部状态栏**：显示今日收入、今日订单、待处理消息数
2. **左侧顾客列表**：显示所有"排队"的顾客，带在线状态指示器
3. **右侧对话窗口**：点击顾客后显示对话，底部输入框 + "AI 生成回复"按钮
4. **点击 AI 生成回复** → 调用 `/api/cs/reply` → AI 回复填入输入框 → 人工确认后点击发送

---

## 六、需求 4：AI 发帖功能

### 效果描述

营销助手工作区，展示 AI 生成的推广帖子，用户可编辑修改。下方提供三个平台发布按钮（X / Facebook / Instagram），点击后模拟发布（写入本地日志）。

### 后端实现

新增 `agents/social_agent.py`：

```python
"""
AI 营销发帖 Agent

实现:
- generate_post() — 基于产品信息生成社交媒体帖子
- publish_to_x() — 发布到 X (Twitter)（模拟/真实切换）
- publish_to_facebook() — 发布到 Facebook（模拟/真实切换）
- publish_to_instagram() — 发布到 Instagram（模拟/真实切换）
- 所有发布函数由 config.ENABLE_SOCIAL_PUBLISH 控制

API: POST /api/social/generate — 生成帖子
     POST /api/social/publish — 发布到指定平台
"""

import json
import os
from datetime import datetime
from langchain_openai import ChatOpenAI
import config
from rag.chroma_client import similarity_search

COLLECTION_STORE = "store_kb"

# 发布日志路径
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
        # 尝试解析 JSON（复用 nodes.py 的 _safe_parse_json 逻辑）
        import re, json as json_mod
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', result)
        if match:
            candidate = match.group(1).strip()
        else:
            brace = re.search(r'(\{[\s\S]*\})', result)
            candidate = brace.group(1).strip() if brace else result
        parsed = json_mod.loads(candidate)
        return parsed
    except Exception as e:
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
    TODO: 接入真实 API 时：
       - X: tweepy.Client.create_tweet()
       - Facebook: requests.post(Graph API)
       - Instagram: requests.post(Graph API /media + /publish)
    """
    platform_map = {
        "x": "X (Twitter)",
        "facebook": "Facebook",
        "instagram": "Instagram",
    }
    platform_name = platform_map.get(platform, platform)

    if config.ENABLE_SOCIAL_PUBLISH:
        # 真实发布（需配置 API Key）
        # 此处写各平台 API 调用的骨架代码
        _log_publish(platform, content, "published")
        return {"status": "published", "platform": platform_name, "message": f"已发布到 {platform_name}"}
    else:
        # 模拟发布
        _log_publish(platform, content, "simulated")
        return {"status": "simulated", "platform": platform_name, "message": f"✅ 模拟发布到 {platform_name}（配置开启后执行真实发布）"}
```

### 在 app.py 中新增 API：

```python
@app.post("/api/social/generate")
async def social_generate(request: Request):
    data = await request.json()
    post = social_agent.generate_post(data.get("product_name", ""))
    return post

@app.post("/api/social/publish")
async def social_publish(request: Request):
    data = await request.json()
    result = social_agent.publish(data.get("platform", ""), data.get("content", ""))
    return result
```

### 在 config.py 中新增：

```python
# ========== 社交平台发布配置 ==========
ENABLE_SOCIAL_PUBLISH = False  # 设为 True 时执行真实发布（需配置各平台 API Key）
```

### 前端实现

营销助手工作区包含：

1. **选择产品下拉框**（从 store_kb 中读取产品列表）
2. **生成帖子按钮**
3. **帖子预览**：三个 tab 分别展示 X/Facebook/Instagram 版本
4. **编辑框**：用户可修改生成的内容
5. **三个发布按钮**：
   - `𝕏 发布到 X`
   - `📘 发布到 Facebook`
   - `📸 发布到 Instagram`
6. 点击任一按钮 → 调用 `/api/social/publish` → 显示弹窗"✅ 已模拟发布到 X"

---

## 七、新增/修改文件汇总

| 文件 | 操作 | 说明 |
|------|------|------|
| `app.py` | 修改 | 前端加工作台 UI + 后端加 6 个新 API |
| `config.py` | 修改 | 加 `ENABLE_SOCIAL_PUBLISH` 配置项 |
| `agents/chat_agent.py` | **新增** | 聊天 Agent |
| `agents/cs_agent.py` | **新增** | 客服 Agent（含模拟数据） |
| `agents/social_agent.py` | **新增** | 营销发帖 Agent（含三个平台发布函数） |
| `agents/__init__.py` | **新增** | 空文件，使 agents 成为包 |
| `rag/chroma_client.py` | 不需改 | `COLLECTION_STORE = "store_kb"` 直接在 agent 中定义即可 |
| 示例店铺文档 | 可选新增 | `sample_data/my_store.md` |

### 原有文件不需要改动的部分

- `workflow/` 全部 — 工作流引擎不动
- `app_format.py` — 格式化函数不动
- `rag/loader.py` — 文档加载器不动
- `rag/prompts.py` — Prompt 模板不动
- `init_knowledge_base.py` — 初始化脚本不动
- 知识库 `knowledge_base/` 全部不动

---

## 八、分工建议

### 前端组（1人）
- 修改 `app.py` 中的 HTML_PAGE
- 新增工作台布局（侧边栏 + 4 个 Agent 面板）
- 新增聊天 UI、客服 UI、营销 UI
- 保持与现有风格一致

### Agent 组（1-2人）
- 实现 `agents/chat_agent.py`
- 实现 `agents/cs_agent.py`
- 实现 `agents/social_agent.py`
- 实现 `agents/__init__.py`

### 集成组（1人）
- 在 `app.py` 中新增 6 个 API 端点
- 修改 `config.py` 加配置项
- 测试所有 API 与前端联通
- 整体联调

---

## 九、注意事项

1. **不要动原有 workflow/ 下的任何文件** — 分析功能仍然保留
2. **客服回复必须设计人工确认步骤** — 不要直接 AI 自动回复顾客，回复先填入输入框让人确认
3. **所有"模拟"数据函数要写 TODO 注释** — 老师看代码时知道这里预留了真实 API 位置
4. **前端风格保持统一** — 参照现有页面的 padding/color/font 体系
5. **测试方式**：python app.py → http://127.0.0.1:7860 → 导航栏进工作台

---

## 十、效果演示路径（给老师看）

```
1. 打开首页 → 展示原有功能完整保留
2. 点击"开始使用"或导航栏"Agent工作台"

3. 分析助手 → 展示原有分析功能（或简单链接到分析页）

4. 切换到 AI 聊天
   → 输入"我这款产品适合在哪些国家卖？"
   → AI 基于店铺文档和自身知识回答

5. 切换到 客服助手
   → 展示今日收入、订单数
   → 顾客列表中有几人在线
   → 点击顾客 → AI 生成回复 → 人工确认

6. 切换到 营销助手
   → 选择产品 → 点击生成帖子
   → 展示 X/Facebook/Instagram 三版内容
   → 点击"发布到 X" → 弹窗 "✅ 模拟发布成功"
```

---

## 十一、回退方案

如果改动过程中出现问题，可以随时回退：

```bash
cd D:\GroupProject
git checkout -- ai-export-demo/app.py
git checkout -- ai-export-demo/config.py
# 删除新增文件
Remove-Item -Recurse -Force ai-export-demo/agents/
```

当前存档点 commit: `ff220ba`
