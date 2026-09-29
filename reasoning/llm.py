from langchain_ollama import ChatOllama


llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0
)


def generate_answer(evidence, question):

    prompt = f"""
You are the language-generation component of an evidence-grounded
pharmacy information system.

Your task is to answer the user's medication-information question
using ONLY the supplied evidence.

USER QUESTION:
{question}

SUPPLIED EVIDENCE:
{evidence}

IMPORTANT RULES:

1. Answer the user's actual question directly.

2. Use ONLY information present in the supplied evidence.

3. Do NOT invent medical facts.

4. Do NOT diagnose the user.

5. Do NOT prescribe a medicine.

6. Do NOT provide personalized dosage recommendations.

7. Preserve the distinction between:
   - reported side effects
   - important warnings
   - precautions
   - contraindications

8. If the supplied evidence contains a section, do NOT ignore it.

9. If IMPORTANT WARNINGS evidence exists, include the relevant warning.

10. If IMPORTANT PRECAUTIONS evidence exists, include the relevant
    precautions.

11. If CONTRAINDICATIONS evidence exists, include the contraindication.

12. Do not claim that precautions or contraindications are absent
    when the supplied evidence contains them.

13. Do not describe a reaction as common unless the evidence explicitly
    supports that frequency.

14. If a frequency is not specified, do not invent one.

15. If evidence contains uncertainty or limitations, preserve that
    uncertainty.

16. Do not turn every warning into an emergency recommendation.

17. Keep the answer concise and easy to understand.

18. Do not mention evidence-support scores in the final answer unless
    the user specifically asks about the scoring system.

19. Do not mention the internal RAG, MCP, ChromaDB, argumentation,
    grounding, or LLM process unless the user specifically asks.

20. DO NOT include drug interactions in the final answer.

21. Even if drug interaction evidence is supplied, do not create a
    Drug interactions section and do not mention drug interactions
    in the answer.

OUTPUT FORMAT:

Direct answer:
Give a concise direct answer to the user's question.

Reported side effects:
List the relevant side effects supported by the evidence.

Serious reactions/warnings:
Include important warnings or serious reactions supported by the evidence.

Important precautions:
Include relevant precautions supported by the evidence.

Contraindications:
Include relevant contraindications supported by the evidence.

When to seek medical help:
Include this section ONLY when the supplied evidence clearly supports
a situation where medical attention is needed.

IMPORTANT:
Do not omit a section when corresponding evidence was supplied.

Do not create a section with unsupported information.

Do not include:
- Drug interactions
- Drug interaction warnings
- Drug interaction recommendations

Return ONLY the final medication-information answer.
"""

    response = llm.invoke(prompt)

    return response.content.strip()