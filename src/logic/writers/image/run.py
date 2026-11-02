import asyncio
import base64
import json
import os
import logging
from textwrap import dedent
from typing import Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Image Generation")

import aiofiles
from openai import AsyncOpenAI, APIConnectionError
from pydantic import BaseModel, Field
from langchain_core.exceptions import OutputParserException

from src.path.path_definition import get_project_dir
from initialization import credential_init
from src.logic.writers.image.image_logic.prompt_generation_pipeline import create_image_prompt_pipeline
from src.logic.writers.image.visual_style.style_generation_pipeline import create_visual_style_pipeline
from src.logic.writers.image.image_matplotlib.code_generation_pipeline import create_matplotlib_code_pipeline
from src.logic.writers.image.render_prompt import build_render_prompt
from model_orchestration import get_model_config

credential_init()

class CodeOutput(BaseModel):
    code: str = Field(description="The python code")


class Context(BaseModel):
    supporting_code: str


async def openai_call(client, prompt: str, image: List, image_temp: Optional[str]=None):

    env = os.environ["env"]

    if image_temp:
        with open(image_temp, "rb") as f:
            image.append(f)
            while True:
                try:
                    result_edit = await client.images.edit(
                        model="gpt-image-2.5-flare",
                        image=image,
                        prompt=prompt,
                        quality=get_model_config(env)['image_quality'],
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
                    model="gpt-image-2.5-sunburst",
                    image=image,
                    prompt=prompt,
                    quality=get_model_config(env)['image_quality'],
                )
                break
            except APIConnectionError:
                logger.info(f"API Connection Error, Sleep for 5 seconds")
                await asyncio.sleep(5)
            except Exception as e:
                logger.info(f"{e}, Sleep for 5 seconds")
                await asyncio.sleep(5)

    return result_edit


async def process_slide_async(client, slide, image_template_rb, semaphore, env: str, output_filename: str, style_output=None):
    """Generate a single image image using gpt-image-2.

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
        image_temp = f"output{slide['slide_number']}.png"

        logger.info(f"Starting image {slide['slide_number']} image")

        image_prompt_pipeline = create_image_prompt_pipeline(model=get_model_config(env)["sub"])

        while True:
            try:
                logger.info(f"Starting image {slide['slide_number']} image classification")

                output = await image_prompt_pipeline.ainvoke({"slide_content": ",\n".join(slide_content),
                                                              "speaker_notes": speaker_notes,
                                                              "context": context,
                                                              "student_persona": slide['student_persona']})

                logger.info(f"Slide {slide['slide_number']} image classification: {output.image_selection}")
                break
            except Exception as e:
                continue

        if not output.image_selection:
            # Case 1: Text-Only Layout - Optimized for clarity and whitespace
            prompt = dedent(f"""\
                            Create a high-quality, minimalist educational image image using the provided image as the background template.
                            
                            STRICT TEMPLATE RULES:
                            - Use the provided image as the fixed layout and background
                            - Preserve its structure, spacing, and visual hierarchy
                            - Do NOT alter the template design

                            TEXT-CENTRIC LAYOUT (CRITICAL):
                            - This image is designed to be text-only for maximum pedagogical clarity.
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
                            - IMPORTANT OVERRIDE: $...$ delimiters are LaTeX markup, NOT image content. Strip the $ symbols from the final image entirely. Render only the enclosed expression as properly formatted mathematical notation (italic variables, upright numbers, proper spacing).

                            VISUAL AREA HANDLING:
                            - Leave the designated visual area of the template clean and empty
                            - Do not attempt to fill the visual space with decorations

                            The final result must look like a polished presentation image where the clarity of the text is the primary focus.
                            """)

            result_edit = await openai_call(client, prompt, image)

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
                - **HARD CONSTRAINT -- NO numerical precision**: Do NOT include specific numbers, axis labels with values, data points with exact figures, percentages, rankings, or any precise quantitative measurements. This is a conceptual illustration only. Use qualitative spatial language (e.g., "on the left," "above," "in the center," "near the top"). If the visual requires specific data values, numeric comparisons, trend lines with concrete figures, or proportional charts, it was incorrectly classified and should have been a MatplotlibImage -- flag this as an error.
                """)
            else:

                content = f"<Context>:\n{context}\n\n<Image_Prompt>:\n{output.image_selection.image_prompt}"

                matplotlib_pipeline, output_parser = create_matplotlib_code_pipeline(model=get_model_config(env)["main"])

                while True:
                    try:
                        matplotlib_pipeline_output = await matplotlib_pipeline.ainvoke({"prompt": content})

                        content = matplotlib_pipeline_output.content

                        if content.startswith("```python"):
                            content = content.replace("```python", "```json")

                        visual_content = output_parser.parse(content).code

                        if "matplotlib.use('Agg')" not in visual_content and "matplotlib.use(\"Agg\")" not in visual_content:
                            visual_content = visual_content.replace("import matplotlib.pyplot as plt", "import matplotlib.pyplot as plt\nimport matplotlib\nmatplotlib.use('Agg')\n")
                        visual_content = visual_content.replace("plt.show()", "plt.close()").replace("output.png", image_temp)
                        visual_content = visual_content.replace("\displaystyle", "")

                        exec(visual_content, {"__builtins__": __builtins__})

                        visual_instruction = "Render a precise data visualization with the second image:\n- Prioritize the accuracy of data, labels, and proportions, like a professional business report chart\n"

                        break

                    except Exception as e:
                        print(f"Slide {slide['slide_number']}: {e}")

            prompt = build_render_prompt(slide_title, slide_content, visual_instruction)

            if not os.path.isfile(image_temp):
                result_edit = await openai_call(client, prompt, image)
            else:
                result_edit = await openai_call(client, prompt, image, image_temp)


        image_base64 = result_edit.data[0].b64_json

        if os.path.isfile(image_temp):
            os.remove(image_temp)

        logger.info(f"Exporting image {slide['slide_number']} image")
        async with aiofiles.open(output_filename, "wb") as fh:
            await fh.write(base64.b64decode(image_base64))

        return (slide['slide_number'], output.image_selection.name if output.image_selection else None)


