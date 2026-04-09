from typing import Literal, List, Optional
from pydantic import BaseModel, Field
from ..models.schemas import RiskScreeningRequest, IntelligenceAnalysisRequest, RiskScreeningResult, IntelligenceAnalysisResult

class PatentRecord(BaseModel):
    """agent内部使用的专利记录结构"""
    patent_id: str = Field(..., description="专利号/公开号")
    title: str = Field(..., description="专利标题")
    applicant: Optional[str] = Field(default=None, description="申请人")
    publication_date: Optional[str] = Field(default=None, description="公开日期")
    ipc_codes: List[str] = Field(default_factory=list, description="IPC分类号")
    cpc_codes: List[str] = Field(default_factory=list, description="CPC分类号")
    abstract: Optional[str] = Field(default=None, description="专利摘要")
    claim_1: Optional[str] = Field(default=None, description="独立权利要求1")
    matched_reason: Optional[str] = Field(default=None, description="命中原因")

class PatentSearchResult(BaseModel):
    """专利检索Agent输出"""
    query: str = Field(..., description="实际检索查询")
    patents: List[PatentRecord] = Field(default_factory=list, description="候选专利列表")


class RiskAnalysisInput(BaseModel):
    """风险分析Agent输入"""
    request: RiskScreeningRequest
    search_result: PatentSearchResult


class IntelligenceAnalysisInput(BaseModel):
    """竞品情报分析Agent输入"""
    request: IntelligenceAnalysisRequest
    search_result: PatentSearchResult
