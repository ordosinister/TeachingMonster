import hashlib
import os

from src.sop.audio import run as run_audio
from src.sop.extractors.pdf import pdf_data_extraction
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

    run_audio.main(messages, source_dir, persona, pdf_filename=filename)
    run_video_gen.main(source_dir)


if __name__ == "__main__":

    os.environ['env'] = 'DEV'

    pdf_path = "data/發票報銷工具教學_ITG.pdf"
    persona = "請使用繁體中文。"

    main(filename=pdf_path, persona=persona)