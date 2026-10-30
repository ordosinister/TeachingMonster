# python -m pip install pywin32
import os
import tempfile
import uuid
from pathlib import Path

import win32com.client
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from src.path.path_definition import get_project_dir

def pptx_to_pdf(pptx_path: str) -> bytes:

    output_dir = os.path.join(get_project_dir(), "data", str(uuid.uuid4()))

    pptx = Path(pptx_path).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not pptx.is_file():
        raise FileNotFoundError(f"找不到 PPTX：{pptx}")

    # pdf_path = out_dir / f"{pptx.stem}.pdf"
    powerpoint = None
    presentation = None

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "temp.pdf"

            powerpoint = win32com.client.DispatchEx(
                "PowerPoint.Application"
            )
            # powerpoint.Visible = 0

            presentation = powerpoint.Presentations.Open(
                str(pptx),
                ReadOnly=True,
                Untitled=False,
                WithWindow=False,
            )

            # 2 = ppFixedFormatTypePDF
            presentation.SaveAs(str(pdf_path), 32)

            if not pdf_path.is_file():
                raise RuntimeError("PowerPoint 未產生 PDF 檔案")

            # return pdf_path
            return pdf_path.read_bytes()
    finally:
        if presentation is not None:
            presentation.Close()

        if powerpoint is not None:
            powerpoint.Quit()


def parse_pptx(pptx_path):
    prs = Presentation(pptx_path)

    output_dir = Path(os.path.join(get_project_dir(), "data", str(uuid.uuid4())))

    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    slides_data = []

    def parse_shapes(shapes, slide_no, elements):
        for shape in shapes:
            item = {
                "shape_id": shape.shape_id,
                "name": shape.name,
                "left": round(shape.left / 914400, 3),
                "top": round(shape.top / 914400, 3),
                "width": round(shape.width / 914400, 3),
                "height": round(shape.height / 914400, 3),
            }

            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                parse_shapes(shape.shapes, slide_no, elements)
                continue

            if shape.has_text_frame and shape.text.strip():
                elements.append({
                    **item,
                    "type": "text",
                    "text": shape.text.strip(),
                })

            elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                image = shape.image
                filename = (
                    f"slide_{slide_no}_shape_{shape.shape_id}."
                    f"{image.ext}"
                )
                (image_dir / filename).write_bytes(image.blob)

                elements.append({
                    **item,
                    "type": "image",
                    "path": str(image_dir / filename),
                    "content_type": image.content_type,
                })

            elif getattr(shape, "has_table", False):
                rows = [
                    [cell.text for cell in row.cells]
                    for row in shape.table.rows
                ]
                elements.append({
                    **item,
                    "type": "table",
                    "rows": rows,
                })

            elif getattr(shape, "has_chart", False):
                chart = shape.chart
                elements.append({
                    **item,
                    "type": "chart",
                    "chart_type": str(chart.chart_type),
                    "series": [
                        {
                            "name": series.name,
                            "values": list(series.values),
                            "categories": [
                                str(c.label)
                                for c in series.category_points
                            ] if series.categories else [],
                        }
                        for series in chart.series
                    ],
                })

    for slide_no, slide in enumerate(prs.slides, start=1):
        elements = []
        parse_shapes(slide.shapes, slide_no, elements)

        slides_data.append({
            "slide_number": slide_no,
            "elements": elements,
        })

    return slides_data, output_dir


if __name__ == "__main__":
    # pdf = pptx_to_pdf(
    #     r"data/Attire for Sales Professionals 241113 updated 3.pptx",
    #     r"data/output",
    # )
    # print(f"轉檔完成：{pdf}")

    pptx_path = r"data/Attire for Sales Professionals 241113 updated 3.pptx"

    parse_pptx(pptx_path)