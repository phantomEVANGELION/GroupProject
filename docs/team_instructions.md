# 组员开发说明

## 项目背景

我们当前项目是一个 AI 跨境电商运营助手（FastAPI + LangGraph + ChromaDB + DeepSeek），可以在浏览器里填产品信息生成分析报告。老师现在要求把它从一个"咨询工具"改成一个"操作工作台"。

简单说就是：原来只能看分析结果，现在要能操作——AI 聊天、AI 客服回消息、AI 发帖子。但"能操作"不代表真要连真实平台，功能做出来、代码写完整、演示走得通就行。

## 核心：别怕，不要被老师的需求吓到

老师提的需求如果全部真实实现，是一个企业级项目。但我们的策略是：

| 老师说的 | 我们做的 |
|----------|---------|
| AI 客服对接顾客 | 做客服工作台界面，AI 生成回复草稿，人工确认发送。有模拟顾客数据、有销量面板。代码中写好了 Amazon API 的接入位置（TODO 注释），演示走模拟。 |
| 自动在 X/Facebook/Ins 发帖 | 做帖子生成 + 预览编辑 + 三个平台按钮。代码中写了各平台 API 调用函数，用一个开关控制是模拟还是真实发布，默认关。 |
| AI 聊天 | 正经做一个聊天界面 + 后端调用 deepseek-chat，这个是真的。 |
| Agent 工作台 | 加一个新页面，左侧 4 个 Agent 按钮切换右侧内容。原有功能全部保留。 |

**老师验收时能看到什么：**
- 点进工作台 → 左边四个按钮
- 聊天 → 真的能对话
- 客服 → 有顾客列表、销量数据、AI 生成回复
- 营销 → 生成帖子、预览、点发布弹窗"模拟发布成功"

**验收标准就一条：演示路径走得通，界面看着像个完整的东西。**

## 文件结构

```
ai-export-demo/
├── app.py                   # ★ 主要修改：前端加工作台 + 后端加 API
├── config.py                # 小改：加一行 ENABLE_SOCIAL_PUBLISH
├── agents/                  # ★ 新增目录：三个 Agent 逻辑
│   ├── __init__.py          #   空文件
│   ├── chat_agent.py        #   聊天 Agent（调用 deepseek-chat）
│   ├── cs_agent.py          #   客服 Agent（模拟数据）
│   └── social_agent.py      #   发帖 Agent（生成+模拟发布）
├── workflow/                # 不动
├── rag/                     # 不动（store_kb 直接用现有 ChromaDB 代码）
├── app_format.py            # 不动
├── knowledge_base/          # 不动
└── sample_data/             # 可选：放一份示例店铺文档
```

## 具体分工

###  改 app.py 的 HTML_PAGE

你要做的事情：

1. **在导航栏加一个链接**：`<a href="#workspace">Agent工作台</a>`
2. **新增一个页面** `<div id="page-workspace" class="page">`
3. **工作台布局**：
   - 左侧 200px 侧边栏，深色背景，4 个按钮垂直排列：分析助手 / AI 聊天 / 客服助手 / 营销助手
   - 右侧是工作区，根据点击切换显示不同的内容
4. **分析助手**：可以直接放一段说明文字 + 链接到现有分析页 `#analyze`，或者把现有分析表单搬过来
5. **AI 聊天界面**：
   - 消息列表（气泡样式，用户蓝色右对齐，AI 白色左对齐）
   - 底部输入框 + 发送按钮
   - 发送时调 `/api/chat`，把返回的 reply 显示在消息列表
6. **客服界面**：
   - 顶部一行状态卡片：今日收入、今日订单、待处理消息（调 `/api/cs/sales`）
   - 左侧顾客列表：显示每个顾客的名字、状态（在线/离线）、最后消息（调 `/api/cs/queue`）
   - 右侧对话窗口：点击顾客后显示，底部有输入框 + "AI 生成回复"按钮
   - 点击"AI 生成回复"→ 调 `/api/cs/reply` → 结果填入输入框 → 用户点发送
7. **营销界面**：
   - 产品选择下拉框 + "生成帖子"按钮
   - 帖子预览区，三个小 tab：X / Facebook / Instagram
   - 帖子内容可编辑（textarea）
   - 三个发布按钮，各调 `/api/social/publish` → 弹窗显示结果
