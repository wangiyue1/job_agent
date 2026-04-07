from fastapi import APIRouter, HTTPException

from ...models.schemas import (
    IntelligenceAnalysisRequest,
    IntelligenceAnalysisResponse,
)
from ...services.intelligence_service import analyze_competitive_intelligence

router = APIRouter(prefix="/intelligence", tags=["竞品情报分析"])


@router.post(
    "/analyze",
    response_model=IntelligenceAnalysisResponse,
    summary="竞品情报分析",
    description="根据技术关键词、公司名或赛道，输出竞品情报分析结果",
)
async def analyze_intelligence(
    request: IntelligenceAnalysisRequest,
) -> IntelligenceAnalysisResponse:
    try:
        result = analyze_competitive_intelligence(request)

        return IntelligenceAnalysisResponse(
            success=True,
            message="竞品情报分析成功",
            data=result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"竞品情报分析失败: {str(e)}",
        )


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "competitive-intelligence",
    }
