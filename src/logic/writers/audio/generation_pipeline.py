from textwrap import dedent

from langchain_core.messages import SystemMessage
from langchain_core.prompts import PromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

from src.logic.writers.audio import SYSTEM_PROMPT


def create_presentation_pipeline(model) -> Runnable:

     system_message = SystemMessage(content=SYSTEM_PROMPT)
     human_prompt = PromptTemplate(template=dedent("""
     <COURSE_REQUIREMENT>: {course_requirement}
     <PERSONA>: {student_persona}
     """),
     input_variables=["course_requirement", "student_persona"]
     )

     human_message = HumanMessagePromptTemplate(prompt=human_prompt)

     chat_prompt = ChatPromptTemplate.from_messages([system_message,
     human_message
     ])

     pipeline = chat_prompt | model | StrOutputParser()

     return pipeline


if __name__ == "__main__":

 from model_orchestration import MODEL_CONFIGURATIONS

 model = MODEL_CONFIGURATIONS["DEV"]["classifier"]

 pipeline = create_presentation_pipeline(model)

 course_requirement = dedent("""
 Topic: Customer Complaint Handling Procedure
 Learning Goal: Guide staff to identify complaint types, apply the appropriate escalation protocol, and document resolution steps
 Key Learning Points: Active listening techniques, escalation matrix, documentation requirements, follow-up timeline
 """)

 student_persona = dedent("""
 Region: Vietnam
 Language Ability: Intermediate English, native Vietnamese
 Business/Technical Background: Frontline customer service staff, 6 months tenure, familiar with basic CRM but new to escalation protocols
 """)

 output = pipeline.invoke({"course_requirement": course_requirement, "student_persona": student_persona})

 print("")