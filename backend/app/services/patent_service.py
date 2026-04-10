from typing import List, Optional

from ..models.agent_structs import PatentRecord

def pg_search_patents(query: str, top_k:int = 10) -> List[PatentRecord]:
    return [
        PatentRecord(
            patent_id="PG-CN100001A",
            title="PG检索-电池热管理方法",
            applicant="PG示例公司A",
            publication_date="2023-01-10",
            ipc_codes=["H01M10/0525"],
            cpc_codes=["H01M10/44"],
            abstract=f"基于关键词进行检索的占位结果，query={query}",
            claim_1="一种热管理控制方法，包括采集温度并执行阈值控制。",
            matched_reason="PG mock 命中结果 1",
        ),
        PatentRecord(
            patent_id="PG-CN100002A",
            title="PG检索-电池管理系统",
            applicant="PG示例公司B",
            publication_date="2023-06-18",
            ipc_codes=["H01M10/48"],
            cpc_codes=["B60L58/16"],
            abstract=f"用于工作流测试的固定专利结果，query={query}",
            claim_1="一种电池管理系统，包括采样、诊断和保护模块。",
            matched_reason="PG mock 命中结果 2",
        ),
        PatentRecord(
            patent_id="PG-CN100003A",
            title="PG检索-热失控预警策略",
            applicant="PG示例公司C",
            publication_date="2024-02-26",
            ipc_codes=["G01R31/36"],
            cpc_codes=["G01R31/382"],
            abstract=f"用于联调图流程的固定返回数据，query={query}",
            claim_1="一种热失控预警方法，包括特征提取与分级告警。",
            matched_reason="PG mock 命中结果 3",
        ),
    ]

def chroma_search_patents(query: str, top_k:int = 10) -> List[PatentRecord]:
    return [
        PatentRecord(
            patent_id="CH-CN200001A",
            title="Chroma检索-电池散热结构",
            applicant="Chroma示例公司A",
            publication_date="2022-11-09",
            ipc_codes=["H01M10/6556"],
            cpc_codes=["H01M10/6567"],
            abstract=f"向量检索占位结果，query={query}",
            claim_1="一种散热结构，包括导热层和风冷通道。",
            matched_reason="Chroma mock 命中结果 1",
        ),
        PatentRecord(
            patent_id="CH-CN200002A",
            title="Chroma检索-电芯异常检测方法",
            applicant="Chroma示例公司B",
            publication_date="2023-08-03",
            ipc_codes=["G01R31/385"],
            cpc_codes=["G01R31/389"],
            abstract=f"用于测试语义检索分支的固定结果，query={query}",
            claim_1="一种异常检测方法，包括数据清洗、建模与阈值判断。",
            matched_reason="Chroma mock 命中结果 2",
        ),
        PatentRecord(
            patent_id="CH-CN200003A",
            title="Chroma检索-多级保护控制系统",
            applicant="Chroma示例公司C",
            publication_date="2024-01-21",
            ipc_codes=["B60L58/18"],
            cpc_codes=["B60L58/24"],
            abstract=f"用于工作流冒烟测试的固定返回，query={query}",
            claim_1="一种多级保护控制系统，包括检测单元和执行单元。",
            matched_reason="Chroma mock 命中结果 3",
        ),
    ]

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
