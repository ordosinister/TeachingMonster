# from textwrap import dedent
# from langchain.agents import create_agent
# from langchain.agents.middleware.tool_retry import ToolRetryMiddleware
#
# from src.logic.writers.slide.image_matplotlib.agent_tool import MathPlotlibTool
# from src.logic.writers.blueprint.agent.mathematic_coder_v2.agent_tool import MathTool
# from model_orchestration import MODEL_CONFIGURATIONS
#
# AGENT_INSTRUCTION = dedent("""
# # ROLE
# Precise Visualization Architect. Generate high-quality Matplotlib code for educational slides. The final output must contain ONLY concrete numerical values -- no unresolved algebraic terms or symbolic variables.
#
# # INPUT
# <CONTEXT>: Content and data from previous slides. Use this to maintain visual and mathematical consistency (e.g., reusing coordinate scales, colors, variable constants).
# <IMAGE_PROMPT>: The visual requirement for the current slide -- contains plot description, mathematical relationships, and labeling requirements.
#
# # TOOLS
#
# ## Matplotlib_Code_Tool
# Generates initial matplotlib plotting code from an image prompt. Pass the prompt as user_query. Returns executable Python code.
#
# ## Math_verification_tool
# Verifies numerical correctness of matplotlib code. Pass the code to validate. Executes independent verification, returns per-slide corrections tagged # MathTool.
#
# # OPERATING PROCEDURE
# Thought -> Action -> Observation -> Thought ... One action per step.
#
# Run the following sequence:
# 1. Matplotlib_Code_Tool(user_query=<IMAGE_PROMPT>)
# 2. Math_verification_tool(code=result_from_step_1)
# 3. Synthesize final code incorporating all corrections from step 2.
#
# # RULES
# - Final code must contain no symbolic variables in plot commands (local loop iterators excepted).
# - All constants and coefficients must be fully expanded into decimals or integers.
# - Incorporate every correction returned by Math_verification_tool.
# - Before output, verify the code can execute and produces a plot from absolute numbers.
# """)
#
#
# def create_plot_agent(env):
#
#     tools = [MathPlotlibTool.create(llm=MODEL_CONFIGURATIONS[env]['sub']),
#              MathTool.create(llm=MODEL_CONFIGURATIONS[env]['sub'])]
#
#     agent = create_agent(
#         model=MODEL_CONFIGURATIONS[env]['main'],
#         name="Matplotlib_Plot_Generation_Agent",
#         tools=tools,
#         system_prompt=AGENT_INSTRUCTION,
#         middleware=[ToolRetryMiddleware(max_retries=2)]
#     )
#
#     return agent
