import hashlib
import json
import os
import shutil
import time

from extractors.word.generation_pipeline import create_pipeline
from extractors.word.parser import parse_docx, docx_to_base64_messages

from src.path.path_definition import get_project_dir


def run(docx_path: str):

    env = os.environ["env"]

    pipeline = create_pipeline(env=env)

    start_time = time.time()

    doc_data, output_dir = parse_docx(docx_path)

    word_input = json.dumps(doc_data, ensure_ascii=False)

    output_dir_dump = json.dumps(str(output_dir), ensure_ascii=False)[1:-1]

    word_input = word_input.replace(output_dir_dump, "")

    hash_result = hashlib.sha256(word_input.encode("utf-8")).hexdigest()

    input_dir = os.path.join(get_project_dir(), "data", hash_result)

    if os.path.isdir(input_dir):

        shutil.rmtree(output_dir)

        return hash_result

    messages = docx_to_base64_messages(doc_data)

    response = pipeline.invoke(
        {"messages": messages}
    )

    print(f"Elapsed seconds: {round(time.time() - start_time, 2)}")

    shutil.rmtree(output_dir)

    if not os.path.isdir(input_dir):
        os.makedirs(input_dir)

    input_filename = os.path.join(input_dir, "input.json")

    with open(input_filename, "w", encoding="utf-8") as f:
        json.dump({"course_requirement": response,
                        "reference": docx_path}, f)

    return hash_result


if __name__ == "__main__":

    os.environ["env"] = "DEV"

    request_id= run(docx_path=r"data/sample.docx")

    print(request_id)