"""
txt -> record
record -> LangChain Document
"""
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
    """
    patent_id: str = Field(..., description="由 PubNo-公开号 映射")
    title: str = Field(..., description="由 Title-题名 映射")
    applicant: Optional[str] = Field(default=None, description="申请人")
    publication_date: Optional[str] = Field(default=None, description="公开日期")
    abstract: Optional[str] = Field(default=None, description="摘要")
    claim_1: Optional[str] = Field(default=None, description="主权项/近似独立权利要求1")
    classification_codes: List[str] = Field(default_factory=list, description="原始分类号")
    raw_fields: Dict[str, Any] = Field(default_factory=dict, description="未纳入顶层 schema 的原始字段")


class PatentTXTLoader:
    """
    负责：
    1. 读取 CNKI txt
    2. 拆分专利记录
    3. 解析为 PatentJsonRecord
    4. 转为 LangChain Document
    """

    # 例如：
    # SrcDatabase-来源库: 中国专利
    # PubNo-公开号: CN121713223A
    FIELD_PATTERN = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)-[^:：]+[:：]\s*(.*)$")

    RECORD_START_PREFIX = "SrcDatabase-来源库:"

    def __init__(self) -> None:
        """初始化加载器。

        当前实现无状态，保留构造函数便于后续扩展：
        - 注入日志器
        - 注入字段映射配置
        - 注入数据清洗策略
        """
        pass

    # =========
    # 文件读取
    # =========
    @staticmethod
    def read_text(file_path: str | Path, encoding: str = "utf-8") -> str:
        """读取文本文件。

        Args:
            file_path: 文本文件路径，支持 `str` 与 `Path`。
            encoding: 文件编码，默认 `utf-8`。

        Returns:
            文件完整文本内容。

        Raises:
            FileNotFoundError: 文件不存在。
            UnicodeDecodeError: 编码不匹配。
            OSError: 其他底层 I/O 异常。
        """
        path = Path(file_path)
        return path.read_text(encoding=encoding)

    # =========
    # 记录拆分
    # =========
    def split_records(self, text: str) -> List[str]:
        """
        将整份 txt 文本按专利记录切分为多个块。

        切分规则：
        1. 以 `SrcDatabase-来源库:` 作为新记录起始标记。
        2. 空行保留到当前记录中，交由后续字段拼接阶段处理。
        3. 若文件开头没有起始标记，先按容错逻辑归入第一块。

        Args:
            text: 原始 txt 全文。

        Returns:
            记录块列表，每个元素是一条记录的原始文本。
        """
        if not text.strip():
            return []

        lines = text.splitlines()
        blocks: List[List[str]] = []
        current_block: List[str] = []

        for raw_line in lines:
            line = raw_line.rstrip()

            if not line.strip():
                # 空行保留为记录内部的一部分，交给后续字段拼接处理
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
                    # 容错：如果文件开头不是 SrcDatabase 开头，先归入一个块
                    current_block = [line]

        if current_block:
            blocks.append(current_block)

        # 去掉全空块
        cleaned_blocks = []
        for block in blocks:
            joined = "\n".join(block).strip()
            if joined:
                cleaned_blocks.append(joined)

        return cleaned_blocks

    # =========
    # 单条记录解析
    # =========
    def parse_record_block(self, block_text: str) -> PatentJsonRecord:
        """
        把一条块文本解析成结构化对象。

        解析规则：
        1. 使用 `FIELD_PATTERN` 匹配字段起始行（如 `PubNo-公开号:`）。
        2. 若某行不匹配字段起始，则作为上一个字段的续行拼接。
        3. 空行作为字段内换行保留。
        4. 最终交由 `_normalize_raw_map` 做字段映射与清洗。

        Args:
            block_text: 单条专利记录块文本。

        Returns:
            标准化后的 `PatentJsonRecord`。

        Raises:
            ValueError: 缺少关键字段（如 `PubNo` 或 `Title`）时抛出。
        """
        raw_map: Dict[str, str] = {}
        current_key: Optional[str] = None

        for raw_line in block_text.splitlines():
            line = raw_line.strip()

            if not line:
                # 空行保留为当前字段的一部分
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
                # 非字段起始行，则视为上一个字段的续行
                if current_key:
                    prev = raw_map.get(current_key, "")
                    if prev and not prev.endswith("\n"):
                        raw_map[current_key] = prev + " " + line
                    else:
                        raw_map[current_key] = prev + line

        return self._normalize_raw_map(raw_map)

    def _normalize_raw_map(self, raw_map: Dict[str, str]) -> PatentJsonRecord:
        """
        将原始字段映射到中间 schema。

        顶层字段仅保留当前检索与展示需要的核心字段；
        其余字段放入 `raw_fields`，避免数据丢失，方便后续扩展。

        Args:
            raw_map: 原始字段键值对（字段名来自 CNKI 导出键）。

        Returns:
            标准化后的 `PatentJsonRecord` 对象。

        Raises:
            ValueError: 缺少 `PubNo` 或 `Title` 等关键字段。
        """
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
        """从原始 txt 文本批量加载专利记录。

        Args:
            text: txt 全文内容。
            skip_errors: 是否跳过单条记录解析错误。
                - `True`: 跳过错误并继续处理。
                - `False`: 遇到错误立即抛出。

        Returns:
            成功解析的专利记录列表。
        """
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
        """从单个 txt 文件加载专利记录。

        Args:
            file_path: txt 文件路径。
            encoding: 文本编码，默认 `utf-8`。
            skip_errors: 是否跳过单条记录错误。

        Returns:
            解析后的专利记录列表。
        """
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
        """从目录下多个 txt 文件批量加载专利记录。

        Args:
            data_dir: 数据目录路径。
            pattern: 文件匹配模式，默认 `*.txt`。
            encoding: 文本编码，默认 `utf-8`。
            skip_errors: 是否跳过单条记录错误。

        Returns:
            合并后的全部专利记录列表。
        """
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
        """将记录列表序列化为 JSON 字符串。

        Args:
            records: 专利记录对象列表。
            indent: JSON 缩进空格数。

        Returns:
            JSON 字符串（`ensure_ascii=False`，保留中文）。
        """
        data = [record.model_dump() for record in records]
        return json.dumps(data, ensure_ascii=False, indent=indent)

    @staticmethod
    def save_records_to_json(
        records: List[PatentJsonRecord],
        output_path: str | Path,
        *,
        indent: int = 2,
    ) -> None:
        """将记录列表写入 JSON 文件。

        Args:
            records: 专利记录对象列表。
            output_path: 输出 json 路径。
            indent: JSON 缩进空格数。
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            PatentTXTLoader.records_to_json(records, indent=indent),
            encoding="utf-8",
        )

    @staticmethod
    def records_from_json(json_text: str) -> List[PatentJsonRecord]:
        """从 JSON 字符串反序列化专利记录。

        Args:
            json_text: JSON 字符串，格式应为 `PatentJsonRecord` 数组。

        Returns:
            `PatentJsonRecord` 列表。

        Raises:
            ValueError: JSON 根节点不是列表时抛出。
            pydantic.ValidationError: 单条记录字段不合法时抛出。
        """
        payload = json.loads(json_text)
        if not isinstance(payload, list):
            raise ValueError("JSON 根节点必须是数组（list）。")
        return [PatentJsonRecord.model_validate(item) for item in payload]

    @staticmethod
    def load_records_from_json_file(file_path: str | Path, *, encoding: str = "utf-8") -> List[PatentJsonRecord]:
        """从 JSON 文件加载专利记录。

        Args:
            file_path: JSON 文件路径。
            encoding: 文件编码，默认 `utf-8`。

        Returns:
            `PatentJsonRecord` 列表。
        """
        path = Path(file_path)
        return PatentTXTLoader.records_from_json(path.read_text(encoding=encoding))

    # =========
    # LangChain Document 转换
    # =========
    @staticmethod
    def build_page_content(record: PatentJsonRecord) -> str:
        """构造用于向量检索的文本内容。

        Args:
            record: 单条专利记录。

        Returns:
            合并标题、摘要、主权项、申请人和分类号后的文本。
        """
        parts = [
            f"标题：{record.title}" if record.title else "",
            f"摘要：{record.abstract}" if record.abstract else "",
            f"主权项：{record.claim_1}" if record.claim_1 else "",
            f"申请人：{record.applicant}" if record.applicant else "",
            f"分类号：{' ; '.join(record.classification_codes)}" if record.classification_codes else "",
        ]
        return "\n".join(part for part in parts if part)

    @staticmethod
    def record_to_document(
        record: PatentJsonRecord,
    ) -> Document:
        """将单条专利记录转换为 LangChain `Document`。

        Args:
            record: 单条专利记录。

        Returns:
            LangChain `Document` 对象。
        """
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

    def records_to_documents(
        self,
        records: Iterable[PatentJsonRecord],
    ) -> List[Document]:
        """将多条专利记录批量转换为 `Document`。

        Args:
            records: 专利记录可迭代对象。

        Returns:
            `Document` 列表。
        """
        return [
            self.record_to_document(record)
            for record in records
        ]

    def load_documents_from_file(
        self,
        file_path: str | Path,
        *,
        encoding: str = "utf-8",
        skip_errors: bool = True,
    ) -> List[Document]:
        """从单个 txt 文件直接加载 `Document` 列表。

        Args:
            file_path: txt 文件路径。
            encoding: 文件编码。
            skip_errors: 是否跳过解析错误记录。

        Returns:
            `Document` 列表。
        """
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
        """从目录下多个 txt 文件直接加载 `Document` 列表。

        Args:
            data_dir: 数据目录路径。
            pattern: 文件匹配模式。
            encoding: 文件编码。
            skip_errors: 是否跳过解析错误记录。

        Returns:
            合并后的 `Document` 列表。
        """
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
        """从 JSON 文件直接加载 `Document` 列表。

        这通常用于离线预处理后复用：
        先把 txt 解析成 json，再在后续流程直接读 json，避免重复解析 txt。

        Args:
            file_path: JSON 文件路径。
            encoding: 文件编码。

        Returns:
            `Document` 列表。
        """
        records = self.load_records_from_json_file(file_path=file_path, encoding=encoding)
        return self.records_to_documents(records)

    # =========
    # 工具函数
    # =========
    @staticmethod
    def _clean_text(value: Optional[str]) -> Optional[str]:
        """清洗文本字段。

        规则：
        - 去除首尾空白
        - 多个空格/制表压缩为一个空格
        - 连续多空行压缩为一个换行

        Args:
            value: 原始文本。

        Returns:
            清洗后的文本；若为空则返回 `None`。
        """
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        # 合并多余空白，但保留换行的基本语义
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{2,}", "\n", value)
        return value.strip()

    @staticmethod
    def _split_codes(value: Optional[str]) -> List[str]:
        """拆分分类号字段为列表。

        支持中英文分号（`;`、`；`）分隔。

        Args:
            value: 原始分类号文本。

        Returns:
            去空白后的分类号列表。
        """
        cleaned = PatentTXTLoader._clean_text(value)
        if not cleaned:
            return []
        parts = re.split(r"[;；]+", cleaned)
        return [part.strip() for part in parts if part.strip()]


# =========
# 便捷函数
# =========
def load_patent_records_from_dir(data_dir: str | Path) -> List[PatentJsonRecord]:
    """便捷函数：从目录读取并解析专利记录。"""
    loader = PatentTXTLoader()
    return loader.load_records_from_dir(data_dir)


def load_patent_documents_from_dir(data_dir: str | Path) -> List[Document]:
    """便捷函数：从目录读取并转换为 LangChain `Document`。"""
    loader = PatentTXTLoader()
    return loader.load_documents_from_dir(data_dir)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    运行方式示例：
    - 从 txt 解析并导出 json：
      `python -m backend.app.rag.loader --input-dir data --output-json data/patents.json`
    - 直接从 json 读取并转 document：
      `python -m backend.app.rag.loader --input-json data/patents.json`
    """
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
    return parser.parse_args()


def main() -> None:
    """命令行入口。

    默认行为：
    1. 从 `data/*.txt` 读取并解析记录
    2. 导出到 `data/patents.json`
    3. 转换为 `Document` 并打印统计信息

    若传入 `--input-json`，则跳过 txt 解析，直接读取 json 复用。
    """
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

if __name__ == "__main__":
    main()