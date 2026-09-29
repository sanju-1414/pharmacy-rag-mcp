# ------------------------------------------------
# ARGUMENTATION + GROUNDING
# ------------------------------------------------

GROUNDING_THRESHOLD = 80.0


# ------------------------------------------------
# SIDE EFFECT / EVIDENCE TERMS
# ------------------------------------------------

SIDE_EFFECT_TERMS = [
    "diarrhea",
    "vomiting",
    "nausea",
    "stomach pain",
    "abdominal pain",
    "loss of appetite",
    "itching",
    "headache",
    "rash",
    "joint pain",
    "photosensitivity",
    "tooth discoloration",
    "enamel hypoplasia",
    "dizziness",
    "constipation",
    "drowsiness",
    "dry mouth",
    "fatigue",
    "weakness",
]


# ------------------------------------------------
# TEXT CLEANING
# ------------------------------------------------

def clean_text(text):

    if text is None:
        return ""

    text = str(text)

    text = text.replace(
        "\n",
        " "
    )

    text = " ".join(
        text.split()
    )

    return text.strip()


# ------------------------------------------------
# SPLIT SENTENCES
# ------------------------------------------------

def split_sentences(text):

    text = clean_text(
        text
    )

    if not text:
        return []

    import re

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


# ------------------------------------------------
# NORMALIZE EFFECT
# ------------------------------------------------

def normalize_effect(effect):

    effect = clean_text(
        effect
    ).lower()

    replacements = {
        "stomach ache": "stomach pain",
        "abdominal discomfort": "abdominal pain",
        "skin rash": "rash",
        "skin rashes": "rash",
        "joint aches": "joint pain",
        "tooth discolouration": "tooth discoloration",
        "tooth discolourations": "tooth discoloration",
    }

    return replacements.get(
        effect,
        effect
    )


# ------------------------------------------------
# FIND EFFECTS IN TEXT
# ------------------------------------------------

def find_effects_in_text(text):

    text_lower = clean_text(
        text
    ).lower()

    found = []

    for term in SIDE_EFFECT_TERMS:

        if term.lower() in text_lower:

            found.append(
                normalize_effect(term)
            )

    # Remove duplicates
    return list(
        dict.fromkeys(found)
    )


# ------------------------------------------------
# EXTRACT EFFECT TEXT
# ------------------------------------------------

def extract_effect_text(
    text,
    effect
):

    text = clean_text(
        text
    )

    if not text:
        return ""

    sentences = split_sentences(
        text
    )

    effect_lower = effect.lower()

    matched = []

    for sentence in sentences:

        if effect_lower in sentence.lower():

            matched.append(
                sentence
            )

    if matched:
        return " ".join(
            matched
        )

    return text


# ------------------------------------------------
# DETECT FREQUENCY
# ------------------------------------------------

def detect_frequency(text):

    text_lower = clean_text(text).lower()

    # Specific frequency statements
    if "very common" in text_lower:
        return "very common"

    if "uncommon" in text_lower:
        return "uncommon"

    if "infrequent" in text_lower:
        return "infrequent"

    if "rare" in text_lower:
        return "rare"

    if "frequent" in text_lower:
        return "frequent"

    if "occasionally reported" in text_lower:
        return "occasional"

    if "occasionally" in text_lower:
        return "occasional"

    if "has been reported" in text_lower:
        return "reported"

    if "have been reported" in text_lower:
        return "reported"

    if "observed" in text_lower:
        return "observed"

    # "Common" is only accepted when the evidence
    # explicitly describes the medicine/reaction,
    # not merely a broad drug class.
    if "common adverse reaction" in text_lower:
        return "common"

    if "common side effect" in text_lower:
        return "common"

    if "commonly reported" in text_lower:
        return "common"

    return "not specified"


# ------------------------------------------------
# SOURCE QUALITY
# ------------------------------------------------

def source_quality(source):

    source_lower = clean_text(
        source
    ).lower()

    if "openfda" in source_lower:
        return 100.0

    if "medlineplus" in source_lower:
        return 95.0

    if "rxnorm" in source_lower:
        return 90.0

    if "rag" in source_lower:
        return 90.0

    return 70.0


# ------------------------------------------------
# DIRECT SUPPORT
# ------------------------------------------------

def calculate_direct_support(
    effect,
    text,
    medicine
):

    text_lower = clean_text(
        text
    ).lower()

    effect_lower = clean_text(
        effect
    ).lower()

    medicine_lower = clean_text(
        medicine
    ).lower()

    if effect_lower not in text_lower:
        return 0.0

    # Evidence explicitly mentioning
    # the medicine receives full direct support.
    if medicine_lower and medicine_lower in text_lower:
        return 100.0

    # Evidence containing the effect but
    # not explicitly naming the medicine
    # still receives direct effect support.
    return 100.0


