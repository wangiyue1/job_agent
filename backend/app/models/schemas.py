from typing import List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime, date

class BaseEntity(BaseModel):
    id: str = Field(..., description="唯一ID")
    source: Optional[str] = Field(None, description="数据来源")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

IndustryType = Literal["internet", "finance", "healthcare", "education", "manufacturing", "new_energy", "other"]
CompanySize = Literal["0-99", "100-999", "1000-9999", "10000+"]
CompanyType = Literal["foreign", "private", "state_owned", "other"]

class Company(BaseEntity):
    """公司模型"""
    name: str = Field(..., description="公司名称")
    industry: Optional[IndustryType] = Field(None, description="所属行业")
    stage: Optional[str] = Field(default=None, description="融资/发展阶段")
    size: Optional[CompanySize] = Field(default=None, description="公司规模")
    type: Optional[CompanyType] = Field(default=None, description="公司类型")
    location: Optional[str] = Field(default=None, description="公司所在城市")
    website: Optional[str] = None
    introduction: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="公司标签")

EducationRequirement = Literal["bachelor", "master", "phd"]
class Job(BaseEntity):
    """岗位模型"""
    title: str = Field(..., description="岗位名称")
    company_id: str = Field(..., description="所属公司ID")
    city: List[str] = Field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    education_requirement: Optional[EducationRequirement] = None
    jd_text: str = Field(..., description="岗位描述原文")
    jd_url: Optional[str] = None
    publish_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)

SkillCategory = Literal["programming_language", "large_language_model", "autonomous_driving", "other"]
class Skill(BaseEntity):
    """技能模型"""
    name: str = Field(..., description="技能名称")
    category: SkillCategory = Field(..., description="技能类别")

class Resume(BaseEntity):
    """简历模型"""
    content: str = Field(..., description="简历内容原文")  
    skills: List[str] = Field(default_factory=list)
    
class ApplicationRecord(BaseEntity):
    """投递记录模型"""
    company_id: str = Field(..., description="公司ID")
    job_id: str = Field(..., description="岗位ID")
    apply_date: Optional[date] = None
    status: Literal["applied", "interview", "offer", "rejected"] = "applied"
    tags: List[str] = Field(default_factory=list)

class LogEntry(BaseEntity):
    """日志模型"""
    source_type: Literal["github", "feishu", "local_doc", "other"] = "other"
    title: Optional[str] = None
    content: Optional[str] = None
    log_time: Optional[date] = None
    tags: List[str] = Field(default_factory=list)

class DocumentChunk(BaseEntity):
    """文档切片"""
    document_id: str = Field(..., description="原始文档ID")
    title: Optional[str] = None
    content: str = Field(..., description="切片内容")
    chunk_index: int = Field(..., description="切片索引")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MatchResult(BaseModel):
    """匹配结果"""
    job_id: str = Field(..., description="岗位ID")
    resume_id: str = Field(..., description="简历ID")
    overall_score: float = Field(..., ge=0, le=100)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    suggestion: str

class WeeklyReport(BaseModel):
    """周报模型"""
    week_start: date = Field(..., description="周报开始日期")
    week_end: date = Field(..., description="周报结束日期")
    summary: str = Field(..., description="周报摘要")
    completed_items: List[str] = Field(default_factory=list)
    next_week_plan: Optional[str] = None

# ============ 请求模型 ============
class JobSearchRequest(BaseModel):
    """岗位搜索请求模型"""
    keywords: List[str] = Field(..., description="搜索关键词列表")
    cities: List[str] = Field(default_factory=list, description="城市")
    education: Optional[EducationRequirement] = Field(None, description="学历要求")
    industries: List[IndustryType] = Field(default_factory=list, description="行业")

class WeeklyLogRequest(BaseModel):
    """周报请求模型"""
    week_start: date = Field(..., description="周报开始日期")
    week_end: date = Field(..., description="周报结束日期")
    sources: List[Literal["github", "feishu", "local_doc", "other"]] = Field(default_factory=list, description="日志来源")
    project_filter: Optional[List[str]] = None

class ApplicationAdviceRequest(BaseModel):
    """申请建议请求模型"""
    include_company_analysis: bool = True
    include_resume_match: bool = True

class InsightRequest(BaseModel):
    company_name: Optional[str] = None
    job_name: Optional[str] = None
    resume_id: Optional[str] = None
    analysis_type: Literal[
        "company_profile", "job_profile", "job_resume_match", "company_risk"
    ]
# ============ 响应模型 ============
class JobSearchResponse(BaseModel):
    jobs: List[Job]
    total_found: int = Field(..., description="总匹配岗位数")
    search_summary: str

class WeeklyLogResponse(BaseModel):
    entries: List[LogEntry]
    merged_summary: Optional[str] = None

class ApplicationAdvice(BaseModel):
    company_analysis: Optional[str] = None
    resume_match: Optional[MatchResult] = None
    overall_suggestion: str = Field(..., description="综合建议")

class InsightResult(BaseModel):
    analysis_type: Literal[
        "company_profile", "job_profile", "job_resume_match", "company_risk"
    ]
    summary: str
