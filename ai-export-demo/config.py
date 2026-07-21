"""应用配置模块"""

import os
from dotenv import load_dotenv

load_dotenv()

# ========== DeepSeek API 配置 ==========
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
LLM_TEMPERATURE_ANALYSIS = 0.3   # 分析类节点（产品/市场/竞品/策略）
LLM_TEMPERATURE_CONTENT = 0.5    # 内容生成节点

# ========== ChromaDB 配置 ==========
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chroma_db")
COLLECTION_PRODUCT = "product_kb"
COLLECTION_MARKET = "market_kb"
COLLECTION_COMPETITOR = "competitor_kb"

# ========== Embedding 配置 ==========
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
EMBEDDING_DEVICE = "cpu"

# ========== RAG 检索参数 ==========
RAG_TOP_K = 3
RAG_SCORE_THRESHOLD = 0.6

# ========== 路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
MARKET_KB_DIR = os.path.join(KNOWLEDGE_BASE_DIR, "market")
COMPETITOR_KB_DIR = os.path.join(KNOWLEDGE_BASE_DIR, "competitors")
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")

# ========== LLM 超时 ==========
LLM_TIMEOUT = 60  # 单次 LLM 调用超时（秒）