# ------------------------------------------------
# SPECIFICITY
# ------------------------------------------------

def calculate_specificity(
    effect,
    text,
    medicine
):

    text_lower = clean_text(
        text
    ).lower()

    medicine_lower = clean_text(
        medicine
    ).lower()

    # Medicine explicitly named
    if medicine_lower and medicine_lower in text_lower:
        return 100.0

    # Class-level wording
    class_terms = [
        "tetracycline",
        "tetracyclines",
        "drug class",
        "class of drugs",
        "antibacterial agents",
        "antibacterial drugs",
    ]

    for term in class_terms:

        if term in text_lower:
            return 60.0

    return 80.0


# ------------------------------------------------
# RELEVANCE
# ------------------------------------------------

def calculate_relevance(
    effect,
    query,
    text
):

    query_lower = clean_text(
        query
    ).lower()

    text_lower = clean_text(
        text
    ).lower()

    effect_lower = clean_text(
        effect
    ).lower()

    score = 50.0

    if effect_lower in query_lower:
        score += 30.0

    if effect_lower in text_lower:
        score += 20.0

    return min(
        score,
        100.0
    )


# ------------------------------------------------
# COMPLETENESS
# ------------------------------------------------

def calculate_completeness(text):

    text = clean_text(
        text
    )

    if not text:
        return 0.0

    if len(text) >= 120:
        return 100.0

    if len(text) >= 60:
        return 90.0

    if len(text) >= 30:
        return 80.0

    return 70.0


# ------------------------------------------------
# CONTRADICTION DETECTION
# ------------------------------------------------

def detect_contradiction(
    effect,
    items
):

    # Basic contradiction detection.
    # More advanced contradiction analysis
    # can be added later.

    if not items:
        return False

    return False


# ------------------------------------------------
# CREATE EVIDENCE ITEM
# ------------------------------------------------

def create_evidence_item(
    effect,
    source,
    section,
    text,
    medicine,
    page=None,
    source_url=None
):

    text = clean_text(
        text
    )

    quality = source_quality(
        source
    )

    direct_support = calculate_direct_support(
        effect,
        text,
        medicine
    )

    specificity = calculate_specificity(
        effect,
        text,
        medicine
    )

    frequency = detect_frequency(
        text
    )

    completeness = calculate_completeness(
        text
    )

    return {
        "effect": normalize_effect(
            effect
        ),

        "source": source,

        # External source URL
        # Used by Explainable AI for clickable links.
        "source_url": source_url,

        "section": section,

        "page": page,

        "text": text,

        "medicine": medicine,

        "direct_support": direct_support,

        "specificity": specificity,

        "relevance": 0.0,

        "completeness": completeness,

        "source_quality": quality,

        "frequency": frequency,

        "contradiction": False,
    }


# ------------------------------------------------
# RAG EVIDENCE EXTRACTION
# ------------------------------------------------

def extract_rag_evidence(
    rag_results,
    medicine,
    query
):

    evidence = []

    if not rag_results:
        return evidence

    for document, distance in rag_results:

        text = clean_text(
            document.page_content
        )

        if not text:
            continue

        metadata = document.metadata or {}

        source = metadata.get(
            "source",
            "RAG"
        )

        section = metadata.get(
            "section",
            "retrieved_document"
        )

        page = metadata.get(
            "page"
        )

        effects = find_effects_in_text(
            text
        )

        for effect in effects:

            item = create_evidence_item(
                effect=effect,
                source="RAG",
                section=section,
                text=text,
                medicine=medicine,
                page=page,
                source_url=None
            )

            item["relevance"] = calculate_relevance(
                effect,
                query,
                text
            )

            evidence.append(
                item
            )

    return evidence


# ------------------------------------------------
# OPENFDA EVIDENCE EXTRACTION
# ------------------------------------------------

