"""Workflow State 定义 —— LangGraph 各节点间传递的数据结构"""

from typing import TypedDict, Optional


class WorkflowState(TypedDict):
    """LangGraph Workflow 的状态类型。

    每个节点从 state 中读取输入，将输出写回 state。
    """

    # ========== 用户输入 ==========
    product_name: str
    product_description: str
    uploaded_files: list[str]

    # ========== 节点 1：产品分析 ==========
    product_analysis: Optional[dict]
    product_sources: list[str]

    # ========== 节点 2：市场分析 ==========
    market_analysis: Optional[dict]
    market_sources: list[str]

    # ========== 节点 3：竞品分析 ==========
    competitor_analysis: Optional[dict]
    competitor_sources: list[str]

    # ========== 节点 4：营销策略 ==========
    strategy: Optional[dict]

    # ========== 节点 5：内容生成 ==========
    contents: Optional[dict]

    # ========== 执行元数据 ==========
    errors: list[str]


def create_initial_state(
    product_name: str = "",
    product_description: str = "",
    uploaded_files: list[str] | None = None,
) -> WorkflowState:
    """创建初始 WorkflowState"""
    return {
        "product_name": product_name,
        "product_description": product_description,
        "uploaded_files": uploaded_files or [],
        "product_analysis": None,
        "product_sources": [],
        "market_analysis": None,
        "market_sources": [],
        "competitor_analysis": None,
        "competitor_sources": [],
        "strategy": None,
        "contents": None,
        "errors": [],
    }
