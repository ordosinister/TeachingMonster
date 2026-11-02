from textwrap import dedent

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.logic.writers.image.image_matplotlib.code_generation_pipeline import create_matplotlib_code_pipeline

class Inputs(BaseModel):
    user_query: str = Field(description="The image prompt")


class MathPlotlibTool(BaseTool):

    input_output_parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Inputs)
    input_format_instructions: str = input_output_parser.get_format_instructions()

    name: str = "Matplotlib_Code_Tool"
    description_template: str = dedent("""\
        Use this tool to create code for matplotlib plots.
        input format: {input_format_instructions}
        """)

    description: str = description_template.format(input_format_instructions=input_format_instructions)

    pipeline: Runnable

    @classmethod
    def create(cls, llm):

        return cls(pipeline=create_matplotlib_code_pipeline(model=llm))

    def _run(self, runtime: ToolRuntime, **input):
        print(f"Running {self.name}...")
        args = input.get("input", input)
        query = args['user_query']

        code = self.pipeline.invoke({"prompt": query})

        return code

    async def _arun(self, runtime: ToolRuntime, **input):
        print(f"Running {self.name}...")
        args = input.get("input", input)
        if 'user_query' in args:
            query = args['user_query']
        else:
            query = input['user_query']

        code = await self.pipeline.ainvoke({"prompt": query})

        return code