"""Docling PDF 解析模組。"""
from __future__ import annotations

import logging
from typing import Any

try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import ConversionResult
    from docling.document_converter import DocumentConverter
    HAS_DOCLING = True
except Exception:
    HAS_DOCLING = False

from extractors.pdf._docling.models import (
    BoundingBox,
    DoclingResult,
    ExtractedImage,
    ExtractedTable,
    PageExtraction,
    TableCell,
)

logger = logging.getLogger(__name__)


def _bbox_from_docling(item: Any) -> BoundingBox | None:
    """嘗試從 _docling 項目提取 bbox。"""
    try:
        if hasattr(item, "prov") and item.prov:
            p = item.prov[0]
            return BoundingBox(
                x0=float(p.bbox.l),
                y0=float(p.bbox.t),
                x1=float(p.bbox.r),
                y1=float(p.bbox.b),
            )
    except Exception:
        pass
    return None


def _to_page_extractions(result: ConversionResult) -> list[PageExtraction]:
    """將 Docling ConversionResult 轉為內部 PageExtraction 列表。"""
    pages: list[PageExtraction] = []
    if not result or not result.document:
        return pages

    doc = result.document
    try:
        import _docling
        docling_version = _docling.__version__
    except Exception:
        docling_version = "unknown"

    page_texts: dict[int, list[str]] = {}
    page_tables: dict[int, list[ExtractedTable]] = {}
    page_images: dict[int, list[ExtractedImage]] = {}

    for item in doc.texts:
        page_no = 0
        try:
            if hasattr(item, "prov") and item.prov:
                page_no = max(0, item.prov[0].page - 1)
        except Exception:
            pass
        text = str(item.text) if hasattr(item, "text") else ""
        page_texts.setdefault(page_no, []).append(text)

    for table in doc.tables:
        page_no = 0
        try:
            if hasattr(table, "prov") and table.prov:
                page_no = max(0, table.prov[0].page - 1)
        except Exception:
            pass
        cells: list[TableCell] = []
        header_rows: list[list[str]] = []
        try:
            grid = table.export_to_dataframe()
            for r_idx, row in grid.iterrows():
                for c_idx, val in enumerate(row):
                    cells.append(TableCell(row=int(r_idx), col=int(c_idx), text=str(val)))
            if len(grid) > 0:
                header_rows.append([str(c) for c in grid.columns])
        except Exception:
            pass
        page_tables.setdefault(page_no, []).append(
            ExtractedTable(
                table_id=f"table_{page_no}_{len(page_tables.get(page_no, []))}",
                page_number=page_no,
                header_rows=header_rows,
                cells=cells,
                bbox=_bbox_from_docling(table),
                row_count=len(cells) // max(len(header_rows[0]) if header_rows else 1, 1),
                col_count=len(header_rows[0]) if header_rows else 0,
            )
        )

    for pic in doc.pictures:
        page_no = 0
        try:
            if hasattr(pic, "prov") and pic.prov:
                page_no = max(0, pic.prov[0].page - 1)
        except Exception:
            pass

        image = pic.get_image(doc)

        if image is not None:
            print("")

        desc = str(pic.caption_text) if hasattr(pic, "caption_text") and pic.caption_text else None
        page_images.setdefault(page_no, []).append(
            ExtractedImage(
                image_id=f"img_{page_no}_{len(page_images.get(page_no, []))}",
                page_number=page_no,
                description=desc,
                bbox=_bbox_from_docling(pic),
            )
        )

    max_page = max(
        list(page_texts.keys()) + list(page_tables.keys()) + list(page_images.keys()) + [0]
    )
    for p in range(max_page + 1):
        pages.append(
            PageExtraction(
                page_number=p,
                page_number_1_indexed=p + 1,
                text="\n".join(page_texts.get(p, [])),
                tables=page_tables.get(p, []),
                images=page_images.get(p, []),
            )
        )

    return pages


class DoclingParser:
    """使用 Docling 解析 PDF，輸出標準化結果。"""

    def __init__(self) -> None:
        if not HAS_DOCLING:
            raise RuntimeError("_docling is not installed")
        self.converter = DocumentConverter()

    def parse(self, pdf_path: str) -> DoclingResult:
        """解析 PDF 並回傳標準化結果。"""
        result = self.converter.convert(pdf_path)
        pages = _to_page_extractions(result)
        full_text = "\n\n".join(p.text for p in pages)

        docling_version = "unknown"
        if getattr(result, "version"):
            docling_version = result.version.docling_version

        return DoclingResult(
            docling_version=docling_version,
            pages=pages,
            full_text=full_text,
            metadata={"source": pdf_path, "pages_count": len(pages)},
        )

if __name__ == "__main__":

    import os

    from path.path_definition import get_project_dir


    docling_parser = DoclingParser()

    pdf_path = os.path.join(get_project_dir(), "data", "5-3-2 Apply New Samples at EIP - Sample Request 240902 1.pdf")

    docling_parser.parse(pdf_path=pdf_path)