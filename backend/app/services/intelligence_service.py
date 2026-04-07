from ..models.schemas import (
    ApplicantStat,
    IntelligenceAnalysisRequest,
    IntelligenceAnalysisResult,
    PatentSummary,
    TechTopicItem,
    TrendPoint,
)

def analyze_competitive_intelligence(
    request: IntelligenceAnalysisRequest,
) -> IntelligenceAnalysisResult:
    domain = request.domain or "通用技术方向"

    return IntelligenceAnalysisResult(
        summary=f"Mock 竞品情报结果：{domain}，路由与服务连通正常。",
        top_applicants=[
            ApplicantStat(
                applicant_name="Job Agent Test Corp.",
                patent_count=3,
                main_topics=["mock-topic-a", "mock-topic-b"],
            )
        ],
        filing_trends=[
            TrendPoint(period="2025-Q4", patent_count=1),
            TrendPoint(period="2026-Q1", patent_count=2),
        ],
        hot_topics=[
            TechTopicItem(
                name="连通性测试主题",
                keywords=["mock", "api", "test"],
                summary="用于验证 intelligence 路由返回结构。",
                representative_patents=["MOCK-CN-100001"],
            )
        ],
        representative_patents=[
            PatentSummary(
                patent_id="MOCK-CN-100001",
                title="用于竞品情报路由测试的示例专利",
                applicant="Job Agent Test Corp.",
                publication_date="2026-02-01",
                ipc_codes=["H04L"],
                cpc_codes=["H04L9/00"],
            )
        ],
    )