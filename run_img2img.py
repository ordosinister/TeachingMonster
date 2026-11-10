import asyncio
import base64
import logging
import os
from pydantic import BaseModel, Field
from typing import List

from openai import AsyncOpenAI, APIConnectionError

from initialization import credential_init
from model_orchestration import get_model_config
from path.path_definition import get_project_dir
from src.logic import build_standard_chat_prompt_template
from src.sop.extractors.pdf import pdf_data_extraction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run img2img prototype")

credential_init()
client = AsyncOpenAI()


async def img2img_process(client, image_file, semaphore):

    QUALITY = "medium"
    PROMPT = "將內容擷取出來，並提升美觀程度"

    async with semaphore:
        while True:
            try:
                result = await client.images.edit(
                    model="gpt-image-2.5-sunburst",
                    image=image_file,
                    prompt=PROMPT,
                    quality=QUALITY,
                    size="1792x1008",
                )
                break
            except APIConnectionError:
                logger.info(f"API Connection Error, Sleep for 5 seconds")
                await asyncio.sleep(5)
            except Exception as e:
                logger.info(f"{e}, Sleep for 5 seconds")
                await asyncio.sleep(5)


        # 4. Base64 -> Binary
        image_base64 = result.data[0].b64_json
        output_bytes = base64.b64decode(image_base64)

        with open(image_file, "wb") as f:
            f.write(output_bytes)


async def process_concurrent(client, image_files, output_dir: str, max_concurrent=4):

    semaphore = asyncio.Semaphore(max_concurrent)

    tasks = []

    for slide_number, image_file in enumerate(image_files,start=1):

        output_filename = os.path.join(output_dir, f"slide_{slide_number}_image.png")

        if not os.path.isfile(output_filename):

            task = img2img_process(client, image_file, semaphore, output_filename)
            tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


def main(request_id: str, cache_key: str):

    env = os.environ['env']

    source_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

    output_dir = os.path.join(source_dir, "image")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    img2img_inputs, messages = pdf_data_extraction(pdf_path)

    client = AsyncOpenAI()

    model = get_model_config(env)["image_caption"]

    SYSTEM_PROMPT = """
    You will receive pdf content as a series of images.
    
    You will create speaker's note for each of the image as content for text to speech.
    
    # Output
    Format instruction: {format_instructions}
    """

    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate, SystemMessagePromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser

    output_parser = PydanticOutputParser(pydantic_object=TTSScripts)
    format_instructions = output_parser.get_format_instructions()

    system_prompt = PromptTemplate(
        template=SYSTEM_PROMPT,
        input_variables=[],
        partial_variables={'format_instructions': format_instructions}
    )

    system_message = SystemMessagePromptTemplate(prompt=system_prompt)

    chat_prompt_template = ChatPromptTemplate.from_messages(
        [system_message, MessagesPlaceholder(variable_name="messages")])

    pipeline = chat_prompt_template | model | output_parser

    tts_output = pipeline.invoke({"messages": messages})

    asyncio.run(process_concurrent(client=client, image_files=img2img_inputs, output_dir=output_dir, max_concurrent=4))


if __name__ == "__main__":

    os.environ['env'] = 'DEV'

    pdf_path = "data/5-3-2 Apply New Samples at EIP - Sample Request 240902 1.pdf"

    # img2img_inputs, messages = pdf_data_extraction(pdf_path)

    main("abc", "123")
