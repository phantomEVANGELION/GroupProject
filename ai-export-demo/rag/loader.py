"""文档加载器模块 —— 支持 PDF / TXT / DOCX / Markdown / JSON 五种格式"""

import os
import traceback
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ========== 文本切分配置 ==========
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def load_document(file_path: str) -> list[Document]:
    """加载单个文档，返回 LangChain Document 列表。

    支持格式: .pdf, .txt, .docx, .md, .json
    metadata 中自动填充 source 字段（文件名）
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    file_name = os.path.basename(file_path)

    try:
        if ext == ".pdf":
            return _load_pdf(file_path, file_name)
        elif ext == ".txt":
            return _load_txt(file_path, file_name)
        elif ext == ".docx":
            return _load_docx(file_path, file_name)
        elif ext in (".md", ".json", ".yaml", ".yml"):
            # Markdown、JSON 等文本格式复用 TXT 加载逻辑
            return _load_txt(file_path, file_name)
        else:
            raise ValueError(f"不支持的文件格式: {ext}（支持 PDF/TXT/DOCX/MD/JSON）")
    except Exception as e:
        raise RuntimeError(f"加载文件失败 [{file_name}]: {e}")


def _load_pdf(file_path: str, source_name: str) -> list[Document]:
    """使用 pypdf 逐页提取 PDF 文本"""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("需要安装 pypdf: pip install pypdf")

    reader = PdfReader(file_path)
    docs: list[Document] = []
    for page_no, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            docs.append(Document(
                page_content=text,
                metadata={"source": source_name, "page": page_no},
            ))
    if not docs:
        docs.append(Document(page_content="", metadata={"source": source_name}))
    return docs


def _load_txt(file_path: str, source_name: str) -> list[Document]:
    """加载 UTF-8 文本文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return [Document(page_content=text, metadata={"source": source_name})]


def _load_docx(file_path: str, source_name: str) -> list[Document]:
    """使用 python-docx 提取段落与表格文本"""
    try:
        import docx
    except ImportError:
        raise ImportError("需要安装 python-docx: pip install python-docx")

    document = docx.Document(file_path)
    parts = [p.text for p in document.paragraphs if p.text.strip()]
    # 表格内容按行拼接，避免产品参数表被丢弃
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))

    text = "\n".join(parts)
    return [Document(page_content=text, metadata={"source": source_name})]


def split_documents(documents: list[Document]) -> list[Document]:
    """将文档切分为固定大小的 chunk"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    return splitter.split_documents(documents)


def load_and_split(file_path: str) -> list[Document]:
    """加载并切分文档的快捷函数"""
    docs = load_document(file_path)
    return split_documents(docs)
