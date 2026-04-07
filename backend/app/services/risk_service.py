from ..models.schemas import (
    PatentEvidence,
    PatentSummary,
    RiskItem,
    RiskScreeningRequest,
    RiskScreeningResult,
)

def analyze_risk_screening(request: RiskScreeningRequest) -> RiskScreeningResult:
    product_name = request.product_name or "未命名产品"

    return RiskScreeningResult(
        summary=f"Mock 风险预筛结果：{product_name}，路由与服务连通正常。",
        candidate_patents=[
            PatentSummary(
                patent_id="MOCK-CN-000001",
                title="用于路由连通性测试的示例专利",
                applicant="Job Agent Test",
                publication_date="2026-01-01",
                ipc_codes=["G06F"],
                cpc_codes=["G06F16/00"],
            )
        ],
        risk_items=[
            RiskItem(
                level="low",
                title="连通性测试风险项",
                description="该条目用于验证 API 返回结构是否正确。",
                suggestion="如需业务逻辑，请替换 service 中的 mock 实现。",
                evidences=[
                    PatentEvidence(
                        patent_id="MOCK-CN-000001",
                        patent_title="用于路由连通性测试的示例专利",
                        section="abstract",
                        text="这是用于接口测试的模拟证据文本。",
                        note="mock-data",
                    )
                ],
            )
        ],
        pending_questions=[
            "是否需要接入真实检索引擎？",
            "是否需要风险评分细则？",
        ],
    )