8. **JavaScript 函数**：
   - `switchAgent(agent)` — 切换 Agent 面板
   - `sendChatMessage()` — 发送聊天消息
   - `loadCustomerService()` — 加载客服数据
   - `generateSocialPost()` — 生成帖子
   - `publishTo(platform)` — 发布到指定平台

**样式提示**：保持现有风格，色值参考：
- 背景 `#f8fafc` / 白色卡片 `#ffffff`
- 主色 `#3b82f6` / 边框 `#e2e8f0`
- 文字 `#1e293b` / 次要文字 `#64748b`
- 侧边栏深色：`#0f172a` 或 `#1e293b`，文字白色

### Agent 组（1-2人）— 新建 agents/ 目录

你要创建 4 个文件：

**`agents/__init__.py`** — 空文件

**`agents/chat_agent.py`**（约 50 行）
- 一个函数 `chat(message, history)`：
  - 从 store_kb 搜索店铺信息
  - 组装 system prompt（含店铺信息）
  - 调用 ChatOpenAI（deepseek-chat）
  - 返回 reply 字符串
- 不需要维护会话状态，前端传 history 过来就行

**`agents/cs_agent.py`**（约 120 行）
- `fetch_sales_data()` — 返回模拟销量 dict（today_revenue, today_orders, monthly_revenue, pending_messages）
- `fetch_customer_queues()` — 返回预设的顾客列表（3-4 个顾客，含 id/name/status/last_message/time/product）
- `generate_reply(message, product_context)` — 从 store_kb 检索产品信息 → 组装客服 prompt → LLM 回复
- 每个函数加 `# TODO: 接入真实 API` 注释，函数名本身就说明了意图

**`agents/social_agent.py`**（约 150 行）
- `generate_post(product_name)` — 调 LLM 生成三个平台的帖子 + hashtags，返回 dict
- `publish(platform, content)` — 
  - 读取 `config.ENABLE_SOCIAL_PUBLISH`
  - False：写 publish_log.jsonl 日志，返回模拟成功
  - True：执行真实发布（注释掉的骨架代码写在里面）
- 需要 `_log_publish()` 函数记录发布日志到 `data/publish_log.jsonl`

### 改 app.py 后端 + 联调

你要做的事情：

1. **在 app.py 顶部加入新的 import**：
   ```python
   from agents import chat_agent, cs_agent, social_agent
   ```

2. **新增 6 个 API 端点**：

   | 端点 | 方法 | 功能 |
   |------|------|------|
   | `/api/chat` | POST | 接收 message + history，返回 reply |
   | `/api/cs/sales` | POST | 返回模拟销量数据 |
   | `/api/cs/queue` | POST | 返回模拟顾客队列 |
   | `/api/cs/reply` | POST | 接收 message + product，返回 AI 生成回复 |
   | `/api/social/generate` | POST | 接收 product_name，返回三个平台的帖子内容 |
   | `/api/social/publish` | POST | 接收 platform + content，模拟/真实发布 |

3. **改 `config.py`**：加一行 `ENABLE_SOCIAL_PUBLISH = False`

4. **联调测试**：确保前端每个按钮调对应 API 都能通

## 关键约定

1. **不动 workflow/ 和 app_format.py** — 原有的分析功能还是好的，不需要动
2. **store_kb collection**：Chat Agent 和 CS Agent 在初始化时从 store_kb 检索店铺信息。目前 store_kb 可能为空，不影响运行（LLM 会用自身知识兜底）。可以在 `sample_data/` 下放一份示例店铺文档 `my_store.md`，程序启动时自动加载到 store_kb
3. **API 错误处理**：每个 API 要 try/except，出错时返回 `{"error": "..."}`，不要让前端白屏

## 如果做不完怎么办

**老师验收的核心**是演示路径走得通，不是代码完美。优先级排序：

```
P0
  - 工作台页面能打开，4 个按钮能切换
  - AI 聊天能收发消息（走通了 deepseek-chat）
  - 客服界面能看到顾客列表和销量数字（模拟数据即可）

P1
  - AI 客服能生成回复
  - 营销助手能生成帖子

P2
  - 帖子编辑后发布 + 弹窗
  - 示例店铺文档 + store_kb 加载
```



## 如何开始

```bash
# 1. 先读文档
cat docs/HANDOVER.md
cat docs/profile.md
cat docs/new_requirement.md      # 完整需求方案

# 2. 启动项目确认当前状态
cd D:\GroupProject\ai-export-demo
python app.py
# 打开 http://127.0.0.1:7860

# 3. 按分工修改代码
# 4. 测试
# 5. git commit
```
