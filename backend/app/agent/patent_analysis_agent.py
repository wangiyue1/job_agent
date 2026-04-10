"""
当前节点分工：
   - route_task：任务分流
   - search_patents：专利检索
   - risk_analysis：技术风险预筛分析
   - intelligence_analysis：竞品情报分析
"""
import logging
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Literal, Optional, Dict, Any
from ..models.schemas import(
    RiskScreeningRequest,
    IntelligenceAnalysisRequest,
    RiskScreeningResult,
    IntelligenceAnalysisResult,
)
from ..models.agent_structs import(
    PatentSearchResult,
    RiskAnalysisInput,
    IntelligenceAnalysisInput,
    PatentRecord
)
from ..services.patent_service import (
    pg_search_patents,
    chroma_search_patents,
)
from ..services.risk_service import analyze_risk_screening
from ..services.intelligence_service import analyze_competitive_intelligence

logger = logging.getLogger(__name__)

# =========================================================
# Graph State
# =========================================================

class PatentAnalysisState(TypedDict, total=False):
    # 当前任务类型
    mode: Literal["risk_analysis", "intelligence_analysis"]
    # 输入请求
    risk_request: Optional[RiskScreeningRequest]
    intelligence_request: Optional[IntelligenceAnalysisRequest]
    # 中间结果
    pg_risk_search_results: Optional[PatentSearchResult]
    chroma_risk_search_results: Optional[PatentSearchResult]
    merged_risk_results: Optional[PatentSearchResult]
    
    pg_intelligence_search_results: Optional[PatentSearchResult]
    chroma_intelligence_search_results: Optional[PatentSearchResult]
    merged_intelligence_results: Optional[PatentSearchResult]
    # 最终输出
    risk_result: Optional[RiskScreeningResult]
    intelligence_result: Optional[IntelligenceAnalysisResult]
    # 错误信息
    error_message: Optional[str]

# =========================================================
# 辅助函数：数据转换 / query 构建
# =========================================================
def _clean_parts(parts: List[Optional[str]]) -> List[str]:
    return [p.strip() for p in parts if p and p.strip()]

def _build_risk_query(request: RiskScreeningRequest) -> str:
    parts: List[Optional[str]] = []
    
    if request.product_name:
        parts.append(f"产品名称: {request.product_name}")
    if request.technical_description:
        parts.append(f"技术描述: {request.technical_description}")
    if request.core_features:
        parts.append(f"核心功能: {';'.join(request.core_features)}")
    if request.extra_requirements:
        parts.append(f"补充说明: {request.extra_requirements}")
    
    return ";".join(_clean_parts(parts))

def _build_intelligence_query(request: IntelligenceAnalysisRequest) -> str:
    parts: List[str] = []

    if request.domain:
        parts.append(request.domain)

    if request.keywords:
        parts.extend(request.keywords)

    if request.company_names:
        parts.extend(request.company_names)

    return ";".join(_clean_parts(parts))

def _merge_search_results(
    query: str,
    pg_results: Optional[PatentSearchResult],
    chroma_results: Optional[PatentSearchResult],
    top_k: int = 5
) -> PatentSearchResult:
    # 简单的去重合并逻辑，关键词检索在前
    # 后续可以改进为更智能的融合算法
    merged: Dict[str, PatentRecord] = {}
    for result in [pg_results, chroma_results]:
        if not result:
            continue
        for patent in result.patents:
            if patent.patent_id not in merged:
                merged[patent.patent_id] = patent
    
    patents = list(merged.values())[:top_k]
    return PatentSearchResult(
        query=query,
        patents=patents
    )

# =========================================================
# Graph 节点
# =========================================================
def route_task_node(state: PatentAnalysisState) -> Dict[str, Any]:
    # 判断任务类型
    mode = state.get("mode")
    if mode not in ["risk_analysis", "intelligence_analysis"]:
        return {"error_message": f"未知的任务模式: {mode}"}
    
    if mode == "risk_analysis":
        request = state.get("risk_request")
        if request is None:
            return {"error_message": "缺少风险分析请求数据"}
    elif mode == "intelligence_analysis":
        request = state.get("intelligence_request")
        if request is None:
            return {"error_message": "缺少情报分析请求数据"}
    return {"mode": mode}

