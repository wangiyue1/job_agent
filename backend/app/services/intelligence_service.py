from collections import Counter, defaultdict

from ..models.schemas import (
    ApplicantStat,
    IntelligenceAnalysisResult,
    PatentSummary,
    TechTopicItem,
    TrendPoint,
)
from ..models.agent_structs import IntelligenceAnalysisInput


def _to_quarter(period_str: str | None) -> str:
    if not period_str:
        return "未知"
    if len(period_str) < 7:
        return "未知"
    try:
        year = int(period_str[0:4])
        month = int(period_str[5:7])
    except ValueError:
        return "未知"
    if month < 1 or month > 12:
        return "未知"
    quarter = (month - 1) // 3 + 1
    return f"{year}-Q{quarter}"


def _extract_topics_from_patent(patent) -> list[str]:
    topics: list[str] = []
    topics.extend(code for code in (patent.ipc_codes or []) if code)
    topics.extend(code for code in (patent.cpc_codes or []) if code)

    title = (patent.title or "").strip()
    if title:
        topics.append(title)
    return topics

def analyze_competitive_intelligence(
    input: IntelligenceAnalysisInput,
) -> IntelligenceAnalysisResult:
    request = input.request
    domain = request.domain or "通用技术方向"
    patents = input.search_result.patents or []

    applicant_counter: Counter[str] = Counter()
    applicant_topics: dict[str, Counter[str]] = defaultdict(Counter)
    trend_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    topic_patents: dict[str, list[str]] = defaultdict(list)

    for patent in patents:
        applicant_name = (patent.applicant or "未知申请人").strip() or "未知申请人"
        applicant_counter[applicant_name] += 1

        for topic in _extract_topics_from_patent(patent):
            applicant_topics[applicant_name][topic] += 1
            topic_counter[topic] += 1
            if patent.patent_id and patent.patent_id not in topic_patents[topic]:
                topic_patents[topic].append(patent.patent_id)

        trend_counter[_to_quarter(patent.publication_date)] += 1

    top_applicants = []
    for applicant_name, patent_count in applicant_counter.most_common(5):
        main_topics = [name for name, _ in applicant_topics[applicant_name].most_common(3)]
        top_applicants.append(
            ApplicantStat(
                applicant_name=applicant_name,
                patent_count=patent_count,
                main_topics=main_topics,
            )
        )

    filing_trends = [
        TrendPoint(period=period, patent_count=count)
        for period, count in sorted(trend_counter.items(), key=lambda x: x[0])
    ]

    hot_topics = []
    for topic_name, count in topic_counter.most_common(5):
        reps = topic_patents.get(topic_name, [])[:3]
        hot_topics.append(
            TechTopicItem(
                name=topic_name,
                keywords=[topic_name],
                summary=f"该主题在候选专利中出现 {count} 次。",
                representative_patents=reps,
            )
        )

    representative_patents = [
        PatentSummary(
            patent_id=patent.patent_id,
            title=patent.title,
            applicant=patent.applicant,
            publication_date=patent.publication_date,
            ipc_codes=patent.ipc_codes,
            cpc_codes=patent.cpc_codes,
        )
        for patent in patents[:5]
    ]

    if patents:
        top_applicant_name = top_applicants[0].applicant_name if top_applicants else "未知"
        summary = (
            f"在“{domain}”方向共分析 {len(patents)} 篇候选专利，"
            f"重点申请人为 {top_applicant_name}。"
        )
    else:
        summary = f"在“{domain}”方向未检索到候选专利，暂无可分析的竞品情报。"

    return IntelligenceAnalysisResult(
        summary=summary,
        top_applicants=top_applicants,
        filing_trends=filing_trends,
        hot_topics=hot_topics,
        representative_patents=representative_patents,
    )