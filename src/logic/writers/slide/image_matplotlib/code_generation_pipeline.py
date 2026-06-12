from textwrap import dedent

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.logic import build_standard_chat_prompt_template


class MatplotlibCodeResponse(BaseModel):
    """Pydantic model for structured matplotlib code finetuning response."""

    code: str = Field(description="The complete Python matplotlib code")


MATPLOTLIB_SYSTEM_PROMPT = dedent("""
You are an expert Python visualization engineer specializing in precise scientific and educational matplotlib graphics.

Generate Python code from:

<PROMPT>: the image description.

# Core Requirements

- Output ONLY valid Python code.
- Code must run as-is with all required imports.
- Save the figure as:
  plt.savefig("output.png", dpi=200, bbox_inches="tight")

- Include:
  import matplotlib
  matplotlib.use("Agg")

# Visualization Principles

- Prioritize clarity and pedagogy over decoration.
- Keep layouts clean, balanced, and easy to understand.
- Avoid unnecessary visual complexity.
- Prevent overlaps using:
  plt.tight_layout()
  or explicit positioning.

# Scientific Accuracy

- Use precise numerical/statistical computation when needed.
- Prefer scipy.stats or reliable numerical methods over hardcoded approximations.
- Dynamically scale axes based on data ranges.
- Add reasonable plot padding (~5–10%) around content.

# Matplotlib Style Rules

- Always use explicit keyword colors:
  ax.plot(x, y, color="orange")

- Never use named colors as positional arguments.
- Compact style strings like "o-" or "k--" are allowed.

# Artist / Patch Imports

- Do NOT access patch classes from matplotlib.pyplot.
- Patch objects and specialized artists must be imported from their correct modules.

Examples:
  from matplotlib.patches import Arc, Circle, Rectangle, Polygon, Wedge
  from matplotlib.lines import Line2D
  from matplotlib.collections import PatchCollection

- Never use:
  plt.Arc(...)
  plt.Circle(...)
  plt.Rectangle(...)

- Correct usage example:

  from matplotlib.patches import Arc

  arc = Arc(
      (0, 0),
      width=1.0,
      height=1.0,
      theta1=0,
      theta2=90,
      color="black"
  )

  ax.add_patch(arc)

# Axes & Layout

- Prefer object-oriented matplotlib:
  fig, ax = plt.subplots()

- Avoid implicit state-machine usage when possible.
- Keep text inside figure bounds.
- Use equal aspect ratio when geometry accuracy matters:
  ax.set_aspect("equal")

# LaTeX Rules

- ALL math expressions must use raw LaTeX strings:
    r"$\\Delta x$" 
    r"$\\frac{{a}}{{b}}$"

- Never place LaTeX in normal strings.

- For dynamically generated LaTeX:
  - Prefer simple concatenation.
  - Avoid nested formatting or template-style braces.

# LangChain / Template Safety

- Escape literal braces using double braces:
  {{ and }}

- Avoid complex nested brace patterns.
- Prefer plain raw strings whenever possible.
- Avoid f-strings for LaTeX unless absolutely necessary.

# MathText Compatibility

- Use matplotlib mathtext-compatible LaTeX only.
- Avoid unsupported commands unless text.usetex=True.

Unsupported examples:
  \displaystyle
  \text
  \begin
  \end

- Sanitize unsupported commands before rendering:
  latex = latex.replace(r"\displaystyle", "")

# Numerical Robustness

- Avoid hardcoded axis limits unless necessary.
- Compute ranges dynamically from data.
- Add padding around plotted content.
- Ensure annotations remain visible within axes limits.

# Output Quality

- Use appropriate figure sizes.
- Use normalized coordinates for text-heavy layouts when useful.
- Ensure visuals are stable, centered, readable, and mathematically precise.
- Prefer high DPI readability.
- Use antialiasing defaults unless a specific raster effect is required.

# Reliability

- Ensure all imports are included explicitly.
- Do not rely on hidden notebook state.
- Do not omit required modules.
- Avoid deprecated matplotlib APIs.
- Ensure generated code executes successfully in a clean Python environment.
""")


def create_matplotlib_code_pipeline(model):

    output_parser = PydanticOutputParser(pydantic_object=MatplotlibCodeResponse)
    format_instructions = output_parser.get_format_instructions()

    human_template = dedent("""
    <PROMPT>: {prompt}

    Output Format Instruction: {format_instructions}
    """)

    text_prompt_template = {"template": human_template,
                            "input_variables": ["prompt"],
                            "partial_variables": {'format_instructions': format_instructions}}

    input_ = {
        "system": {"template": MATPLOTLIB_SYSTEM_PROMPT},
        "human": [text_prompt_template],
    }

    chat_prompt_template = build_standard_chat_prompt_template(input_)

    pipeline = chat_prompt_template | model | output_parser

    return pipeline

