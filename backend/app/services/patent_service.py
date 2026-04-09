from typing import List, Optional

from ..models.agent_structs import PatentRecord


def search_patents(
    query: str,
    top_k: int = 10,
    applicant: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[PatentRecord]:
    """
    专利检索服务（当前为占位实现）
    后续这里可以接：
    - 公开专利API
    - 本地数据库
    - 向量检索
    """
    return [
        PatentRecord(
            patent_id="CN123456A",
            title="一种电池热管理控制方法",
            applicant="示例公司A",
            publication_date="2024-01-01",
            ipc_codes=["H01M10/0525"],
            cpc_codes=["H01M10/44"],
            abstract="本发明涉及一种电池热管理控制方法，用于降低热失控风险。",
            claim_1="一种电池热管理控制方法，其特征在于包括温度监测、阈值判断与冷却控制步骤。",
            matched_reason="与热管理、热失控保护相关",
        ),
        PatentRecord(
            patent_id="CN234567A",
            title="一种电池管理系统及其保护策略",
            applicant="示例公司B",
            publication_date="2024-03-15",
            ipc_codes=["H01M10/48"],
            cpc_codes=["B60L58/16"],
            abstract="公开了一种电池管理系统，支持异常检测与多级保护。",
            claim_1="一种电池管理系统，包括采样模块、控制模块和保护模块。",
            matched_reason="与电池管理系统和保护机制相关",
        ),
    ]


def get_patent_detail(patent_id: str) -> Optional[PatentRecord]:
    """
    单篇专利详情查询（当前为占位实现）
    """
    for patent in search_patents(query=patent_id, top_k=2):
        if patent.patent_id == patent_id:
            return patent
    return None
