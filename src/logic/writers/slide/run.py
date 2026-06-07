"""Slide image generation: renders educational slides from adapted blueprints.

Uses gpt-image-2 (OpenAI) with a layout template to generate high-quality
PNG slide images. Supports text-only, diagram, and mixed layouts with
concurrent processing (up to 4 slides at once).
"""

"""Slide image generation: renders educational slides from adapted blueprints.

Uses gpt-image-2 (OpenAI) with a layout template to generate high-quality
PNG slide images. Supports text-only, diagram, and mixed layouts with
concurrent processing (up to 4 slides at once).
"""

import asyncio
import base64
import json
import os
import logging
from textwrap import dedent
from typing import Optional, List

logger = logging.getLogger("Image Merge")

import aiofiles
from openai import AsyncOpenAI, APIConnectionError
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_core.exceptions import OutputParserException

from src.io.path_definition import get_project_dir
from initialization import credential_init
from src.logic.writers.slide.image_logic.prompt_generation_pipeline import create_image_prompt_pipeline
from src.logic.writers.slide.visual_style.style_generation_pipeline import create_visual_style_pipeline
from src.logic.writers.slide.image_matplotlib.code_generation_pipeline import create_matplotlib_code_pipeline
from src.logic.writers.slide.load_agent import create_plot_agent
from model_orchestration import MODEL_CONFIGURATIONS

credential_init()

client = AsyncOpenAI()

class CodeOutput(BaseModel):
    code: str = Field(description="The python code")


class Context(BaseModel):
    supporting_code: str


async def openai_call(prompt: str, image: List, image_temp: Optional[str]=None):

    env = os.environ["env"]

    if image_temp:
        with open(image_temp, "rb") as f:
            image.append(f)
            while True:
                try:
                    result_edit = await client.images.edit(
                        model="gpt-image-2",
                        image=image,
                        prompt=prompt,
                        quality=MODEL_CONFIGURATIONS[env]['image_quality'],
                    )
                    break
                except APIConnectionError:
                    logger.info(f"API Connection Error, Sleep for 5 seconds")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.info(f"{e}, Sleep for 5 seconds")
                    await asyncio.sleep(5)

    else:
        while True:
            try:
                result_edit = await client.images.edit(
                    model="gpt-image-2",
                    image=image,
                    prompt=prompt,
                    quality=MODEL_CONFIGURATIONS[env]['image_quality'],
                )
                break
            except APIConnectionError:
                logger.info(f"API Connection Error, Sleep for 5 seconds")
                await asyncio.sleep(5)
            except Exception as e:
                logger.info(f"{e}, Sleep for 5 seconds")
                await asyncio.sleep(5)

    return result_edit


