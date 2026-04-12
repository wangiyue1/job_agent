import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field
from langchain_core.documents import Document


class PatentJsonRecord(BaseModel):
    """
    中间层专利记录：
    - 用于 txt -> json
    - 用于 json -> LangChain Document
    - 用于 json -> PostgreSQL rows

    注意：
    1. 这是“现实兼容层”，忠实反映当前拿到的 CNKI 导出字段。
    2. 不强行假设当前数据中一定存在 description / IPC / CPC。
    3. 将暂不纳入顶层 schema 的字段保存在 raw_fields 中，便于未来扩展。
    """

    patent_id: str = Field(..., description="由 PubNo-公开号 映射")
    title: str = Field(..., description="由 Title-题名 映射")
    applicant: Optional[str] = Field(default=None, description="申请人")
    publication_date: Optional[str] = Field(default=None, description="公开日期，原始字符串格式")
    abstract: Optional[str] = Field(default=None, description="摘要")
    claim_1: Optional[str] = Field(default=None, description="主权项/近似独立权利要求1")
    classification_codes: List[str] = Field(default_factory=list, description="原始分类号，当前主要来自 CLC")
    raw_fields: Dict[str, Any] = Field(default_factory=dict, description="未纳入顶层 schema 的原始字段")


class PatentTXTLoader:
    """
    负责：
    1. 读取 CNKI txt
    2. 拆分专利记录
    3. 解析为 PatentJsonRecord
    4. 转为 LangChain Document（兼容旧链路）
    5. 转为 PostgreSQL rows（新主链路）
    """

    FIELD_PATTERN = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)-[^:：]+[:：]\s*(.*)$")
    RECORD_START_PREFIX = "SrcDatabase-来源库:"

    def __init__(self) -> None:
        pass

    # =========
    # 文件读取
    # =========
    @staticmethod
    def read_text(file_path: str | Path, encoding: str = "utf-8") -> str:
        path = Path(file_path)
        return path.read_text(encoding=encoding)

    # =========
    # 记录拆分
    # =========
    def split_records(self, text: str) -> List[str]:
        if not text.strip():
            return []

        lines = text.splitlines()
        blocks: List[List[str]] = []
        current_block: List[str] = []

        for raw_line in lines:
            line = raw_line.rstrip()

            if not line.strip():
                if current_block:
                    current_block.append("")
                continue

            if line.startswith(self.RECORD_START_PREFIX):
                if current_block:
                    blocks.append(current_block)
                current_block = [line]
            else:
                if current_block:
                    current_block.append(line)
                else:
                    current_block = [line]

        if current_block:
            blocks.append(current_block)

        cleaned_blocks: List[str] = []
        for block in blocks:
            joined = "\n".join(block).strip()
            if joined:
                cleaned_blocks.append(joined)

        return cleaned_blocks

    # =========
    # 单条记录解析
    # =========
    def parse_record_block(self, block_text: str) -> PatentJsonRecord:
        raw_map: Dict[str, str] = {}
        current_key: Optional[str] = None

        for raw_line in block_text.splitlines():
            line = raw_line.strip()

            if not line:
                if current_key and raw_map.get(current_key):
                    raw_map[current_key] += "\n"
                continue

            match = self.FIELD_PATTERN.match(line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                raw_map[key] = value
                current_key = key
            else:
                if current_key:
                    prev = raw_map.get(current_key, "")
                    if prev and not prev.endswith("\n"):
                        raw_map[current_key] = prev + " " + line
                    else:
                        raw_map[current_key] = prev + line

        return self._normalize_raw_map(raw_map)

    def _normalize_raw_map(self, raw_map: Dict[str, str]) -> PatentJsonRecord:
        patent_id = self._clean_text(raw_map.get("PubNo"))
        title = self._clean_text(raw_map.get("Title"))

        if not patent_id:
            raise ValueError(f"缺少 PubNo，无法生成 patent_id。raw_map={raw_map}")
        if not title:
            raise ValueError(f"缺少 Title，无法生成 title。raw_map={raw_map}")

        applicant = self._clean_text(raw_map.get("Applicant"))
        publication_date = self._clean_text(raw_map.get("PubTime"))
        abstract = self._clean_text(raw_map.get("Summary"))
        claim_1 = self._clean_text(raw_map.get("Claims"))
        classification_codes = self._split_codes(raw_map.get("CLC"))

        used_keys = {
            "PubNo",
            "Title",
            "Applicant",
            "PubTime",
            "Summary",
            "Claims",
            "CLC",
        }

        raw_fields = {
            key: self._clean_text(value)
            for key, value in raw_map.items()
            if key not in used_keys and self._clean_text(value) is not None
        }

        return PatentJsonRecord(
            patent_id=patent_id,
            title=title,
            applicant=applicant,
            publication_date=publication_date,
            abstract=abstract,
            claim_1=claim_1,
            classification_codes=classification_codes,
            raw_fields=raw_fields,
        )

    # =========
    # 批量加载
    # =========
    def load_records_from_text(self, text: str, *, skip_errors: bool = True) -> List[PatentJsonRecord]:
        records: List[PatentJsonRecord] = []
        blocks = self.split_records(text)

        for idx, block in enumerate(blocks):
            try:
                record = self.parse_record_block(block)
                records.append(record)
            except Exception as exc:
                if not skip_errors:
                    raise
                print(f"[loader] 跳过第 {idx} 条记录，原因: {exc}")

        return records

    def load_records_from_file(
        self,
        file_path: str | Path,
        *,
        encoding: str = "utf-8",
        skip_errors: bool = True,
    ) -> List[PatentJsonRecord]:
        text = self.read_text(file_path, encoding=encoding)
        return self.load_records_from_text(text, skip_errors=skip_errors)

    def load_records_from_dir(
        self,
        data_dir: str | Path,
        pattern: str = "*.txt",
        *,
        encoding: str = "utf-8",
        skip_errors: bool = True,
    ) -> List[PatentJsonRecord]:
        all_records: List[PatentJsonRecord] = []
        data_path = Path(data_dir)

        for file_path in sorted(data_path.glob(pattern)):
            records = self.load_records_from_file(
                file_path=file_path,
                encoding=encoding,
                skip_errors=skip_errors,
            )
            all_records.extend(records)

        return all_records

    # =========
    # JSON 导出
    # =========
    @staticmethod
    def records_to_json(records: List[PatentJsonRecord], *, indent: int = 2) -> str:
        data = [record.model_dump() for record in records]
        return json.dumps(data, ensure_ascii=False, indent=indent)

    @staticmethod
    def save_records_to_json(
        records: List[PatentJsonRecord],
        output_path: str | Path,
        *,
        indent: int = 2,
    ) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            PatentTXTLoader.records_to_json(records, indent=indent),
            encoding="utf-8",
        )

    @staticmethod
    def records_from_json(json_text: str) -> List[PatentJsonRecord]:
        payload = json.loads(json_text)
        if not isinstance(payload, list):
            raise ValueError("JSON 根节点必须是数组（list）。")
        return [PatentJsonRecord.model_validate(item) for item in payload]

    @staticmethod
    def load_records_from_json_file(file_path: str | Path, *, encoding: str = "utf-8") -> List[PatentJsonRecord]:
        path = Path(file_path)
        return PatentTXTLoader.records_from_json(path.read_text(encoding=encoding))

    # =========
    # LangChain Document 转换（兼容旧链路）
    # =========
    @staticmethod
    def build_page_content(record: PatentJsonRecord) -> str:
        parts = [
            f"标题：{record.title}" if record.title else "",
            f"摘要：{record.abstract}" if record.abstract else "",
            f"主权项：{record.claim_1}" if record.claim_1 else "",
            f"申请人：{record.applicant}" if record.applicant else "",
            f"分类号：{' ; '.join(record.classification_codes)}" if record.classification_codes else "",
        ]
        return "\n".join(part for part in parts if part)

    @staticmethod
    def record_to_document(record: PatentJsonRecord) -> Document:
        metadata: Dict[str, Any] = {
            "patent_id": record.patent_id,
            "title": record.title,
            "applicant": record.applicant,
            "publication_date": record.publication_date,
            "classification_codes": record.classification_codes,
        }

        return Document(
            page_content=PatentTXTLoader.build_page_content(record),
            metadata=metadata,
        )

    def records_to_documents(self, records: Iterable[PatentJsonRecord]) -> List[Document]:
        return [self.record_to_document(record) for record in records]

    def load_documents_from_file(
        self,
        file_path: str | Path,
        *,
        encoding: str = "utf-8",
        skip_errors: bool = True,
    ) -> List[Document]:
        records = self.load_records_from_file(
            file_path=file_path,
            encoding=encoding,
            skip_errors=skip_errors,
        )
        return self.records_to_documents(records)

    def load_documents_from_dir(
        self,
        data_dir: str | Path,
        pattern: str = "*.txt",
        *,
        encoding: str = "utf-8",
        skip_errors: bool = True,
    ) -> List[Document]:
        records = self.load_records_from_dir(
            data_dir=data_dir,
            pattern=pattern,
            encoding=encoding,
            skip_errors=skip_errors,
        )
        return self.records_to_documents(records)

    def load_documents_from_json_file(
        self,
        file_path: str | Path,
        *,
        encoding: str = "utf-8",
    ) -> List[Document]:
        records = self.load_records_from_json_file(file_path=file_path, encoding=encoding)
        return self.records_to_documents(records)

    # =========
    # PostgreSQL rows 转换（新主链路）
    # =========
    @staticmethod
    def record_to_patent_row(record: PatentJsonRecord) -> Dict[str, Any]:
        """
        将 PatentJsonRecord 转为 patents 主表的一行。

        建议 PostgreSQL 表字段：
        - patent_id TEXT PRIMARY KEY
        - title TEXT NOT NULL
        - applicant TEXT
        - publication_date DATE NULL
        - abstract TEXT
        - claim_1 TEXT
        - raw_fields JSONB
        """
        return {
            "patent_id": record.patent_id,
            "title": record.title,
            "applicant": record.applicant,
            "publication_date": record.publication_date,
            "abstract": record.abstract,
            "claim_1": record.claim_1,
            "raw_fields": record.raw_fields,
        }

    @staticmethod
    def record_to_code_rows(record: PatentJsonRecord) -> List[Dict[str, Any]]:
        """
        将分类号拆成 patent_codes 子表的多行。

        当前分类号主要来自 CLC，所以 code_type 固定写为 CLC。
        将来数据源升级后，再扩展 IPC / CPC。
        """
        rows: List[Dict[str, Any]] = []
        for code in record.classification_codes:
            rows.append(
                {
                    "patent_id": record.patent_id,
                    "code_type": "CLC",
                    "code": code,
                }
            )
        return rows

    @staticmethod
    def record_to_chunk_rows(record: PatentJsonRecord, *, include_title: bool = False) -> List[Dict[str, Any]]:
        """
        将一条专利转换为 patent_chunks 检索单元。

        当前现实数据下：
        - 必然可用的高价值 section 主要是 abstract / claim1
        - 可选地把 title 也作为弱检索信号落库

        建议 PostgreSQL 表字段：
        - chunk_id TEXT PRIMARY KEY
        - patent_id TEXT NOT NULL
        - section TEXT NOT NULL
        - chunk_index INT NOT NULL
        - text TEXT NOT NULL
        - embedding VECTOR(384) NULL
        """
        rows: List[Dict[str, Any]] = []

        if include_title and record.title:
            rows.append(
                {
                    "chunk_id": f"{record.patent_id}_title_0",
                    "patent_id": record.patent_id,
                    "section": "title",
                    "chunk_index": 0,
                    "text": record.title,
                }
            )

        if record.abstract:
            rows.append(
                {
                    "chunk_id": f"{record.patent_id}_abstract_0",
                    "patent_id": record.patent_id,
                    "section": "abstract",
                    "chunk_index": 0,
                    "text": record.abstract,
                }
            )

        if record.claim_1:
            rows.append(
                {
                    "chunk_id": f"{record.patent_id}_claim1_0",
                    "patent_id": record.patent_id,
                    "section": "claim1",
                    "chunk_index": 0,
                    "text": record.claim_1,
                }
            )

        return rows

    def records_to_postgres_rows(
        self,
        records: Iterable[PatentJsonRecord],
        *,
        include_title_chunk: bool = False,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量转换为 PostgreSQL 入库所需的三类 rows：
        - patents
        - patent_codes
        - patent_chunks
        """
        patent_rows: List[Dict[str, Any]] = []
        code_rows: List[Dict[str, Any]] = []
        chunk_rows: List[Dict[str, Any]] = []

        for record in records:
            patent_rows.append(self.record_to_patent_row(record))
            code_rows.extend(self.record_to_code_rows(record))
            chunk_rows.extend(self.record_to_chunk_rows(record, include_title=include_title_chunk))

        return {
            "patents": patent_rows,
            "patent_codes": code_rows,
            "patent_chunks": chunk_rows,
        }

    def load_postgres_rows_from_file(
        self,
        file_path: str | Path,
        *,
        encoding: str = "utf-8",
        skip_errors: bool = True,
        include_title_chunk: bool = False,
    ) -> Dict[str, List[Dict[str, Any]]]:
        records = self.load_records_from_file(
            file_path=file_path,
            encoding=encoding,
            skip_errors=skip_errors,
        )
        return self.records_to_postgres_rows(records, include_title_chunk=include_title_chunk)

    def load_postgres_rows_from_dir(
        self,
        data_dir: str | Path,
        pattern: str = "*.txt",
        *,
        encoding: str = "utf-8",
        skip_errors: bool = True,
        include_title_chunk: bool = False,
    ) -> Dict[str, List[Dict[str, Any]]]:
        records = self.load_records_from_dir(
            data_dir=data_dir,
            pattern=pattern,
            encoding=encoding,
            skip_errors=skip_errors,
        )
        return self.records_to_postgres_rows(records, include_title_chunk=include_title_chunk)

    # =========
    # 工具函数
    # =========
    @staticmethod
    def _clean_text(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{2,}", "\n", value)
        return value.strip()

    @staticmethod
    def _split_codes(value: Optional[str]) -> List[str]:
        cleaned = PatentTXTLoader._clean_text(value)
        if not cleaned:
            return []
        parts = re.split(r"[;；]+", cleaned)
        return [part.strip() for part in parts if part.strip()]


# =========
# 便捷函数
# =========
def load_patent_records_from_dir(data_dir: str | Path) -> List[PatentJsonRecord]:
    loader = PatentTXTLoader()
    return loader.load_records_from_dir(data_dir)


def load_patent_documents_from_dir(data_dir: str | Path) -> List[Document]:
    loader = PatentTXTLoader()
    return loader.load_documents_from_dir(data_dir)


def load_patent_postgres_rows_from_dir(
    data_dir: str | Path,
    *,
    include_title_chunk: bool = False,
) -> Dict[str, List[Dict[str, Any]]]:
    loader = PatentTXTLoader()
    return loader.load_postgres_rows_from_dir(data_dir, include_title_chunk=include_title_chunk)


# =========
# CLI
# =========
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CNKI 专利 txt/json 加载与转换工具")
    parser.add_argument("--input-dir", default="data", help="txt 输入目录，默认 data")
    parser.add_argument("--pattern", default="*.txt", help="txt 匹配模式，默认 *.txt")
    parser.add_argument("--encoding", default="utf-8", help="输入文件编码，默认 utf-8")
    parser.add_argument(
        "--output-json",
        default="data/patents.json",
        help="json 输出路径；为空字符串则不导出（默认 data/patents.json）",
    )
    parser.add_argument("--input-json", default=None, help="若提供，则直接从 json 读取记录")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：遇到解析错误立即抛出（默认跳过错误）",
    )
    parser.add_argument(
        "--print-postgres-rows",
        action="store_true",
        help="打印 PostgreSQL rows 统计信息",
    )
    parser.add_argument(
        "--include-title-chunk",
        action="store_true",
        help="将 title 也作为检索 chunk 输出",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    loader = PatentTXTLoader()
    skip_errors = not args.strict

    if args.input_json:
        records = loader.load_records_from_json_file(args.input_json, encoding=args.encoding)
        source = f"json={args.input_json}"
    else:
        records = loader.load_records_from_dir(
            data_dir=args.input_dir,
            pattern=args.pattern,
            encoding=args.encoding,
            skip_errors=skip_errors,
        )
        source = f"txt_dir={args.input_dir}, pattern={args.pattern}"
        if args.output_json:
            loader.save_records_to_json(records, args.output_json)
            print(f"[loader] 已导出 JSON: {args.output_json}")

    documents = loader.records_to_documents(records)

    print(f"[loader] 数据来源: {source}")
    print(f"[loader] records 数量: {len(records)}")
    print(f"[loader] documents 数量: {len(documents)}")
    if records:
        print(f"[loader] 首条专利ID: {records[0].patent_id}")

    if args.print_postgres_rows:
        rows = loader.records_to_postgres_rows(records, include_title_chunk=args.include_title_chunk)
        print(f"[loader] patents rows: {len(rows['patents'])}")
        print(f"[loader] patent_codes rows: {len(rows['patent_codes'])}")
        print(f"[loader] patent_chunks rows: {len(rows['patent_chunks'])}")
        if rows["patents"]:
            print("[loader] 示例 patents row:")
            print(json.dumps(rows["patents"][0], ensure_ascii=False, indent=2))
        if rows["patent_codes"]:
            print("[loader] 示例 patent_codes row:")
            print(json.dumps(rows["patent_codes"][0], ensure_ascii=False, indent=2))
        if rows["patent_chunks"]:
            print("[loader] 示例 patent_chunks row:")
            print(json.dumps(rows["patent_chunks"][0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
