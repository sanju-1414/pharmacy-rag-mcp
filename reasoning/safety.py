import re


def run_safety_checks(question, evidence):

    question_lower = question.lower()
    evidence_lower = evidence.lower()

    flags = []

    # ========================================================
    # ALLERGY
    # ========================================================

    allergy_patterns = [
        r"allergic to",
        r"allergy to",
        r"allergic reaction",
        r"allergy with"
    ]

    if any(
        re.search(pattern, question_lower)
        for pattern in allergy_patterns
    ):

        flags.append({
            "type": "ALLERGY",
            "severity": "HIGH",
            "category": "USER_SPECIFIC",
            "message": (
                "The user has mentioned a possible drug allergy "
                "or allergic reaction."
            )
        })

    # ========================================================
    # DRUG INTERACTION
    # ========================================================

    interaction_patterns = [
        r"interact",
        r"interaction",
        r"taking .* with",
        r"take .* together"
    ]

    if any(
        re.search(pattern, question_lower)
        for pattern in interaction_patterns
    ):

        flags.append({
            "type": "DRUG_INTERACTION",
            "severity": "HIGH",
            "category": "USER_SPECIFIC",
            "message": (
                "The question involves a possible drug-drug "
                "interaction."
            )
        })

    # ========================================================
    # OVERDOSE
    # ========================================================

    overdose_patterns = [
        r"overdose",
        r"too much",
        r"took too many",
        r"excessive amount"
    ]

    if any(
        re.search(pattern, question_lower)
        for pattern in overdose_patterns
    ):

        flags.append({
            "type": "OVERDOSE",
            "severity": "CRITICAL",
            "category": "USER_SPECIFIC",
            "message": (
                "Possible overdose or excessive medicine use "
                "has been mentioned."
            )
        })

    # ========================================================
    # PREGNANCY / BREASTFEEDING
    # ========================================================

    pregnancy_patterns = [
        r"pregnant",
        r"pregnancy",
        r"breastfeeding",
        r"breast feeding"
    ]

    if any(
        re.search(pattern, question_lower)
        for pattern in pregnancy_patterns
    ):

        flags.append({
            "type": "PREGNANCY_BREASTFEEDING",
            "severity": "HIGH",
            "category": "USER_SPECIFIC",
            "message": (
                "Pregnancy or breastfeeding has been mentioned."
            )
        })

    # ========================================================
    # KIDNEY
    # ========================================================

    kidney_patterns = [
        r"kidney disease",
        r"kidney problem",
        r"renal disease",
        r"renal impairment",
        r"kidney failure",
        r"history of kidney",
        r"history of renal"
    ]

    if any(
        re.search(pattern, question_lower)
        for pattern in kidney_patterns
    ):

        flags.append({
            "type": "KIDNEY_PRECAUTION",
            "severity": "HIGH",
            "category": "USER_SPECIFIC",
            "message": (
                "Kidney-related disease or impairment "
                "has been mentioned."
            )
        })

    # ========================================================
    # LIVER
    # ========================================================

    liver_patterns = [
        r"liver disease",
        r"liver problem",
        r"hepatic disease",
        r"hepatic impairment",
        r"liver failure",
        r"history of liver",
        r"history of hepatic"
    ]

    if any(
        re.search(pattern, question_lower)
        for pattern in liver_patterns
    ):

        flags.append({
            "type": "LIVER_PRECAUTION",
            "severity": "HIGH",
            "category": "USER_SPECIFIC",
            "message": (
                "Liver-related disease or impairment "
                "has been mentioned."
            )
        })

    # ========================================================
    # STOMACH / ULCER
    # ========================================================

    stomach_patterns = [
        r"stomach ulcer",
        r"stomach ulcers",
        r"gastric ulcer",
        r"gastric ulcers",
        r"peptic ulcer",
        r"peptic ulcers",
        r"history of ulcer",
        r"history of ulcers",
        r"history of stomach problem",
        r"history of stomach problems",
        r"stomach bleeding",
        r"gastrointestinal bleeding",
        r"gi bleeding"
    ]

    if any(
        re.search(pattern, question_lower)
        for pattern in stomach_patterns
    ):

        flags.append({
            "type": "STOMACH_ULCER_RISK",
            "severity": "HIGH",
            "category": "USER_SPECIFIC",
            "message": (
                "The user has mentioned a history of stomach "
                "ulcers or another stomach-related risk factor."
            )
        })

    # ========================================================
    # RED FLAGS
    # ========================================================

    red_flag_patterns = [
        r"difficulty breathing",
        r"trouble breathing",
        r"chest pain",
        r"fainting",
        r"unconscious",
        r"seizure",
        r"confusion",
        r"severe bleeding",
        r"vomiting blood",
        r"blood in vomit",
        r"bloody stools",
        r"black stools"
    ]

    if any(
        re.search(pattern, question_lower)
        for pattern in red_flag_patterns
    ):

        flags.append({
            "type": "RED_FLAG",
            "severity": "CRITICAL",
            "category": "USER_SPECIFIC",
            "message": (
                "The question contains a symptom that may "
                "require urgent medical evaluation."
            )
        })

    # ========================================================
    # EVIDENCE-BASED CONTRAINDICATION INFORMATION
    # ========================================================

    contraindication_terms = [
        "contraindicated",
        "contraindication",
        "do not use",
        "should not be used"
    ]

    if any(
        term in evidence_lower
        for term in contraindication_terms
    ):

        flags.append({
            "type": "CONTRAINDICATION_INFORMATION",
            "severity": "INFORMATION",
            "category": "EVIDENCE",
            "message": (
                "The retrieved medicine evidence contains "
                "contraindication or do-not-use information."
            )
        })

    # ========================================================
    # EVIDENCE WARNINGS
    # ========================================================

    if "warnings" in evidence_lower:

        flags.append({
            "type": "WARNING_INFORMATION",
            "severity": "INFORMATION",
            "category": "EVIDENCE",
            "message": (
                "The retrieved medicine evidence contains "
                "warning information."
            )
        })

    return flags


# ============================================================
# SAFETY SUMMARY
# ============================================================

def summarize_safety(flags):

    if not flags:

        return {
            "overall_level": "NO_FLAG",
            "flags": []
        }

    severity_order = {
        "NO_FLAG": 0,
        "INFORMATION": 0,
        "MEDIUM": 1,
        "HIGH": 2,
        "CRITICAL": 3
    }

    highest = "NO_FLAG"

    for flag in flags:

        if flag["category"] != "USER_SPECIFIC":
            continue

        severity = flag["severity"]

        if (
            severity_order[severity]
            >
            severity_order[highest]
        ):

            highest = severity

    return {
        "overall_level": highest,
        "flags": flags
    }