# =========================================================
# Risk 并行检索节点
# =========================================================

def route_pg_risk_edge(state: PatentAnalysisState) -> str:
    # 根据任务类型进行pg检索
    if state.get("error_message"):
        logger.error(f"路由任务失败: {state['error_message']}")
        return "end"
    if state.get("mode") != "risk_analysis":
        return "end"
    return "pg_risk_search"

def route_chroma_risk_edge(state: PatentAnalysisState) -> str:
    # 根据任务类型进行chroma检索
    if state.get("error_message"):
        logger.error(f"路由任务失败: {state['error_message']}")
        return "end"
    if state.get("mode") != "risk_analysis":
        return "end"
    return "chroma_risk_search"

def route_merge_risk_edge(state: PatentAnalysisState) -> str:
    if state.get("error_message"):
        logger.error(f"路由任务失败: {state['error_message']}")
        return "end"
    return "merge_risk_search"

def pg_risk_search_node(state: PatentAnalysisState) -> Dict[str, Any]:
    # risk任务的pg检索
    try:
        request = state.get("risk_request")
        if request is None:
            return {"error_message": "缺少风险分析请求数据"}
        query = _build_risk_query(request)
        results = pg_search_patents(query=query)
        
        return {"pg_risk_search_results": PatentSearchResult(query=query, patents=results)}
    except Exception as e:
        logger.error(f"PG专利检索失败: {str(e)}")
        return {"error_message": f"PG专利检索失败: {str(e)}"}
    
def chroma_risk_search_node(state: PatentAnalysisState) -> Dict[str, Any]:
    # risk任务的chroma检索
    try:
        request = state.get("risk_request")
        if request is None:
            return {"error_message": "缺少风险分析请求数据"}
        query = _build_risk_query(request)
        results = chroma_search_patents(query=query)
        
        return {"chroma_risk_search_results": PatentSearchResult(query=query, patents=results)}
    except Exception as e:
        logger.error(f"Chroma专利检索失败: {str(e)}")
        return {"error_message": f"Chroma专利检索失败: {str(e)}"}

def merge_risk_search_node(state: PatentAnalysisState) -> Dict[str, Any]:
    pg_results = state.get("pg_risk_search_results")
    chroma_results = state.get("chroma_risk_search_results")
    if not pg_results and not chroma_results:
        return {"error_message": "缺少专利检索结果数据"}
    
    query = pg_results.query if pg_results else chroma_results.query
    merged_result = _merge_search_results(query, pg_results, chroma_results)
    return {"merged_risk_results": merged_result}

# =========================================================
# Intelligence 并行检索节点
# =========================================================

def route_pg_intelligence_edge(state: PatentAnalysisState) -> str:
    # 根据任务类型进行路由
    if state.get("error_message"):
        logger.error(f"路由任务失败: {state['error_message']}")
        return "end"
    if state.get("mode") != "intelligence_analysis":
        return "end"
    
    return "pg_intelligence_search"

def route_chroma_intelligence_edge(state: PatentAnalysisState) -> str:
    # 根据任务类型进行路由
    if state.get("error_message"):
        logger.error(f"路由任务失败: {state['error_message']}")
        return "end"
    if state.get("mode") != "intelligence_analysis":
        return "end"
    
    return "chroma_intelligence_search"

def route_merge_intelligence_edge(state: PatentAnalysisState) -> str:
    if state.get("error_message"):
        logger.error(f"路由任务失败: {state['error_message']}")
        return "end"
    return "merge_intelligence_search"

def pg_intelligence_search_node(state: PatentAnalysisState) -> Dict[str, Any]:
    # intelligence任务的pg检索
    try:
        request = state.get("intelligence_request")
        if request is None:
            return {"error_message": "缺少情报分析请求数据"}
        query = _build_intelligence_query(request)
        results = pg_search_patents(query=query)
        
        return {"pg_intelligence_search_results": PatentSearchResult(query=query, patents=results)}
    except Exception as e:
        logger.error(f"PG专利检索失败: {str(e)}")
        return {"error_message": f"PG专利检索失败: {str(e)}"}

