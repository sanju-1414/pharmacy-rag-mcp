import sys
import os
import re
import json
import importlib.util


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# IMPORT RAG
# ============================================================

from rag.retrieve import (
    retrieve_documents,
    check_rag_sufficiency,
)


# ============================================================
# LOAD MCP ROUTER
# ============================================================

router_path = os.path.join(
    PROJECT_ROOT,
    "mcp_server",
    "router.py"
)

spec = importlib.util.spec_from_file_location(
    "local_router",
    router_path
)

router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


# ============================================================
# PROJECT THRESHOLD
# ============================================================

GROUNDING_THRESHOLD = 80.0


# ============================================================
# SIDE EFFECT TERMS
# ============================================================

SIDE_EFFECT_TERMS = [
    "diarrhea",
    "nausea",
    "vomiting",
    "stomach pain",
    "abdominal pain",
    "headache",
    "dizziness",
    "rash",
    "itching",
    "loss of appetite",
    "photosensitivity",
    "sun sensitivity",
    "tooth discoloration",
    "discoloration of permanent teeth",
    "difficulty swallowing",
    "heartburn",
    "joint pain",
    "muscle pain",
    "fatigue"
]


# ============================================================
# MEDICINE DETECTION
# ============================================================

def detect_medicine_from_question(query):

    medicines = [
        "doxycycline",
        "amoxicillin",
        "ibuprofen",
        "paracetamol",
        "acetaminophen",
        "cetirizine",
        "omeprazole"
    ]

    query_lower = query.lower()

    for medicine in medicines:

        if medicine in query_lower:
            return medicine

    return None


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    if isinstance(text, (dict, list)):

        return ""

    text = str(text)

    text = text.replace("\\n", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# MCP RESULT → TEXT
# ============================================================

def extract_mcp_text(mcp_result):

    if not mcp_result:
        return ""

    # MCP CallToolResult
    if hasattr(mcp_result, "content"):

        try:

            content = mcp_result.content

            if content:

                first = content[0]

                if hasattr(first, "text"):
                    return first.text

                if isinstance(first, dict):
                    return first.get("text", "")

        except Exception:
            pass

    # Dictionary
    if isinstance(mcp_result, dict):

        if "mcp_result" in mcp_result:

            return extract_mcp_text(
                mcp_result["mcp_result"]
            )

        try:
            return json.dumps(
                mcp_result,
                ensure_ascii=False
            )

        except Exception:
            return str(mcp_result)

    # String
    if isinstance(mcp_result, str):
        return mcp_result

    return str(mcp_result)


# ============================================================
# PARSE MCP JSON
# ============================================================

def parse_mcp_payload(mcp_result):

    raw = extract_mcp_text(
        mcp_result
    )

    if not raw:
        return {}

    try:

        return json.loads(raw)

    except Exception:

        start = raw.find("{")
        end = raw.rfind("}")

        if start != -1 and end != -1:

            try:

                return json.loads(
                    raw[start:end + 1]
                )

            except Exception:
                pass

    return {}


# ============================================================
# NORMALIZE EFFECT
# ============================================================

def normalize_effect(effect):

    effect = effect.lower().strip()

    replacements = {

        "loose stool":
            "diarrhea",

        "loose stools":
            "diarrhea",

        "stomach ache":
            "stomach pain",

        "abdominal discomfort":
            "abdominal pain",

        "sun sensitivity":
            "photosensitivity"
    }

    return replacements.get(
        effect,
        effect
    )


# ============================================================
# FIND EFFECTS
# ============================================================

def find_effects(text):

    text_lower = text.lower()

    effects = []

    terms = sorted(
        SIDE_EFFECT_TERMS,
        key=len,
        reverse=True
    )

    for term in terms:

        if term in text_lower:

            effect = normalize_effect(
                term
            )

            if effect not in effects:

                effects.append(
                    effect
                )

    return effects


# ============================================================
# FREQUENCY
# ============================================================

def detect_frequency(text):

    text_lower = text.lower()

    # Check specific words first.

    if "very common" in text_lower:
        return "very common"

    if "infrequent" in text_lower:
        return "infrequent"

    if "uncommon" in text_lower:
        return "uncommon"

    if "rare" in text_lower:
        return "rare"

    if "common" in text_lower:
        return "common"

    return "unspecified"


# ============================================================
# SPLIT TEXT INTO SENTENCES
# ============================================================

def split_sentences(text):

    text = clean_text(text)

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


# ============================================================
# DIRECT DRUG-EFFECT RELATIONSHIP
# ============================================================

def check_direct_relationship(
    medicine,
    effect,
    text,
    section
):

    text_lower = text.lower()
    medicine_lower = medicine.lower()
    effect_lower = effect.lower()

    # --------------------------------------------------------
    # Effect must be present
    # --------------------------------------------------------

    if effect_lower not in text_lower:

        return 0.0

    # --------------------------------------------------------
    # MedlinePlus side_effects section
    #
    # If the item came directly from the side-effects
    # section, it is already associated with the medicine.
    # --------------------------------------------------------

    if (
        "medlineplus" in section.lower()
        and "side_effect" in section.lower()
    ):

        return 100.0

    # --------------------------------------------------------
    # Explicit drug name
    # --------------------------------------------------------

    if medicine_lower in text_lower:

        return 100.0

    # --------------------------------------------------------
    # Explicit causation
    # --------------------------------------------------------

    causation_words = [
        "causes",
        "cause",
        "caused by",
        "associated with",
        "associated",
        "reported with",
        "reported",
        "adverse reaction",
        "adverse reactions",
        "side effect",
        "side effects"
    ]

    for word in causation_words:

        if word in text_lower:

            return 90.0

    # --------------------------------------------------------
    # Class-level evidence
    # --------------------------------------------------------

    class_words = [
        "tetracycline",
        "tetracyclines"
    ]

    for word in class_words:

        if word in text_lower:

            return 70.0

    # --------------------------------------------------------
    # General antibacterial evidence
    # --------------------------------------------------------

    general_words = [
        "antibacterial drugs",
        "antibiotics",
        "antibiotic drugs"
    ]

    for word in general_words:

        if word in text_lower:

            return 40.0

    return 0.0


# ============================================================
# EVIDENCE SPECIFICITY
# ============================================================

def determine_specificity(
    medicine,
    text,
    source,
    section
):

    text_lower = text.lower()

    medicine_lower = medicine.lower()

    source_lower = source.lower()

    section_lower = section.lower()

    # --------------------------------------------------------
    # MedlinePlus side-effects section
    # --------------------------------------------------------

    if (
        source_lower == "medlineplus"
        and "side_effect" in section_lower
    ):

        return "direct"

    # --------------------------------------------------------
    # Explicit medicine name
    # --------------------------------------------------------

    if medicine_lower in text_lower:

        return "direct"

    # --------------------------------------------------------
    # Tetracycline class
    # --------------------------------------------------------

    if (
        "tetracycline" in text_lower
        or "tetracyclines" in text_lower
    ):

        return "class-level"

    # --------------------------------------------------------
    # General antibiotics
    # --------------------------------------------------------

    if (
        "antibacterial drugs" in text_lower
        or "antibiotics" in text_lower
    ):

        return "general"

    return "unclear"


# ============================================================
# SOURCE QUALITY
# ============================================================

def source_quality(
    source,
    section,
    specificity
):

    source_lower = source.lower()
    section_lower = section.lower()

    # Direct MedlinePlus side-effect evidence
    if (
        source_lower == "medlineplus"
        and "side_effect" in section_lower
        and specificity == "direct"
    ):

        return 100.0

    # Direct openFDA adverse reactions
    if (
        source_lower == "openfda"
        and "adverse" in section_lower
        and specificity == "direct"
    ):

        return 100.0

    # FDA warnings/precautions
    if (
        source_lower == "openfda"
        and (
            "warning" in section_lower
            or "precaution" in section_lower
        )
        and specificity == "direct"
    ):

        return 95.0

    # Other direct MedlinePlus evidence
    if (
        source_lower == "medlineplus"
        and specificity == "direct"
    ):

        return 95.0

    # Class-level
    if specificity == "class-level":

        return 75.0

    # General
    if specificity == "general":

        return 45.0

    return 30.0


# ============================================================
# QUESTION RELEVANCE
# ============================================================

def calculate_question_relevance(
    query,
    effect
):

    query_lower = query.lower()

    # If user explicitly asks about this effect
    if effect.lower() in query_lower:

        return 100.0

    side_effect_terms = [
        "side effect",
        "side effects",
        "adverse reaction",
        "adverse reactions",
        "reaction",
        "reactions"
    ]

    for term in side_effect_terms:

        if term in query_lower:

            return 95.0

    return 50.0


# ============================================================
# EVIDENCE COMPLETENESS
# ============================================================

def calculate_completeness(
    text
):

    text = clean_text(text)

    if not text:

        return 0.0

    if len(text) < 30:

        return 50.0

    if len(text) < 80:

        return 75.0

    return 100.0


# ============================================================
# CLAIM-SPECIFIC CORROBORATION
# ============================================================

def calculate_corroboration(
    evidence_items
):

    direct_sources = set()

    for item in evidence_items:

        if item["direct_support"] >= 80:

            direct_sources.add(
                item["source"]
            )

    # Two independent sources
    if len(direct_sources) >= 2:

        return 100.0

    # One direct source
    if len(direct_sources) == 1:

        return 60.0

    # Only weak/class/general evidence
    return 20.0


# ============================================================
# CONTRADICTION
# ============================================================

def calculate_contradiction(
    effect,
    evidence_items
):

    frequencies = []

    for item in evidence_items:

        frequency = item.get(
            "frequency",
            "unspecified"
        )

        if frequency != "unspecified":

            frequencies.append(
                frequency
            )

    # No contradictory frequency
    if not frequencies:

        return 0.0

    # We are saying "can cause", so
    # infrequent/rare is NOT a contradiction.
    #
    # Contradiction would matter if the generated
    # answer claimed "common".

    return 0.0


# ============================================================
# BUILD EVIDENCE ITEM
# ============================================================

def make_evidence_item(
    medicine,
    effect,
    source,
    section,
    text
):

    specificity = determine_specificity(
        medicine,
        text,
        source,
        section
    )

    direct_support = check_direct_relationship(
        medicine,
        effect,
        text,
        f"{source} {section}"
    )

    frequency = detect_frequency(
        text
    )

    quality = source_quality(
        source,
        section,
        specificity
    )

    completeness = calculate_completeness(
        text
    )

    return {

        "medicine": medicine,

        "effect": effect,

        "source": source,

        "section": section,

        "text": text,

        "specificity": specificity,

        "direct_support": direct_support,

        "source_quality": quality,

        "frequency": frequency,

        "completeness": completeness
    }


# ============================================================
# EXTRACT OPENFDA EVIDENCE
# ============================================================

def extract_openfda_evidence(
    openfda,
    medicine
):

    evidence = []

    if not isinstance(
        openfda,
        dict
    ):

        return evidence

    # --------------------------------------------------------
    # IMPORTANT:
    # Ignore metadata fields such as "sections".
    # Extract actual individual sections.
    # --------------------------------------------------------

    sections = openfda.get(
        "sections"
    )

    if isinstance(
        sections,
        dict
    ):

        for section_name, section_value in sections.items():

            if section_value is None:
                continue

            # ------------------------------------------------
            # List section
            # ------------------------------------------------

            if isinstance(
                section_value,
                list
            ):

                values = section_value

            else:

                values = [
                    section_value
                ]

            for value in values:

                text = clean_text(
                    value
                )

                if not text:
                    continue

                # Break long sections into sentences
                sentences = split_sentences(
                    text
                )

                for sentence in sentences:

                    effects = find_effects(
                        sentence
                    )

                    for effect in effects:

                        item = make_evidence_item(
                            medicine,
                            effect,
                            "openFDA",
                            section_name,
                            sentence
                        )

                        # Keep only evidence that has
                        # some actual relationship.
                        if (
                            item["direct_support"] > 0
                        ):

                            evidence.append(
                                item
                            )

    return evidence


# ============================================================
# EXTRACT MEDLINEPLUS EVIDENCE
# ============================================================

def extract_medlineplus_evidence(
    medlineplus,
    medicine
):

    evidence = []

    if not isinstance(
        medlineplus,
        dict
    ):

        return evidence

    sections = medlineplus.get(
        "sections"
    )

    if not isinstance(
        sections,
        dict
    ):

        return evidence

    for section_name, section_value in sections.items():

        if section_value is None:
            continue

        # ----------------------------------------------------
        # Side effects list
        # ----------------------------------------------------

        if isinstance(
            section_value,
            list
        ):

            for value in section_value:

                text = clean_text(
                    value
                )

                if not text:
                    continue

                effects = find_effects(
                    text
                )

                for effect in effects:

                    item = make_evidence_item(
                        medicine,
                        effect,
                        "MedlinePlus",
                        section_name,
                        text
                    )

                    # Side effects list is direct evidence
                    if (
                        item["direct_support"] >= 80
                    ):

                        evidence.append(
                            item
                        )

        # ----------------------------------------------------
        # Normal text section
        # ----------------------------------------------------

        else:

            text = clean_text(
                section_value
            )

            if not text:
                continue

            sentences = split_sentences(
                text
            )

            for sentence in sentences:

                effects = find_effects(
                    sentence
                )

                for effect in effects:

                    item = make_evidence_item(
                        medicine,
                        effect,
                        "MedlinePlus",
                        section_name,
                        sentence
                    )

                    if (
                        item["direct_support"] > 0
                    ):

                        evidence.append(
                            item
                        )

    return evidence


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_evidence(
    evidence
):

    unique = []

    seen = set()

    for item in evidence:

        key = (
            item["source"],
            item["section"],
            item["effect"],
            item["text"]
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            item
        )

    return unique


# ============================================================
# GROUP EVIDENCE BY EFFECT
# ============================================================

def group_evidence_by_effect(
    evidence
):

    grouped = {}

    for item in evidence:

        effect = item["effect"]

        if effect not in grouped:

            grouped[effect] = []

        grouped[effect].append(
            item
        )

    return grouped


# ============================================================
# CALCULATE FINAL EVIDENCE SCORE
# ============================================================

def calculate_evidence_score(
    query,
    effect,
    evidence_items
):

    if not evidence_items:

        return {

            "source_score": 0.0,

            "direct_support": 0.0,

            "question_relevance": 0.0,

            "corroboration": 0.0,

            "completeness": 0.0,

            "contradiction": 0.0,

            "final_score": 0.0
        }

    # Best source quality
    source_score = max(
        item["source_quality"]
        for item in evidence_items
    )

    # Best direct support
    direct_support = max(
        item["direct_support"]
        for item in evidence_items
    )

    relevance = (
        calculate_question_relevance(
            query,
            effect
        )
    )

    corroboration = (
        calculate_corroboration(
            evidence_items
        )
    )

    completeness = max(
        item["completeness"]
        for item in evidence_items
    )

    contradiction = (
        calculate_contradiction(
            effect,
            evidence_items
        )
    )

    final_score = (

        0.30 * source_score

        + 0.30 * direct_support

        + 0.20 * relevance

        + 0.10 * corroboration

        + 0.10 * completeness

        - contradiction
    )

    final_score = max(
        0.0,
        min(
            100.0,
            final_score
        )
    )

    return {

        "source_score":
            source_score,

        "direct_support":
            direct_support,

        "question_relevance":
            relevance,

        "corroboration":
            corroboration,

        "completeness":
            completeness,

        "contradiction":
            contradiction,

        "final_score":
            final_score
    }


# ============================================================
# ARGUMENTATION DECISION
# ============================================================

def make_decision(
    score
):

    if score >= GROUNDING_THRESHOLD:

        return "SUPPORTED"

    if score >= 50:

        return "QUALIFIED"

    return "NOT SUPPORTED"


# ============================================================
# PRINT EVIDENCE ANALYSIS
# ============================================================

def display_evidence_analysis(
    query,
    effect,
    evidence_items
):

    scores = calculate_evidence_score(
        query,
        effect,
        evidence_items
    )

    decision = make_decision(
        scores["final_score"]
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        f"EVIDENCE ANALYSIS: "
        f"{effect}"
    )

    print(
        "=" * 70
    )

    print(
        f"\nEvidence supporting: "
        f"{effect}"
    )

    for index, item in enumerate(
        evidence_items,
        start=1
    ):

        print(
            f"\nEvidence {index}"
        )

        print(
            f"Source       : "
            f"{item['source']}"
        )

        print(
            f"Section      : "
            f"{item['section']}"
        )

        print(
            f"Specificity  : "
            f"{item['specificity']}"
        )

        print(
            f"Frequency    : "
            f"{item['frequency']}"
        )

        print(
            f"Direct link  : "
            f"{item['direct_support']:.1f}%"
        )

        print(
            f"\nText:\n"
            f"{item['text'][:700]}"
        )

    print(
        "\nARGUMENTATION / GROUNDING"
    )

    print(
        "-" * 70
    )

    print(
        f"Source quality       : "
        f"{scores['source_score']:.1f}%"
    )

    print(
        f"Direct drug-effect   : "
        f"{scores['direct_support']:.1f}%"
    )

    print(
        f"Question relevance   : "
        f"{scores['question_relevance']:.1f}%"
    )

    print(
        f"Corroboration        : "
        f"{scores['corroboration']:.1f}%"
    )

    print(
        f"Evidence completeness: "
        f"{scores['completeness']:.1f}%"
    )

    print(
        f"Contradiction        : "
        f"{scores['contradiction']:.1f}%"
    )

    print(
        "\nFINAL EVIDENCE SUPPORT SCORE: "
        f"{scores['final_score']:.1f}%"
    )

    print(
        f"DECISION: {decision}"
    )

    return scores, decision


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 70
    )

    print(
        "PHARMACY RAG + MCP EVIDENCE ARGUMENTATION TEST"
    )

    print(
        "=" * 70
    )

    question = input(
        "\nEnter your question: "
    ).strip()

    if not question:

        print(
            "No question entered."
        )

        return

    # ========================================================
    # MEDICINE
    # ========================================================

    medicine = detect_medicine_from_question(
        question
    )

    print(
        f"\nDetected medicine: "
        f"{medicine}"
    )

    if not medicine:

        print(
            "\nMedicine could not be identified."
        )

        return

    # ========================================================
    # RAG
    # ========================================================

    print(
        "\n========== RAG CHECK =========="
    )

    rag_results = retrieve_documents(
        question,
        k=3
    )

    rag_sufficient = (
        check_rag_sufficiency(
            rag_results,
            question
        )
    )

    print(
        f"RAG sufficient: "
        f"{rag_sufficient}"
    )

    # ========================================================
    # CURRENT TEST FOCUSES ON MCP
    # ========================================================

    if rag_sufficient:

        print(
            "\n========== ROUTE =========="
        )

        print(
            "Route: RAG"
        )

        print(
            "\nRAG contains sufficient evidence."
        )

        print(
            "MCP argumentation is not required "
            "for this query."
        )

        return

    # ========================================================
    # MCP
    # ========================================================

    print(
        "\n========== ROUTE =========="
    )

    print(
        "Route: MCP"
    )

    print(
        "\nCalling MCP..."
    )

    route_result = router.route_query(
        question
    )

    if route_result.get("error"):

        print(
            "\nMCP ERROR:"
        )

        print(
            route_result["error"]
        )

        return

    mcp_result = route_result.get(
        "mcp_result"
    )

    if not mcp_result:

        print(
            "\nNo MCP result returned."
        )

        return

    # ========================================================
    # PARSE MCP
    # ========================================================

    payload = parse_mcp_payload(
        mcp_result
    )

    if not payload:

        print(
            "\nCould not parse MCP response."
        )

        return

    print(
        "\nMCP structured evidence received."
    )

    print(
        f"RxCUI: "
        f"{route_result.get('rxcui')}"
    )

    # ========================================================
    # EXTRACT SOURCES
    # ========================================================

    openfda = payload.get(
        "openfda",
        {}
    )

    medlineplus = payload.get(
        "medlineplus",
        {}
    )

    openfda_evidence = (
        extract_openfda_evidence(
            openfda,
            medicine
        )
    )

    medlineplus_evidence = (
        extract_medlineplus_evidence(
            medlineplus,
            medicine
        )
    )

    all_evidence = (
        openfda_evidence
        + medlineplus_evidence
    )

    all_evidence = (
        remove_duplicate_evidence(
            all_evidence
        )
    )

    print(
        f"\nOpenFDA evidence items: "
        f"{len(openfda_evidence)}"
    )

    print(
        f"MedlinePlus evidence items: "
        f"{len(medlineplus_evidence)}"
    )

    print(
        f"Total evidence items: "
        f"{len(all_evidence)}"
    )

    if not all_evidence:

        print(
            "\nNo sufficiently grounded "
            "side-effect evidence found."
        )

        return

    # ========================================================
    # GROUP EVIDENCE
    # ========================================================

    grouped = group_evidence_by_effect(
        all_evidence
    )

    print(
        f"Unique evidence categories: "
        f"{len(grouped)}"
    )

    # ========================================================
    # ARGUMENTATION
    # ========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "EVIDENCE-BASED ARGUMENTATION"
    )

    print(
        "=" * 70
    )

    accepted_effects = []
    qualified_effects = []

    for effect, evidence_items in grouped.items():

        scores, decision = (
            display_evidence_analysis(
                question,
                effect,
                evidence_items
            )
        )

        if decision == "SUPPORTED":

            accepted_effects.append(
                (
                    effect,
                    evidence_items,
                    scores
                )
            )

        elif decision == "QUALIFIED":

            qualified_effects.append(
                (
                    effect,
                    evidence_items,
                    scores
                )
            )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "ARGUMENTATION SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        f"Evidence categories evaluated: "
        f"{len(grouped)}"
    )

    print(
        f"Supported: "
        f"{len(accepted_effects)}"
    )

    print(
        f"Qualified: "
        f"{len(qualified_effects)}"
    )

    print(
        f"Grounding threshold: "
        f"{GROUNDING_THRESHOLD}%"
    )

    # ========================================================
    # LLAMA-READY EVIDENCE
    # ========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "EVIDENCE READY FOR LLAMA"
    )

    print(
        "=" * 70
    )

    if not accepted_effects:

        print(
            "No evidence passed the grounding threshold."
        )

        return

    for effect, evidence_items, scores in accepted_effects:

        print(
            f"\n• {effect}"
        )

        print(
            f"  Evidence support: "
            f"{scores['final_score']:.1f}%"
        )

        for item in evidence_items:

            if item["direct_support"] >= 80:

                print(
                    f"  - {item['source']}: "
                    f"{item['text'][:400]}"
                )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "ARGUMENTATION COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "\nThe next stage is to pass only this "
        "grounded evidence to Llama."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()