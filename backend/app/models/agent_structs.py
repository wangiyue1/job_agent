from typing import Literal, List, Optional
from pydantic import BaseModel, Field
from ..models.schemas import RiskScreeningRequest, IntelligenceAnalysisRequest

class PatentChunk(BaseModel):
    # agent 内部命中结果
    chunk_id: str = Field(..., description='chunk唯一标识，格式建议为 patent_id + "_" + chunk序号')
    patent_id: str = Field(..., description="专利号/公开号")
    chunk_index: int = Field(..., description="chunk序号，从0开始")
    section: Literal["abstract", "claim1", "description"] = Field(..., description="文本来源章节")
    text: str = Field(..., description="文本内容")
    score: Optional[float] = Field(default=None, description="与查询的相关度分数")
    
class PatentRecord(BaseModel):
    # agent内部使用的专利记录结构
    patent_id: str = Field(..., description="专利号/公开号")
    title: str = Field(..., description="专利标题")
    applicant: Optional[str] = Field(default=None, description="申请人")
    publication_date: Optional[str] = Field(default=None, description="公开日期")
    ipc_codes: List[str] = Field(default_factory=list, description="IPC分类号")
    cpc_codes: List[str] = Field(default_factory=list, description="CPC分类号")
    abstract: Optional[str] = Field(default=None, description="专利摘要")
    claim_1: Optional[str] = Field(default=None, description="独立权利要求1")
    
    score: Optional[float] = Field(default=None, description="与查询的相关度分数")
    matched_chunks: List[PatentChunk] = Field(default_factory=list, description="命中的chunk列表，作为证据返回")    
    
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
