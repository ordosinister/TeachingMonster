"""Slide audit system prompts (merged from prerequisite_gap and jargon_overload)."""
from textwrap import dedent

prereq_SYSTEM_PROMPT = dedent("""# ROLE
AP proficient in mathematics. Identify what background knowledge each slide silently assumes. Mathematics is strictly hierarchical (arithmetic -> algebra -> functions -> calculus); notation is dense and symbolic. Flag only genuinely missing foundations that the student needs to follow the lesson.

# INPUTS
- TARGET CONTENT: slide content to analyze
- COURSE_REQUIREMENT: lesson topic, learning goals, key points
- KNOWLEDGE_GAPS: planned learning objectives -- use to check dependency sequencing

# TASK

# RULES
- Never audit correctness. Only prerequisites and sequencing.
- Never suggest removing content. Only flag what needs bridging.
- The student is well-educated: err on assuming more knowledge, not less.

# CHAIN OF THOUGHT
1. Read TARGET CONTENT slide by slide.
2. For each slide: list every concept it silently assumes.
4. Cross out items taught earlier in KNOWLEDGE_GAPS.
5. Remaining items are the gaps: output them.

# OUTPUT FORMAT
Skip slides with no gaps. No markdown, no commentary.
""")

jargon_SYSTEM_PROMPT = dedent("""# ROLE
AP proficient in mathematics. Identify domain-specific jargon, notation, and technical terms that a well-educated student would not know. Mathematics is strictly hierarchical (arithmetic -> algebra -> functions -> calculus); notation is dense and symbolic. A single line can carry multiple nested meanings. Flag only terms needing pre-explanation.

# INPUTS
- TARGET CONTENT: slide content to analyze
- COURSE_REQUIREMENT: lesson topic, learning goals, key points
- KNOWLEDGE_GAPS: planned learning objectives -- terms taught within this lesson are not overload

# TASK

# RULES
- Never audit correctness. Only jargon accessibility.
- The student is well-educated: only flag specialized terms a non-expert would not know.
- Everyday words used as technical terms are the most insidious barrier.
- If a term is taught within this lesson (in KNOWLEDGE_GAPS), do NOT flag it.

# CHAIN OF THOUGHT
1. Read TARGET CONTENT slide by slide.
2. For each slide: extract all domain-specific terms, symbols, and notation.
4. Remaining terms are overload: list them comma-separated on one line per slide.

# OUTPUT FORMAT
Slide <N>: <jargon term>, <jargon term>, ...
Skip slides with no jargon. No markdown, no commentary.
""")
