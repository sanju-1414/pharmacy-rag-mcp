# ------------------------------------------------
# PHARMACY RAG + MCP PIPELINE
# ------------------------------------------------

from rag.retrieve import (
    retrieve_documents,
    check_rag_sufficiency,
    detect_medicine
)

from mcp_server.router import (
    detect_medicine_for_mcp,
    call_mcp
)

from reasoning.argumentation import (
    run_argumentation
)

from reasoning.safety import (
    run_safety_checks,
    summarize_safety
)

from reasoning.llm import (
    generate_answer
)

from reasoning.xai import (
    generate_xai_explanation
)


# ------------------------------------------------
# DETECT MEDICINE FROM RAG
# ------------------------------------------------

def detect_medicine_from_rag(query):

    try:

        medicine = detect_medicine(
            query
        )

        return medicine

    except Exception:

        return None


# ------------------------------------------------
# BUILD RAG ARGUMENTATION PAYLOAD
# ------------------------------------------------

def build_rag_argumentation_payload(
    rag_results
):

    return {
        "rag_results": rag_results
    }


# ------------------------------------------------
# CONVERT EVIDENCE TO TEXT FOR LLAMA
# ------------------------------------------------

def evidence_to_text(
    argumentation_result
):

    if not argumentation_result:
        return ""

    supported = argumentation_result.get(
        "supported",
        []
    )

    qualified = argumentation_result.get(
        "qualified",
        []
    )

    results = supported + qualified

    if not results:
        return ""

    lines = []

    # ------------------------------------------------
    # Evidence categories
    # ------------------------------------------------

    side_effects = []

    warnings = []

    precautions = []

    contraindications = []

    rag_evidence = []

    # ------------------------------------------------
    # Collect evidence
    # ------------------------------------------------

    for result in results:

        items = result.get(
            "items",
            []
        )

        if not items:
            continue

        for item in items:

            section = item.get(
                "section",
                ""
            ).lower()

            source = item.get(
                "source",
                ""
            ).upper()

            # ------------------------------------------------
            # RAG evidence
            #
            # RAG items currently use:
            # section = retrieved_document
            # source = RAG
            # ------------------------------------------------

            if source == "RAG":

                rag_evidence.append(
                    (result, item)
                )

            # ------------------------------------------------
            # MCP evidence
            # ------------------------------------------------

            elif section == "side_effects":

                side_effects.append(
                    (result, item)
                )

            elif section == "warnings":

                warnings.append(
                    (result, item)
                )

            elif section == "precautions":

                precautions.append(
                    (result, item)
                )

            elif section == "contraindications":

                contraindications.append(
                    (result, item)
                )

    # ------------------------------------------------
    # ADD SECTION
    # ------------------------------------------------

    def add_section(
        title,
        evidence_items,
        limit=5
    ):

        if not evidence_items:
            return

        lines.append(
            f"=== {title} ==="
        )

        for result, item in evidence_items[:limit]:

            score = result.get(
                "score",
                0.0
            )

            effect = item.get(
                "effect",
                "unspecified"
            )

            source = item.get(
                "source",
                "unknown"
            )

            section = item.get(
                "section",
                "unknown"
            )

            text = item.get(
                "text",
                ""
            )

            frequency = item.get(
                "frequency",
                "not specified"
            )

            lines.append(
                f"""
Category:
{effect}

Evidence-support score:
{score}%

Source:
{source}

Section:
{section}

Frequency:
{frequency}

Evidence:
{text}
""".strip()
            )

    # ------------------------------------------------
    # RAG EVIDENCE
    # ------------------------------------------------

    add_section(
        "RETRIEVED RAG EVIDENCE",
        rag_evidence,
        limit=8
    )

    # ------------------------------------------------
    # MCP SIDE EFFECTS
    # ------------------------------------------------

    add_section(
        "REPORTED SIDE EFFECTS",
        side_effects,
        limit=8
    )

    # ------------------------------------------------
    # MCP WARNINGS
    # ------------------------------------------------

    add_section(
        "IMPORTANT WARNINGS",
        warnings,
        limit=4
    )

    # ------------------------------------------------
    # MCP PRECAUTIONS
    # ------------------------------------------------

    add_section(
        "IMPORTANT PRECAUTIONS",
        precautions,
        limit=3
    )

    # ------------------------------------------------
    # MCP CONTRAINDICATIONS
    # ------------------------------------------------

    add_section(
        "CONTRAINDICATIONS",
        contraindications,
        limit=2
    )

    # ------------------------------------------------
    # IMPORTANT:
    # Drug interactions are intentionally NOT passed
    # to Llama.
    # ------------------------------------------------

    return "\n\n".join(
        lines
    )


# ------------------------------------------------
# PREPARE EVIDENCE FOR LLAMA
# ------------------------------------------------

def prepare_llama_evidence(
    argumentation_result
):

    return evidence_to_text(
        argumentation_result
    )


# ------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------

