"""ChromaDB 客户端模块 —— 管理三个知识库 Collection 的增删查"""

import os
import shutil
from typing import Optional

import chromadb
from langchain_chroma import Chroma
try:
    # langchain-huggingface >= 0.1 新路径
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    # 降级到旧路径
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

import config


# ========== 全局单例 ==========
_chroma_client: Optional[chromadb.PersistentClient] = None
_embedding_function = None


def get_chroma_client() -> chromadb.PersistentClient:
    """获取 ChromaDB 持久化客户端（单例）"""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(config.CHROMA_DB_PATH, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    return _chroma_client


def get_embedding_function():
    """获取 Embedding 函数。

    默认使用 BAAI/bge-small-zh-v1.5（本地 HuggingFace），
    加载失败时自动降级到 OpenAI Compatible Embedding。
    """
    global _embedding_function
    if _embedding_function is not None:
        return _embedding_function

    # 尝试加载本地 BGE 模型
    _embedding_function = _try_load_bge()
    if _embedding_function is not None:
        return _embedding_function

    # 降级到 OpenAI Compatible
    _embedding_function = _try_load_openai()
    if _embedding_function is not None:
        print("⚠️ 已降级到 OpenAI Compatible Embedding")
        return _embedding_function

    raise RuntimeError("所有 Embedding 方案均加载失败，请检查网络或模型配置")


def _try_load_bge() -> Optional[HuggingFaceEmbeddings]:
    """尝试加载 BGE 本地 Embedding 模型"""
    try:
        print(f"正在加载 Embedding 模型: {config.EMBEDDING_MODEL} ...")
        embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL,
            model_kwargs={"device": config.EMBEDDING_DEVICE},
            encode_kwargs={"normalize_embeddings": True},
        )
        # 验证可用性
        _ = embeddings.embed_query("test")
        print("✅ Embedding 模型加载成功（本地 BGE）")
        return embeddings
    except Exception as e:
        print(f"❌ BGE 模型加载失败: {e}")
        return None


def _try_load_openai() -> Optional[object]:
    """尝试加载 OpenAI Compatible Embedding（备用方案）"""
    try:
        from langchain_openai import OpenAIEmbeddings

        api_key = config.DEEPSEEK_API_KEY
        if not api_key or api_key.startswith("sk-your"):
            print("⚠️ 未配置有效的 API Key，跳过 OpenAI Embedding 降级")
            return None

        embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            openai_api_key=api_key,
            openai_api_base=config.DEEPSEEK_API_BASE,
        )
        _ = embeddings.embed_query("test")
        print("✅ OpenAI Compatible Embedding 连接成功")
        return embeddings
    except Exception as e:
        print(f"❌ OpenAI Embedding 降级也失败: {e}")
        return None


def get_vectorstore(collection_name: str) -> Chroma:
    """获取指定 collection 的 LangChain Chroma VectorStore 对象"""
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embedding_fn,
    )


def create_or_get_collection(collection_name: str):
    """创建或获取 ChromaDB Collection（当不需要 VectorStore 接口时使用）"""
    client = get_chroma_client()
    return client.get_or_create_collection(collection_name)


def add_documents(collection_name: str, documents: list[Document]):
    """向指定 collection 添加文档。

    自动使用配置的 Embedding 模型进行向量化。
    要求 documents 的 metadata 中包含 source 字段。
    """
    vs = get_vectorstore(collection_name)
    vs.add_documents(documents)


def similarity_search(
    collection_name: str,
    query: str,
    k: int = 4,
) -> list[Document]:
    """在指定 collection 中进行相似度检索。

    返回 Document 列表，每个 Document 包含:
    - page_content: 文本内容
    - metadata.source: 来源文件名
    """
    try:
        vs = get_vectorstore(collection_name)
        docs = vs.similarity_search(query, k=k)
        return docs
    except Exception as e:
        print(f"⚠️ 检索失败 [{collection_name}]: {e}")
        return []


def get_collection_count(collection_name: str) -> int:
    """获取指定 collection 的文档数量"""
    try:
        client = get_chroma_client()
        col = client.get_collection(collection_name)
        return col.count()
    except Exception:
        return 0


def reset_collection(collection_name: str):
    """清空指定 collection（用于测试或重新初始化）"""
    try:
        client = get_chroma_client()
        client.delete_collection(collection_name)
    except Exception:
        pass
