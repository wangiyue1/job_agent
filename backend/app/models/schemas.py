from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# =========================
# 请求模型
# =========================

class RiskScreeningRequest(BaseModel):
    """技术风险预筛请求"""
    product_name: Optional[str] = Field(default=None, description="产品名称")
    technical_description: str = Field(..., description="技术方案/产品描述")
    core_features: List[str] = Field(default_factory=list, description="核心功能点")
    extra_requirements: Optional[str] = Field(default=None, description="补充说明")


class IntelligenceAnalysisRequest(BaseModel):
    """竞品情报分析请求"""
    keywords: List[str] = Field(default_factory=list, description="技术关键词")
    company_names: List[str] = Field(default_factory=list, description="公司名称")
    domain: Optional[str] = Field(default=None, description="赛道/技术方向")
    start_date: Optional[str] = Field(default=None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="结束日期 YYYY-MM-DD")


# =========================
# 响应模型：最小单元
# =========================

class PatentSummary(BaseModel):
    """专利摘要信息"""
    patent_id: str = Field(..., description="专利号/公开号")
    title: str = Field(..., description="专利标题")
    applicant: Optional[str] = Field(default=None, description="申请人")
    publication_date: Optional[str] = Field(default=None, description="公开日期")
    ipc_codes: List[str] = Field(default_factory=list, description="IPC分类号")
    cpc_codes: List[str] = Field(default_factory=list, description="CPC分类号")


class PatentEvidence(BaseModel):
    """专利证据片段"""
    patent_id: str = Field(..., description="专利号/公开号")
    patent_title: str = Field(..., description="专利标题")
    section: Literal["abstract", "claim1", "description"] = Field(..., description="证据来源章节")
    text: str = Field(..., description="证据原文")
    note: Optional[str] = Field(default=None, description="证据说明")


class RiskItem(BaseModel):
    """风险点"""
    level: Literal["high", "medium", "low", "pending_review"] = Field(..., description="风险等级")
    title: str = Field(..., description="风险点标题")
    description: str = Field(..., description="风险说明")
    suggestion: Optional[str] = Field(default=None, description="建议")
    evidences: List[PatentEvidence] = Field(default_factory=list, description="支撑证据")


class ApplicantStat(BaseModel):
    """申请人统计项"""
    applicant_name: str = Field(..., description="申请人名称")
    patent_count: int = Field(default=0, description="专利数量")
    main_topics: List[str] = Field(default_factory=list, description="主要技术方向")


class TrendPoint(BaseModel):
    """时间趋势点"""
    period: str = Field(..., description="时间区间，如 2024-Q1 / 2025-01")
    patent_count: int = Field(default=0, description="专利数量")


class TechTopicItem(BaseModel):
    """技术主题项"""
    name: str = Field(..., description="技术主题名称")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    summary: str = Field(..., description="主题摘要")
    representative_patents: List[str] = Field(default_factory=list, description="代表专利号")


# =========================
# 响应模型：组合结果
# =========================

class RiskScreeningResult(BaseModel):
    """技术风险预筛结果"""
    summary: str = Field(..., description="总体结论")
    candidate_patents: List[PatentSummary] = Field(default_factory=list, description="候选专利")
    risk_items: List[RiskItem] = Field(default_factory=list, description="风险点列表")
    pending_questions: List[str] = Field(default_factory=list, description="待人工确认事项")
    disclaimer: str = Field(
        default="本结果仅用于技术风险预筛，不构成法律意见。",
        description="免责声明"
    )


class IntelligenceAnalysisResult(BaseModel):
    """竞品情报分析结果"""
    summary: str = Field(..., description="总体摘要")
    top_applicants: List[ApplicantStat] = Field(default_factory=list, description="重点申请人")
    filing_trends: List[TrendPoint] = Field(default_factory=list, description="申请趋势")
    hot_topics: List[TechTopicItem] = Field(default_factory=list, description="技术热点/技术路线")
    representative_patents: List[PatentSummary] = Field(default_factory=list, description="代表专利")


# =========================
# 响应模型：顶层响应
# =========================

class RiskScreeningResponse(BaseModel):
    """技术风险预筛响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="响应消息")
    data: Optional[RiskScreeningResult] = Field(default=None, description="风险预筛结果")


class IntelligenceAnalysisResponse(BaseModel):
    """竞品情报分析响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="响应消息")
    data: Optional[IntelligenceAnalysisResult] = Field(default=None, description="竞品情报结果")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False, description="是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(default=None, description="错误代码")
