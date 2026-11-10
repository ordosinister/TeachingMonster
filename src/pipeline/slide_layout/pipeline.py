"""Pipeline builders for two-stage slide layout generation."""
from textwrap import dedent

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable

from src.logic import build_standard_chat_prompt_template
from src.pipeline.slide_layout.models import SlideImagePrompt, SlideLayout
from src.pipeline.slide_layout.prompts import IMAGE_PROMPT_SYSTEM_PROMPT, LAYOUT_SYSTEM_PROMPT


def create_image_prompt_pipeline(model) -> Runnable:
    """Stage A: generate image prompt per slide."""
    output_parser = PydanticOutputParser(pydantic_object=SlideImagePrompt)
    format_instructions = output_parser.get_format_instructions()

    input_ = {
        "system": {
            "template": IMAGE_PROMPT_SYSTEM_PROMPT,
            "partial_variables": {"format_instructions": format_instructions},
        },
        "human": {
            "template": dedent("""
                Slide number: {slide_number}
                Slide title: {slide_title}
                Slide content: {slide_content}
                Speaker notes: {speaker_notes}
                Persona: {persona}
                Visual guidance (APPLY STRICTLY): {visual_guidance}
                Anti-patterns (CONVERT TO Negative Prompt): {anti_patterns}
            """),
        },
    }

    pipeline = build_standard_chat_prompt_template(input_) | model | output_parser
    return pipeline


def create_slide_layout_pipeline(model) -> Runnable:
    """Stage B: generate HTML layout per slide (needs image_prompt)."""
    output_parser = PydanticOutputParser(pydantic_object=SlideLayout)
    format_instructions = output_parser.get_format_instructions()

    input_ = {
        "system": {
            "template": LAYOUT_SYSTEM_PROMPT,
            "partial_variables": {"format_instructions": format_instructions},
        },
        "human": {
            "template": dedent("""
                Slide number: {slide_number}
                Slide content: {slide_content}
                Image prompt: {image_prompt}
                Image type: {image_type}
            """),
        },
    }

    pipeline = build_standard_chat_prompt_template(input_) | model | output_parser
    return pipeline