async def process_slide_async(slide, image_template_rb, semaphore, env: str, output_filename: str, style_output=None):
    """Generate a single slide image using gpt-image-2.

    Args:
        slide: Slide dict with slide_content, speaker_notes, context, etc.
        image_template_rb: Template image bytes for the background layout.
        semaphore: asyncio.Semaphore for concurrency control.
        env: Environment key ("DEV" or "PROD") for quality settings.
        output_filename: Path to write the generated PNG image.
        style_output: Optional visual style specification.
    """

    async with semaphore:

        image = [image_template_rb]

        slide_content = slide['slide_content']
        slide_title = slide['slide_title']
        speaker_notes = slide['speaker_notes']
        context = slide['context']
        slide_type = slide['slide_type']
        image_temp = f"output{slide['slide_number']}.png"

        logger.info(f"Starting slide {slide['slide_number']} image")

        image_prompt_pipeline = create_image_prompt_pipeline(model=MODEL_CONFIGURATIONS[env]["sub"])

        while True:
            try:
                logger.info(f"Starting slide {slide['slide_number']} image classification")

                output = await image_prompt_pipeline.ainvoke({"slide_content": ",\n".join(slide_content),
                                                              "speaker_notes": speaker_notes,
                                                              "context": context, "slide_type": slide_type,
                                                              "student_persona": slide['student_persona']})

                logger.info(f"Slide {slide['slide_number']} image classification: {output.image_selection}")
                break
            except Exception as e:
                continue

        if not output.image_selection:
            # Case 1: Text-Only Layout - Optimized for clarity and whitespace
            prompt = dedent(f"""\
                            Create a high-quality, minimalist educational slide image using the provided image as the background template.
                            
                            STRICT TEMPLATE RULES:
                            - Use the provided image as the fixed layout and background
                            - Preserve its structure, spacing, and visual hierarchy
                            - Do NOT alter the template design

                            TEXT-CENTRIC LAYOUT (CRITICAL):
                            - This slide is designed to be text-only for maximum pedagogical clarity.
                            - Title (place in the title area exactly):
                            {slide_title}

                            Bullet Points (place in the content area, left-aligned):
                            {chr(10).join([f"{item}" for item in slide_content])}

                            TYPOGRAPHIC REQUIREMENTS:
                            - Ensure the text has significant "breathing room" (whitespace)
                            - Do NOT add any images, icons, or diagrams; the focus is entirely on the textual logic
                            - Maintain a clean, professional, and academic aesthetic
                            - Use high contrast and perfect alignment to ensure readability
                            - Preserve all numbers, equations, and units EXACTLY

                            VISUAL AREA HANDLING:
                            - Leave the designated visual area of the template clean and empty
                            - Do not attempt to fill the visual space with decorations

                            The final result must look like a polished presentation slide where the clarity of the text is the primary focus.
                            """)

            result_edit = await openai_call(prompt, image)

        else:
            # Case 2: Visual Support - Determining type and generating content
            if output.image_selection.name == 'general':
                visual_content = output.image_selection.image_prompt

                logger.info(f"Slide {slide['slide_number']} visual style: {style_output.style_category}")

                visual_instruction = dedent(f"""\
                Generate a supporting educational diagram based on this description:
                {visual_content}

                VISUAL STYLE GUIDANCE:
                - Style category: {style_output.style_category}
                - Rendering approach: {style_output.visual_guidance}
                - Tone: {style_output.tone_descriptor}
                - AVOID: {style_output.anti_patterns}
                - **DO NOT DRAW ANY GRAPH WHICH REQUIRES MATHEMATICAL PRECISION**
                """)
            else:
                matplotlib_code_agent = create_plot_agent(env=env)

                agent_input = {"messages": HumanMessage(content=f"<Context>:\n{context}\n\n<Image_Prompt>:\n{output.image_selection.image_prompt}")}

                agent_result = await matplotlib_code_agent.ainvoke(agent_input)

                last_agent_message = agent_result['messages'][-1].content

                matplotlib_pipeline = create_matplotlib_code_pipeline(model=MODEL_CONFIGURATIONS[env]["main"])

                while True:
                    try:
                        matplotlib_pipeline_output = await matplotlib_pipeline.ainvoke({"prompt": last_agent_message})

                        visual_content = matplotlib_pipeline_output.code

                        visual_content = visual_content.replace("import matplotlib.pyplot as plt", "import matplotlib.pyplot as plt\nimport matplotlib\nmatplotlib.use('Agg')\n")
                        visual_content = visual_content.replace("plt.show()", "plt.close()").replace("output.png", image_temp)
                        visual_content = visual_content.replace("\displaystyle", "")

                        exec(visual_content, {})

                        visual_instruction = "Render a precise mathematical plot with the second image:\n- Prioritize the accuracy of the graph, like copy-paste\n"

                        break

                    except Exception as e:
                        print(f"Slide {slide['slide_number']}: {e}")
                        pass

            prompt = dedent(f"""
                        STRICT TEMPLATE RULES:
                        - Use the provided image as the fixed layout and background
                        - Preserve its structure, spacing, and visual hierarchy
                        - Do NOT alter the template design

                        TEXT PLACEMENT:

                        Title (place in the title area exactly):
                        {slide_title}

                        Bullet Points (place in the content area, left-aligned):
                        {chr(10).join([f"{item}" for item in slide_content])}

                        TEXT REQUIREMENTS (CRITICAL):
                        - Preserve all numbers, equations, and units EXACTLY
                        - Do NOT reword, summarize, or simplify
                        - Ensure high readability and clean alignment
                        - Use consistent bullet spacing
                        - Content must be appropriate for AP-aligned coursework (academically rigorous and precise)

                        VISUAL CONTENT:
                        {visual_instruction}
                        - Place it in the designated visual area of the template
                        - Ensure it does NOT overlap with text
                        - Keep proportions clean and uncluttered

                        LAYOUT RULES:
                        - Maintain clear separation between text and visuals
                        - Do not overcrowd the slide
                        - Adjust diagram scale if needed to fit cleanly

                        STYLE:
                        - Professional educational slide
                        - Clean, minimal, high contrast
                        - No unnecessary decorations
                        - Designed for AP curriculum presentation standards
                        - Color coding rule: Blue is used exclusively for key concepts (important terms and core ideas)
                        - Key formulas appear in a subtle box or highlight -- exam-ready emphasis

                        The final result must look like a polished, academically rigorous AP presentation slide rendered on the provided template.
                        """)

            if not os.path.isfile(image_temp):
                result_edit = await openai_call(prompt, image)
            else:
                result_edit = await openai_call(prompt, image, image_temp)


        image_base64 = result_edit.data[0].b64_json

        if os.path.isfile(image_temp):
            os.remove(image_temp)

        logger.info(f"Exporting slide {slide['slide_number']} image")
        async with aiofiles.open(output_filename, "wb") as fh:
            await fh.write(base64.b64decode(image_base64))