def chroma_intelligence_search_node(state: PatentAnalysisState) -> Dict[str, Any]:
    # intelligence任务的chroma检索
    try:
        request = state.get("intelligence_request")
        if request is None:
            return {"error_message": "缺少情报分析请求数据"}
        query = _build_intelligence_query(request)
        results = chroma_search_patents(query=query)
        
        return {"chroma_intelligence_search_results": PatentSearchResult(query=query, patents=results)}
    except Exception as e:
        logger.error(f"Chroma专利检索失败: {str(e)}")
        return {"error_message": f"Chroma专利检索失败: {str(e)}"}

def merge_intelligence_search_node(state: PatentAnalysisState) -> Dict[str, Any]:
    pg_results = state.get("pg_intelligence_search_results")
    chroma_results = state.get("chroma_intelligence_search_results")
    if not pg_results and not chroma_results:
        return {"error_message": "缺少专利检索结果数据"}
    
    query = pg_results.query if pg_results else chroma_results.query
    merged_result = _merge_search_results(query, pg_results, chroma_results)
    return {"merged_intelligence_results": merged_result}

# =========================================================
# Analysis 节点
# =========================================================

def risk_analysis_node(state: PatentAnalysisState) -> Dict[str, Any]:
    try:
        request = state.get("risk_request")
        search_result = state.get("merged_risk_results")
        if request is None:
            return {"error_message": "缺少风险分析请求数据"}
        if search_result is None:
            return {"error_message": "缺少专利检索结果数据"}
        
        risk_analysis_input = RiskAnalysisInput(
            request=request,
            search_result=search_result
        )
        result = analyze_risk_screening(risk_analysis_input)
        return {"risk_result": result}
    except Exception as e:
        logger.error(f"技术风险预筛分析失败: {str(e)}")
        return {"error_message": f"技术风险预筛分析失败: {str(e)}"}

def intelligence_analysis_node(state: PatentAnalysisState) -> Dict[str, Any]:
    try:
        request = state.get("intelligence_request")
        search_result = state.get("merged_intelligence_results")
        if request is None:
            return {"error_message": "缺少情报分析请求数据"}
        if search_result is None:
            return {"error_message": "缺少专利检索结果数据"}
        
        intelligence_analysis_input = IntelligenceAnalysisInput(
            request=request,
            search_result=search_result
        )
        result = analyze_competitive_intelligence(intelligence_analysis_input)
        return {"intelligence_result": result}
    
    except Exception as e:
        logger.error(f"竞品情报分析失败: {str(e)}")
        return {"error_message": f"竞品情报分析失败: {str(e)}"}

# =========================================================
# 构建 Graph
# =========================================================
def build_patent_analysis_graph():
    graph = StateGraph(PatentAnalysisState)
    
    graph.add_node("route_task", route_task_node)
    # Risk 分支
    graph.add_node("pg_risk_search", pg_risk_search_node)
    graph.add_node("chroma_risk_search", chroma_risk_search_node)
    graph.add_node("merge_risk_search", merge_risk_search_node)
    graph.add_node("risk_analysis", risk_analysis_node)
    # Intelligence 分支
    graph.add_node("pg_intelligence_search", pg_intelligence_search_node)
    graph.add_node("chroma_intelligence_search", chroma_intelligence_search_node)
    graph.add_node("merge_intelligence_search", merge_intelligence_search_node)
    graph.add_node("intelligence_analysis", intelligence_analysis_node)
    # 路由边
    graph.add_edge(START, "route_task")
    graph.add_conditional_edges(
        "route_task",
        route_chroma_risk_edge,
        {
            "chroma_risk_search": "chroma_risk_search",
            "end": END
        }
    )
    graph.add_conditional_edges(
        "route_task",
        route_pg_risk_edge,
        {
            "pg_risk_search": "pg_risk_search",
            "end": END
        }
    )
    graph.add_conditional_edges(
        "route_task",
        route_chroma_intelligence_edge,
        {
            "chroma_intelligence_search": "chroma_intelligence_search",
            "end": END
        }
    )
    graph.add_conditional_edges(
        "route_task",
        route_pg_intelligence_edge,
        {
            "pg_intelligence_search": "pg_intelligence_search",
            "end": END
        }
    )
    
    # Risk 分支连接
    graph.add_conditional_edges(
        "pg_risk_search",
        route_merge_risk_edge,
        {
            "merge_risk_search": "merge_risk_search",
            "end": END
        }
    )
    graph.add_conditional_edges(
        "chroma_risk_search",
        route_merge_risk_edge,
        {
            "merge_risk_search": "merge_risk_search",
            "end": END
        }
    )
    graph.add_edge("merge_risk_search", "risk_analysis")
    graph.add_edge("risk_analysis", END)
    
    # Intelligence 分支连接
    graph.add_conditional_edges(
        "pg_intelligence_search",
        route_merge_intelligence_edge,
        {
            "merge_intelligence_search": "merge_intelligence_search",
            "end": END
        }
    )
    graph.add_conditional_edges(
        "chroma_intelligence_search",
        route_merge_intelligence_edge,
        {
            "merge_intelligence_search": "merge_intelligence_search",
            "end": END
        }
    )
    graph.add_edge("merge_intelligence_search", "intelligence_analysis")
    graph.add_edge("intelligence_analysis", END)
    
    return graph.compile()

