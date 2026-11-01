from typing import Literal, Union

from pydantic import BaseModel, Field


class GeneralImage(BaseModel):
    name: Literal["general"] = "general"
    image_prompt: str = Field(
        description="Natural-language textual description (never code). Use for conceptual, illustrative, or scenario-based visualizations (workflows, process flows, organizational charts, product layouts, business scenarios, conceptual frameworks) that aid understanding and do not require precise numerical data or coordinate-driven plotting.")


class MatplotlibImage(BaseModel):
    name: Literal["matplotlib"] = "matplotlib"
    image_prompt: str = Field(
        description="Natural-language textual description (NEVER Python/matplotlib code). Use for data-driven visuals requiring precise numerical values or exact proportional relationships: bar charts, line charts, pie charts, trend graphs, KPI dashboards, ranking comparisons, and any visualization where wrong numbers would mislead the audience.")


class Output(BaseModel):
    reasoning: str = Field(
        description="Explanation of why an image is unnecessary (e.g., textual sufficiency, pure conceptual logic, or avoiding cognitive overload) or why a specific image type was chosen.")
    image_selection: Union[GeneralImage, MatplotlibImage, None] = Field(
        description="The chosen image type if necessary, otherwise None.")
