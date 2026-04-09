"""
当前节点分工：
   - route_task：任务分流
   - search_patents：专利检索
   - risk_analysis：技术风险预筛分析
   - intelligence_analysis：竞品情报分析
"""
import logging
from unittest import result
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Literal, Optional, Dict, Any
from ..models.schemas import(
    RiskScreeningRequest,
    IntelligenceAnalysisRequest,
    RiskScreeningResult,
    IntelligenceAnalysisResult,
    PatentSummary
)
from ..models.agent_structs import(
    PatentSearchResult,
    RiskAnalysisInput,
    IntelligenceAnalysisInput
)
from ..services.patent_service import search_patents, get_patent_detail
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
    search_results: Optional[PatentSearchResult]
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

def _to_patent_summary(record: PatentSearchResult) -> PatentSummary:
    """将专利检索结果转换为专利摘要"""
    return PatentSummary(
        patent_id=record.patent_id,
        title=record.title,
        applicant=record.applicant,
        publication_date=record.publication_date,
        ipc_codes=record.ipc_codes,
        cpc_codes=record.cpc_codes,
    )

def _build_risk_query(request: RiskScreeningRequest) -> str:
    parts: List[Optional[str]] = []
    
    if request.product_name:
        parts.append(f"产品名称: {request.product_name}")
    if request.technical_description:
        parts.append(f"技术描述: {request.technical_description}")
    if request.core_features:
        parts.append(f"核心功能: {request.core_features}")
    if request.core_features:
        parts.append(f"核心技术: {request.core_technology}")
    
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

def route_task_edge(state: PatentAnalysisState) -> str:
    # 判断路由类型
    if state.get("error_message"):
        logger.error(f"路由任务失败: {state['error_message']}")
        return "end"
    return "search_patents"

def search_patents_node(state: PatentAnalysisState) -> Dict[str, Any]:
    try:
        mode = state.get("mode")
        if mode == "risk_analysis":
            request = state.get("risk_request")
            if request is None:
                return {"error_message": "缺少风险分析请求数据"}
            
            query = _build_risk_query(request)
            patents = search_patents(query=query, top_k=10)
            return {"search_results": patents}
            
        elif mode == "intelligence_analysis":
            request = state.get("intelligence_request")
            if request is None:
                return {"error_message": "缺少情报分析请求数据"}
            
            query = _build_intelligence_query(request)
            
            applicant = request.company_names[0] if request.company_names else None
            patents = search_patents(
                query=query,
                top_k=10,
                applicant=applicant,
                start_date=request.start_date,
                end_date=request.end_date
            )
        else:
            return {"error_message": f"无效的模式: {mode}"}
        
        search_results = PatentSearchResult(
            query=query,
            patents=patents,
        )
        return {"search_results": search_results}
    except Exception as e:
        logger.exception("专利检索失败")
        return {"error_message": f"专利检索失败: {str(e)}"}
    
def search_to_analysis_edge(state: PatentAnalysisState) -> str:
    if state.get("error_message"):
        logger.error(f"专利检索失败: {state['error_message']}")
        return "end"
    
    mode = state.get("mode")
    if mode == "risk_analysis":
        return "risk_analysis"
    elif mode == "intelligence_analysis":
        return "intelligence_analysis"
    
    return "end"

def risk_analysis_node(state: PatentAnalysisState) -> Dict[str, Any]:
    try:
        request = state.get("risk_request")
        search_result = state.get("search_results")
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
        search_result = state.get("search_results")
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
    graph.add_node("routr_task", route_task_node)
    graph.add_node("search_patents", search_patents_node)
    graph.add_node("risk_analysis", risk_analysis_node)
    graph.add_node("intelligence_analysis", intelligence_analysis_node)
    
    graph.add_edge(START, "routr_task")
    graph.add_conditional_edges(
        "routr_task", 
        route_task_edge,
        {
            "search_patents": "search_patents",
            "end": END
        }
    )
    graph.add_conditional_edges(
        "search_patents",
        search_to_analysis_edge,
        {
            "risk_analysis": "risk_analysis",
            "intelligence_analysis": "intelligence_analysis",
            "end": END
        }
    )
    graph.add_edge("risk_analysis", END)
    graph.add_edge("intelligence_analysis", END)
    
    return graph.compile()

build_patent_analysis_graph = build_patent_analysis_graph()


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
    result = build_patent_analysis_graph.invoke(test_state)
    print("[patent_analysis_agent] smoke test result:", result)