def extract_openfda_evidence(
    openfda,
    medicine,
    query=""
):

    evidence = []

    if not isinstance(
        openfda,
        dict
    ):
        return evidence

    sections = openfda.get(
        "sections",
        {}
    )

    if not isinstance(
        sections,
        dict
    ):
        return evidence

    # URL generated by the MCP openFDA function.
    source_url = openfda.get(
        "url"
    )

    for section, content in sections.items():

        if not content:
            continue

        if isinstance(
            content,
            list
        ):

            items = [
                clean_text(item)
                for item in content
                if clean_text(item)
            ]

        else:

            items = [
                clean_text(content)
            ]

        for item_text in items:

            if not item_text:
                continue

            sentences = split_sentences(
                item_text
            )

            for sentence in sentences:

                sentence = clean_text(
                    sentence
                )

                if not sentence:
                    continue

                effects = find_effects_in_text(
                    sentence
                )

                # --------------------------------
                # SIDE-EFFECT EVIDENCE
                # --------------------------------

                for effect in effects:

                    item = create_evidence_item(
                        effect=effect,
                        source="openFDA",
                        section=section,
                        text=sentence,
                        medicine=medicine,
                        source_url=source_url
                    )

                    item["relevance"] = (
                        calculate_relevance(
                            effect,
                            query,
                            sentence
                        )
                    )

                    evidence.append(
                        item
                    )

                # --------------------------------
                # WARNING / PRECAUTION EVIDENCE
                # --------------------------------

                section_lower = (
                    section.lower()
                )

                if section_lower == "warnings":

                    item = create_evidence_item(
                        effect="important warning",
                        source="openFDA",
                        section=section,
                        text=sentence,
                        medicine=medicine,
                        source_url=source_url
                    )

                    item["relevance"] = (
                        calculate_relevance(
                            "important warning",
                            query,
                            sentence
                        )
                    )

                    evidence.append(
                        item
                    )

                elif section_lower == "precautions":

                    item = create_evidence_item(
                        effect="precaution",
                        source="openFDA",
                        section=section,
                        text=sentence,
                        medicine=medicine,
                        source_url=source_url
                    )

                    item["relevance"] = (
                        calculate_relevance(
                            "precaution",
                            query,
                            sentence
                        )
                    )

                    evidence.append(
                        item
                    )

                elif section_lower == "contraindications":

                    item = create_evidence_item(
                        effect="contraindication",
                        source="openFDA",
                        section=section,
                        text=sentence,
                        medicine=medicine,
                        source_url=source_url
                    )

                    item["relevance"] = (
                        calculate_relevance(
                            "contraindication",
                            query,
                            sentence
                        )
                    )

                    evidence.append(
                        item
                    )

                elif section_lower == "drug_interactions":

                    item = create_evidence_item(
                        effect="drug interaction",
                        source="openFDA",
                        section=section,
                        text=sentence,
                        medicine=medicine,
                        source_url=source_url
                    )

                    item["relevance"] = (
                        calculate_relevance(
                            "drug interaction",
                            query,
                            sentence
                        )
                    )

                    evidence.append(
                        item
                    )

    return evidence


# ------------------------------------------------
# MEDLINEPLUS EVIDENCE EXTRACTION
# ------------------------------------------------

def extract_medlineplus_evidence(
    medlineplus,
    medicine,
    query=""
):

    evidence = []

    if not isinstance(
        medlineplus,
        dict
    ):
        return evidence

    sections = medlineplus.get(
        "sections",
        {}
    )

    if not isinstance(
        sections,
        dict
    ):
        return evidence

    # URL generated by the MCP MedlinePlus function.
    source_url = medlineplus.get(
        "url"
    )

    for section, content in sections.items():

        if not content:
            continue

        if isinstance(
            content,
            list
        ):

            items = [
                clean_text(item)
                for item in content
                if clean_text(item)
            ]

        else:

            items = [
                clean_text(content)
            ]

        for item_text in items:

            if not item_text:
                continue

            sentences = split_sentences(
                item_text
            )

            for sentence in sentences:

                sentence = clean_text(
                    sentence
                )

                if not sentence:
                    continue

                effects = find_effects_in_text(
                    sentence
                )

                for effect in effects:

                    item = create_evidence_item(
                        effect=effect,
                        source="MedlinePlus",
                        section=section,
                        text=sentence,
                        medicine=medicine,
                        source_url=source_url
                    )

                    item["relevance"] = calculate_relevance(
                        effect,
                        query,
                        sentence
                    )

                    evidence.append(
                        item
                    )

    return evidence


# ------------------------------------------------
# REMOVE DUPLICATE EVIDENCE
# ------------------------------------------------

def remove_duplicate_evidence(
    evidence
):

    unique = []

    seen = set()

    for item in evidence:

        key = (
            item.get(
                "effect",
                ""
            ),
            item.get(
                "source",
                ""
            ),
            item.get(
                "section",
                ""
            ),
            item.get(
                "text",
                ""
            )
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            item
        )

    return unique


# ------------------------------------------------
# GROUP EVIDENCE BY EFFECT
# ------------------------------------------------

def group_evidence_by_effect(
    evidence
):

    grouped = {}

    for item in evidence:

        effect = item.get(
            "effect",
            "unknown"
        )

        grouped.setdefault(
            effect,
            []
        ).append(
            item
        )

    return grouped


# ------------------------------------------------
# CORROBORATION
# ------------------------------------------------

