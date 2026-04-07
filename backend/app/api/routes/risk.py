from fastapi import APIRouter, HTTPException

from ...models.schemas import (
    RiskScreeningRequest,
    RiskScreeningResponse,
)
from ...services.risk_service import analyze_risk_screening

router = APIRouter(prefix="/risk", tags=["技术风险预筛"])


@router.post(
    "/analyze",
    response_model=RiskScreeningResponse,
    summary="技术风险预筛",
    description="根据用户输入的产品/技术方案，输出风险预筛结果",
)
async def analyze_risk(request: RiskScreeningRequest) -> RiskScreeningResponse:
    try:
        result = analyze_risk_screening(request)

        return RiskScreeningResponse(
            success=True,
            message="技术风险预筛成功",
            data=result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"技术风险预筛失败: {str(e)}",
        )


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "risk-screening",
    }
