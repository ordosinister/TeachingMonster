import hashlib
import os

from src.sop.audio import run as run_audio
from src.sop.extractors.pdf import pdf_data_extraction
from src.sop.image import run as run_image
from src.sop.video_gen import run as run_video_gen
from src.path.path_definition import get_project_dir

def main(filename: str, persona: str):

    if filename.endswith("pdf"):
        request_id = hashlib.sha256(filename.encode("utf-8")).hexdigest()
        results, messages = pdf_data_extraction(filename)
    else:
        raise ValueError(f"{filename} format is not supported")

    source_dir = os.path.join(get_project_dir(), "data", request_id)
    if not os.path.isdir(source_dir):
        os.makedirs(source_dir)

    run_audio.main(messages, source_dir, persona)
    # run_image.main(results, source_dir)

    # Temporary Solution
    import io

    import pymupdf
    from PIL import Image

    pdf_doc = pymupdf.open(filename)

    output_dir = os.path.join(source_dir, "image")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for page_number, page in enumerate(pdf_doc, start=1):
        pixmap = page.get_pixmap(dpi=200)
        image_bytes = pixmap.tobytes("jpeg")
        image = Image.open(io.BytesIO(image_bytes))

        width, height = image.size
        new_width = width - (width % 2)
        new_height = height - (height % 2)

        if (width, height) != (new_width, new_height):
            image = image.crop((0, 0, new_width, new_height))

        filename = os.path.join(output_dir, f"slide_{page_number}_image.png")

        image.save(filename, format="PNG")
        # image_str = image_to_base64_opened(image)

    run_video_gen.main(source_dir)


if __name__ == "__main__":

    os.environ['env'] = 'DEV'

    pdf_path = "data/發票報銷工具教學_ITG.pdf"
    persona = "請使用繁體中文。"

    main(filename=pdf_path, persona=persona)