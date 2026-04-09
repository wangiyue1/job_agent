from ..models.schemas import (
    PatentEvidence,
    PatentSummary,
    RiskItem,
    RiskScreeningRequest,
    RiskScreeningResult,
)

from ..models.agent_structs import RiskAnalysisInput

def analyze_risk_screening(
    input: RiskAnalysisInput
) -> RiskScreeningResult:
    request = input.request
    search_result = input.search_result

    product_name = request.product_name or "未命名产品"
    core_features = request.core_features or []

    candidate_patents = [
        PatentSummary(
            patent_id="MOCK-CN-200001",
            title="一种电池热管理与保护控制方法",
            applicant="Job Agent Test Corp.",
            publication_date="2025-11-20",
            ipc_codes=["H01M10/0525"],
            cpc_codes=["H01M10/44"],
        ),
        PatentSummary(
            patent_id="MOCK-CN-200002",
            title="电池管理系统的异常检测策略",
            applicant="Job Agent Test Corp.",
            publication_date="2026-01-10",
            ipc_codes=["H01M10/48"],
            cpc_codes=["B60L58/16"],
        ),
    ]

    risk_items = [
        RiskItem(
            level="medium",
            title="核心功能可能与现有专利权利要求重叠",
            description=(
                f"产品 {product_name} 的关键能力与已公开专利在技术路径上存在潜在交叉，"
                "建议在立项阶段进行权利要求逐条比对。"
            ),
            suggestion="补充关键技术差异点，必要时进行绕开设计。",
            evidences=[
                PatentEvidence(
                    patent_id="MOCK-CN-200001",
                    patent_title="一种电池热管理与保护控制方法",
                    section="claim1",
                    text="一种热管理控制方法，包括温度监测、阈值判断与冷却执行。",
                    note="与热管理控制逻辑存在可比性。",
                )
            ],
        )
    ]

    if core_features:
        risk_items.append(
            RiskItem(
                level="pending_review",
                title="核心功能需人工逐项确认",
                description="核心功能列表较多，建议逐项与候选专利独立权利要求做映射。",
                suggestion="优先确认与商业化路径相关的高价值功能点。",
                evidences=[],
            )
        )

    pending_questions = [
        "是否已明确产品的必选技术特征与可替代方案？",
        "是否需要限定目标市场（如中国/美国/欧洲）后再做深入检索？",
    ]

    if core_features:
        pending_questions.append(f"请确认核心功能优先级：{', '.join(core_features)}")

    return RiskScreeningResult(
        summary=(
            "Mock 风险预筛结果：当前结果用于验证服务连通性与返回结构，"
            "不构成法律意见。"
        ),
        candidate_patents=candidate_patents,
        risk_items=risk_items,
        pending_questions=pending_questions,
    )