def calculate_corroboration(
    items
):

    sources = set()

    for item in items:

        source = item.get(
            "source"
        )

        if source:
            sources.add(
                source
            )

    if len(sources) >= 2:
        return 100.0

    if len(sources) == 1:
        return 60.0

    return 0.0


# ------------------------------------------------
# ANALYZE ONE EFFECT
# ------------------------------------------------

def analyze_effect(
    effect,
    items,
    query,
    medicine
):

    if not items:

        return {
            "effect": effect,
            "score": 0.0,
            "decision": "QUALIFY",
            "items": [],
            "scores": {
                "final_score": 0.0
            },
            "evidence": []
        }

    direct_support = max(
        item.get(
            "direct_support",
            0.0
        )
        for item in items
    )

    specificity = max(
        item.get(
            "specificity",
            0.0
        )
        for item in items
    )

    relevance = max(
        item.get(
            "relevance",
            0.0
        )
        for item in items
    )

    completeness = max(
        item.get(
            "completeness",
            0.0
        )
        for item in items
    )

    quality = max(
        item.get(
            "source_quality",
            0.0
        )
        for item in items
    )

    corroboration = calculate_corroboration(
        items
    )

    # ------------------------------------------------
    # FINAL PROJECT-DEFINED SUPPORT SCORE
    # ------------------------------------------------

    score = (
        direct_support * 0.30
        + specificity * 0.15
        + relevance * 0.20
        + completeness * 0.10
        + quality * 0.15
        + corroboration * 0.10
    )

    score = round(
        min(
            score,
            100.0
        ),
        2
    )

    decision = (
        "SUPPORTED"
        if score >= GROUNDING_THRESHOLD
        else "QUALIFY"
    )

    return {
        "effect": effect,

        "score": score,

        "decision": decision,

        "items": items,

        # Compatibility with XAI / pipeline
        "scores": {
            "final_score": score
        },

        "evidence": items,

        "corroboration": corroboration,
    }


# ------------------------------------------------
# MAIN ARGUMENTATION FUNCTION
# ------------------------------------------------

def run_argumentation(
    query,
    medicine,
    payload
):

    all_evidence = []

    # ------------------------------------------------
    # RAG PAYLOAD
    # ------------------------------------------------

    if isinstance(
        payload,
        dict
    ):

        rag_results = payload.get(
            "rag_results",
            []
        )

        if rag_results:

            all_evidence.extend(
                extract_rag_evidence(
                    rag_results,
                    medicine,
                    query
                )
            )

        # ------------------------------------------------
        # OPENFDA
        # ------------------------------------------------

        openfda = payload.get(
            "openfda"
        )

        if openfda:

            all_evidence.extend(
                extract_openfda_evidence(
                    openfda,
                    medicine,
                    query
                )
            )

        # ------------------------------------------------
        # MEDLINEPLUS
        # ------------------------------------------------

        medlineplus = payload.get(
            "medlineplus"
        )

        if medlineplus:

            all_evidence.extend(
                extract_medlineplus_evidence(
                    medlineplus,
                    medicine,
                    query
                )
            )

    # ------------------------------------------------
    # REMOVE DUPLICATES
    # ------------------------------------------------

    all_evidence = remove_duplicate_evidence(
        all_evidence
    )

    # ------------------------------------------------
    # GROUP EVIDENCE
    # ------------------------------------------------

    grouped = group_evidence_by_effect(
        all_evidence
    )

    analyses = []

    for effect, items in grouped.items():

        analysis = analyze_effect(
            effect,
            items,
            query,
            medicine
        )

        analyses.append(
            analysis
        )

    # ------------------------------------------------
    # SUPPORTED / QUALIFIED
    # ------------------------------------------------

    supported = [
        result
        for result in analyses
        if result.get(
            "score",
            0.0
        ) >= GROUNDING_THRESHOLD
    ]

    qualified = [
        result
        for result in analyses
        if result.get(
            "score",
            0.0
        ) < GROUNDING_THRESHOLD
    ]

    # ------------------------------------------------
    # FINAL DECISION
    # ------------------------------------------------

    decision = (
        "ACCEPT"
        if supported
        else "QUALIFY"
    )

    # ------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------

    return {
        "query": query,

        "medicine": medicine,

        "threshold": GROUNDING_THRESHOLD,

        "evidence_items": all_evidence,

        "evidence_categories": analyses,

        "supported": supported,

        "qualified": qualified,

        "supported_count": len(
            supported
        ),

        "qualified_count": len(
            qualified
        ),

        "total_evidence_items": len(
            all_evidence
        ),

        "total_evidence_categories": len(
            analyses
        ),

        "decision": decision,
    }