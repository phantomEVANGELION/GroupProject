"""LangGraph 图定义 —— 将 5 个节点串联为完整的分析工作流"""

from langgraph.graph import StateGraph, START, END

from workflow.state import WorkflowState
from workflow.nodes import (
    product_node,
    market_node,
    competitor_node,
    strategy_node,
    content_node,
    comprehensive_node,
)


def build_workflow() -> StateGraph:
    """构建 LangGraph 工作流图。

    节点顺序：
        product → market → competitor → strategy → content
    """
    builder = StateGraph(WorkflowState)

    # ---- 注册节点 ----
    builder.add_node("product_analysis", product_node)
    builder.add_node("market_analysis", market_node)
    builder.add_node("competitor_analysis", competitor_node)
    builder.add_node("strategy", strategy_node)
    builder.add_node("content", content_node)
    builder.add_node("comprehensive", comprehensive_node)

    # ---- 连接边 ----
    builder.add_edge(START, "product_analysis")
    builder.add_edge("product_analysis", "market_analysis")
    builder.add_edge("market_analysis", "competitor_analysis")
    builder.add_edge("competitor_analysis", "strategy")
    builder.add_edge("strategy", "content")
    builder.add_edge("content", "comprehensive")
    builder.add_edge("comprehensive", END)

    return builder


def compile_workflow():
    """编译并返回可执行的工作流图"""
    builder = build_workflow()
    graph = builder.compile()
    return graph


def run_workflow(state: WorkflowState) -> WorkflowState:
    """执行完整工作流的快捷函数。

    参数:
        state: 初始状态（至少包含 product_name）

    返回:
        执行完毕后的最终状态（所有分析结果写入其中）
    """
    graph = compile_workflow()
    result = graph.invoke(state)
    return result