async def process_concurrent(
    script, image_template_rb, output_dir, env: str, max_concurrent=4
) :

    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []

    context = ""

    for slide in script["slides"]:

        slide_number = slide['slide_number']

        context += f"\n===================================\n-Slide number {slide_number}\n\n-Slide content:\n{slide['slide_content']}"

    # Determine visual style based on image prompt + course context
    source_dir = os.path.dirname(output_dir)
    input_json_path = os.path.join(source_dir, "input.json")
    with open(input_json_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    visual_style_pipeline = create_visual_style_pipeline(model=MODEL_CONFIGURATIONS[env]["sub"])

    while True:
        try:
            style_output = await visual_style_pipeline.ainvoke({
                "course_requirement": input_data["course_requirement"],
                "student_persona": input_data["student_persona"],
                "content": context
            })
            break
        except OutputParserException as e:
            logger.info(f"visual style pipeline failed due to {e}")

    logger.info(f"Visual style: {style_output}")

    for slide in script['slides']:
        slide_number = slide['slide_number']
        output_filename = os.path.join(output_dir, f"slide_{slide_number}_image.png")

        slide['context'] = context
        slide['student_persona'] = input_data["student_persona"]

        if not os.path.isfile(output_filename):
            logger.info(f"{output_filename} does not exist, add to pipeline")
            task = process_slide_async(slide, image_template_rb, semaphore, env, output_filename=output_filename, style_output=style_output)
            tasks.append(task)

        # context += f"\n===================================\n-Slide number {slide_number}\n\n-Slide content:\n{slide['slide_content']}"

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


def main(request_id: str):
    """Generate slide images for all slides in the adapted blueprint.

    Reads blueprint_adapted.json (falls back to blueprint.json), applies
    visual style analysis, and renders all slide images concurrently.

    Args:
        request_id: Unique request identifier for file path resolution.
    """

    env = os.environ['env']

    source_dir = os.path.join(get_project_dir(), "data", request_id)

    output_dir = os.path.join(source_dir, "image")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    image_template = os.path.join(get_project_dir(), "layout_template.png")

    filename = os.path.join(source_dir, f"blueprint_adapted.json")
    if os.path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as f:
            script = json.load(f)
    else:
        filename = os.path.join(source_dir, f"blueprint.json")
        with open(filename, "r", encoding="utf-8") as f:
            script = json.load(f)

    image_template_rb = open(image_template, "rb")

    asyncio.run(process_concurrent(script, image_template_rb, output_dir, env, max_concurrent=4))


if __name__ == "__main__":

    os.environ['dev'] = 'DEV'

    main(request_id="celery_2528_1777708473", env="DEV")