def run_pipeline(
    question
):

    # ------------------------------------------------
    # INITIAL VALUES
    # ------------------------------------------------

    route = None

    medicine = None

    rxcui = None

    tools_used = []

    rag_results = []

    argumentation_result = None

    safety_result = None

    answer = ""

    xai = ""

    # ------------------------------------------------
    # STEP 1 — RAG SEARCH
    # ------------------------------------------------

    try:

        rag_results = retrieve_documents(
            question,
            k=5
        )

    except Exception:

        rag_results = []

    # ------------------------------------------------
    # STEP 2 — CHECK RAG SUFFICIENCY
    # ------------------------------------------------

    try:

        rag_sufficient = check_rag_sufficiency(
            rag_results,
            question
        )

    except Exception:

        rag_sufficient = False

    # ------------------------------------------------
    # STEP 3 — DETECT MEDICINE FROM RAG
    # ------------------------------------------------

    try:

        medicine = detect_medicine_from_rag(
            question
        )

    except Exception:

        medicine = None

    # ------------------------------------------------
    # STEP 4 — RAG ROUTE
    # ------------------------------------------------

    if rag_sufficient and medicine:

        route = "RAG"

        tools_used = [
            "ChromaDB"
        ]

        payload = build_rag_argumentation_payload(
            rag_results
        )

    # ------------------------------------------------
    # STEP 5 — MCP FALLBACK
    # ------------------------------------------------

    else:

        route = "MCP"

        # ------------------------------------------------
        # Detect medicine dynamically through RxNorm
        # ------------------------------------------------

        try:

            medicine_info = detect_medicine_for_mcp(
                question
            )

        except Exception:

            medicine_info = None

        # ------------------------------------------------
        # Invalid medicine / unrelated question
        # ------------------------------------------------

        if not medicine_info:

            return {
                "route": "NONE",

                "medicine": None,

                "rxcui": None,

                "tools_used": [],

                "rag_results": rag_results,

                "argumentation": None,

                "evidence": "",

                "safety": None,

                "answer": (
                    "I could not identify a valid medicine "
                    "related to your question from the available "
                    "knowledge sources."
                ),

                "xai": (
                    "The system could not identify a valid "
                    "medicine, so no medication evidence was "
                    "accepted."
                ),

                "decision": "REJECT"
            }

        # ------------------------------------------------
        # Read medicine information
        # ------------------------------------------------

        if isinstance(
            medicine_info,
            dict
        ):

            medicine = medicine_info.get(
                "medicine"
            )

            rxcui = medicine_info.get(
                "rxcui"
            )

        else:

            medicine = str(
                medicine_info
            )

        # ------------------------------------------------
        # Validate medicine
        # ------------------------------------------------

        if not medicine:

            return {
                "route": "NONE",

                "medicine": None,

                "rxcui": None,

                "tools_used": [],

                "rag_results": rag_results,

                "argumentation": None,

                "evidence": "",

                "safety": None,

                "answer": (
                    "I could not identify a valid medicine "
                    "for this question."
                ),

                "xai": (
                    "Medicine identification failed. "
                    "No external medicine evidence was accepted."
                ),

                "decision": "REJECT"
            }

        # ------------------------------------------------
        # STEP 6 — CALL MCP
        # ------------------------------------------------

        try:

            mcp_payload = call_mcp(
                medicine
            )

        except Exception as e:

            return {
                "route": "MCP",

                "medicine": medicine,

                "rxcui": rxcui,

                "tools_used": [],

                "rag_results": rag_results,

                "argumentation": None,

                "evidence": "",

                "safety": None,

                "answer": (
                    "The external medicine information "
                    "sources could not be accessed."
                ),

                "xai": (
                    f"MCP retrieval failed: {str(e)}"
                ),

                "decision": "REJECT"
            }

        # ------------------------------------------------
        # TOOLS USED
        # ------------------------------------------------

        tools_used = [
            "RxNorm",
            "openFDA",
            "MedlinePlus"
        ]

        payload = mcp_payload

    # ------------------------------------------------
    # STEP 7 — ARGUMENTATION + GROUNDING
    # ------------------------------------------------

    argumentation_result = run_argumentation(
        question,
        medicine,
        payload
    )

    # ------------------------------------------------
    # GET ARGUMENTATION DECISION
    # ------------------------------------------------

    argumentation_decision = argumentation_result.get(
        "decision",
        "QUALIFY"
    )

    # ------------------------------------------------
    # STEP 8 — SAFETY CHECK
    # ------------------------------------------------

    try:

        safety_flags = run_safety_checks(
            question,
            argumentation_result
        )

        safety_summary = summarize_safety(
            safety_flags
        )

        if isinstance(
            safety_summary,
            dict
        ):

            safety_result = safety_summary

        else:

            safety_result = {
                "summary": str(
                    safety_summary
                ),
                "flags": safety_flags
            }

    except Exception:

        safety_result = {
            "summary": (
                "No user-specific safety flag detected."
            ),
            "flags": []
        }

    # ------------------------------------------------
    # STEP 9 — PREPARE GROUNDED EVIDENCE
    # ------------------------------------------------

    grounded_evidence = prepare_llama_evidence(
        argumentation_result
    )

    # ------------------------------------------------
    # STEP 10 — GENERATE LLAMA ANSWER
    # ------------------------------------------------

    if grounded_evidence:

        try:

            answer = generate_answer(
                grounded_evidence,
                question
            )

        except Exception:

            answer = (
                "The evidence was retrieved successfully, "
                "but the final language-generation step failed."
            )

    else:

        answer = (
            "The available evidence did not meet the "
            "project-defined grounding requirement."
        )

    # ------------------------------------------------
    # STEP 11 — XAI
    # ------------------------------------------------

    try:

        xai = generate_xai_explanation(
            argumentation_result=argumentation_result,
            safety_result=safety_result,
            route=route,
            medicine=medicine,
            tools_used=tools_used
        )

    except Exception as e:

        xai = (
            f"XAI explanation could not be generated: {str(e)}"
        )

    # ------------------------------------------------
    # STEP 12 — FINAL RESULT
    # ------------------------------------------------

    return {
        "route": route,

        "medicine": medicine,

        "rxcui": rxcui,

        "tools_used": tools_used,

        "rag_results": rag_results,

        "argumentation": argumentation_result,

        "evidence": grounded_evidence,

        "safety": safety_result,

        "answer": answer,

        "xai": xai,

        "decision": argumentation_decision
    }