async def process_concurrent(client, script, image_template_rb, output_dir, env: str,
                             max_concurrent=4):

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

    visual_style_pipeline = create_visual_style_pipeline(model=get_model_config(env)["sub"])

    while True:
        try:
            style_output = await visual_style_pipeline.ainvoke({
                "course_requirement": input_data["course_requirement"],
                "student_persona": input_data["persona"],
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
        slide['student_persona'] = input_data["persona"]

        if not os.path.isfile(output_filename):
            logger.info(f"{output_filename} does not exist, add to pipeline")
            task = process_slide_async(client, slide, image_template_rb, semaphore, env,
                                       output_filename=output_filename, style_output=style_output)
            tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results



async def fix_general_images(client, flawed_general_slides, image_template_rb, script, output_dir, max_concurrent=4):
    """Fix flawed general images using images.edit API based on validation feedback.

    Runs concurrently with a semaphore. For each flawed image, reads the existing
    image, calls images.edit with a fix prompt derived from the validation text,
    and overwrites the output file with the corrected result.

    Args:
        client: AsyncOpenAI client.
        flawed_general_slides: List of (slide_number, validation_text, type_name) tuples.
        image_template_rb: Template image bytes for the background layout.
        output_dir: Directory containing image images.
        max_concurrent: Maximum concurrent API calls.

    Returns:
        List of image numbers that were successfully fixed.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fix_one(sn, issue):
        async with semaphore:
            image_path = os.path.join(output_dir, f"slide_{sn}_image.png")
            if not os.path.isfile(image_path):
                logger.warning(f"Slide {sn} image not found, skipping fix")
                return None

            for slide in script['slides']:
                slide_number = slide['slide_number']
                if slide_number == sn:
                    slide_content = chr(10).join([f"{item}" for item in slide['slide_content']])
                    break

            fix_prompt = dedent(f"""\
            Edit this educational diagram to correct the issues described below. The image content is the authoritative reference — every element in the diagram must accurately reflect it.
            
            SLIDE CONTENT (authoritative reference):
            {slide_content}
            
            ISSUES TO CORRECT (described by a quality reviewer):
            {issue}

            EDITING RULES:
            - Make only the minimal edits needed to resolve each issue listed above.
            - Do NOT alter any correct elements: preserve all accurate labels, equations, data points, colors, layout, fonts, and visual styling exactly as they appear.
            - When an issue describes something incorrect or misaligned, adjust that specific element to match the image content.
            - When an issue describes something missing, add only what the image content specifies — do not introduce extra elements.
            - Maintain the same overall composition, diagram type, and visual identity.
            """)

            image = [image_template_rb]

            logger.info(f"Fixing general image for image {sn}")
            result_edit = await openai_call(client, fix_prompt, image, image_temp=image_path)

            image_base64 = result_edit.data[0].b64_json
            async with aiofiles.open(image_path, "wb") as fh:
                await fh.write(base64.b64decode(image_base64))

            temp_file = f"output{sn}.png"
            if os.path.isfile(temp_file):
                os.remove(temp_file)

            logger.info(f"Slide {sn} general image fixed")
            return sn

    tasks = [fix_one(sn, text) for sn, text, _ in flawed_general_slides]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if r is not None and not isinstance(r, Exception)]


def main(request_id: str, cache_key: str):
    """Generate image images for all slides in the adapted blueprint.

    Reads blueprint_adapted.json (falls back to blueprint.json), applies
    visual style analysis, and renders all image images concurrently.

    Args:
        request_id: Unique request identifier for file path resolution.
        cache_key:
        persona
    """

    env = os.environ['env']

    source_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

    output_dir = os.path.join(source_dir, "image")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    image_template = os.path.join(get_project_dir(), "layout_template_itg.png")

    filename = os.path.join(source_dir, f"blueprint_adapted.json")
    if os.path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as f:
            script = json.load(f)
    else:
        filename = os.path.join(source_dir, f"blueprint.json")
        with open(filename, "r", encoding="utf-8") as f:
            script = json.load(f)

    client = AsyncOpenAI()

    with open(image_template, "rb") as image_template_rb:

        max_retries = 3
        retry_count = 0
        image_types = asyncio.run(process_concurrent(client, script, image_template_rb,
                                                     output_dir, env, max_concurrent=4))

if __name__ == "__main__":

    os.environ['env'] = 'DEV'

    main(request_id="01aa1889f2d4c3e75f4c6013db743e09b4edaca190cc45fe98270d81afb08331",
         cache_key="a97294bb5efc6db3")







