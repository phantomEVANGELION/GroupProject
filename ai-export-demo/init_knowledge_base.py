"""初始化知识库 —— 将预置的行业数据加载到 ChromaDB"""

import os
import glob
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import config
from rag.loader import load_and_split
from rag.chroma_client import (
    add_documents, reset_collection, get_collection_count
)


def init_market_kb():
    """加载 knowledge_base/market/ 下的所有文件到 market_kb"""
    print("\n📚 初始化市场知识库 (market_kb) ...")
    reset_collection(config.COLLECTION_MARKET)

    pattern = os.path.join(config.MARKET_KB_DIR, "*")
    files = glob.glob(pattern)

    if not files:
        print("  ⚠️ 未找到市场数据文件")
        return

    total_chunks = 0
    for file_path in sorted(files):
        try:
            chunks = load_and_split(file_path)
            if chunks:
                add_documents(config.COLLECTION_MARKET, chunks)
                total_chunks += len(chunks)
                print(f"  ✅ {os.path.basename(file_path)} → {len(chunks)} chunks")
            else:
                print(f"  ⚠️ {os.path.basename(file_path)} → 空内容")
        except Exception as e:
            print(f"  ❌ {os.path.basename(file_path)} → 失败: {e}")

    count = get_collection_count(config.COLLECTION_MARKET)
    print(f"  市场知识库总计: {count} chunks ✅")


def init_competitor_kb():
    """加载 knowledge_base/competitors/ 下的所有文件到 competitor_kb"""
    print("\n📚 初始化竞品知识库 (competitor_kb) ...")
    reset_collection(config.COLLECTION_COMPETITOR)

    pattern = os.path.join(config.COMPETITOR_KB_DIR, "*")
    files = glob.glob(pattern)

    if not files:
        print("  ⚠️ 未找到竞品数据文件")
        return

    total_chunks = 0
    for file_path in sorted(files):
        try:
            chunks = load_and_split(file_path)
            if chunks:
                add_documents(config.COLLECTION_COMPETITOR, chunks)
                total_chunks += len(chunks)
                print(f"  ✅ {os.path.basename(file_path)} → {len(chunks)} chunks")
            else:
                print(f"  ⚠️ {os.path.basename(file_path)} → 空内容")
        except Exception as e:
            print(f"  ❌ {os.path.basename(file_path)} → 失败: {e}")

    count = get_collection_count(config.COLLECTION_COMPETITOR)
    print(f"  竞品知识库总计: {count} chunks ✅")


def main():
    print("=" * 50)
    print("知识库初始化")
    print("=" * 50)
    print(f"ChromaDB 路径: {config.CHROMA_DB_PATH}")

    init_market_kb()
    init_competitor_kb()

    print("\n" + "=" * 50)
    print("知识库初始化完成 ✅")
    print("=" * 50)


if __name__ == "__main__":
    main()