patent_analysis_graph = build_patent_analysis_graph()


def _print_risk_result_pretty(risk_result: Any) -> None:
    print("\n===== 风险预筛结果 =====")
    if hasattr(risk_result, "model_dump"):
        data = risk_result.model_dump()
        for key, value in data.items():
            print(f"- {key}: {value}")
    else:
        print(risk_result)


def _print_intelligence_result_pretty(intelligence_result: Any) -> None:
    print("\n===== 竞品情报分析结果 =====")

    summary = getattr(intelligence_result, "summary", None)
    if summary:
        print(f"\n【摘要】\n{summary}")

    top_applicants = getattr(intelligence_result, "top_applicants", None) or []
    if top_applicants:
        print("\n【Top 申请人】")
        for idx, item in enumerate(top_applicants, 1):
            name = getattr(item, "applicant_name", "-")
            count = getattr(item, "patent_count", "-")
            topics = getattr(item, "main_topics", []) or []
            print(f"{idx}. {name} | 专利数: {count} | 主题: {', '.join(topics)}")

    filing_trends = getattr(intelligence_result, "filing_trends", None) or []
    if filing_trends:
        print("\n【申请趋势】")
        for point in filing_trends:
            period = getattr(point, "period", "-")
            count = getattr(point, "patent_count", "-")
            print(f"- {period}: {count}")

    hot_topics = getattr(intelligence_result, "hot_topics", None) or []
    if hot_topics:
        print("\n【热点技术】")
        for idx, topic in enumerate(hot_topics, 1):
            name = getattr(topic, "name", "-")
            keywords = getattr(topic, "keywords", []) or []
            topic_summary = getattr(topic, "summary", "")
            print(f"{idx}. {name}")
            print(f"   关键词: {', '.join(keywords)}")
            if topic_summary:
                print(f"   说明: {topic_summary}")

    representative_patents = getattr(intelligence_result, "representative_patents", None) or []
    if representative_patents:
        print("\n【代表专利】")
        for idx, patent in enumerate(representative_patents, 1):
            patent_id = getattr(patent, "patent_id", "-")
            title = getattr(patent, "title", "-")
            applicant = getattr(patent, "applicant", "-")
            pub_date = getattr(patent, "publication_date", "-")
            print(f"{idx}. [{patent_id}] {title}")
            print(f"   申请人: {applicant} | 公开日: {pub_date}")


if __name__ == "__main__":
    print("[patent_analysis_agent] graph compiled")
    test_state: PatentAnalysisState = {
        "mode": "intelligence_analysis",
        "intelligence_request": IntelligenceAnalysisRequest(
            domain="人工智能",
            keywords=["大模型", "机器学习"],
            company_names=["示例公司"],
            start_date="2020-01-01",
            end_date="2024-12-31"
        )
    }
    result: PatentAnalysisState = patent_analysis_graph.invoke(test_state)

    if result.get("error_message"):
        print("\n===== 执行失败 =====")
        print(result["error_message"])
    elif result.get("risk_result") is not None:
        _print_risk_result_pretty(result["risk_result"])
    elif result.get("intelligence_result") is not None:
        _print_intelligence_result_pretty(result["intelligence_result"])
    else:
        print(f"result: {result}")