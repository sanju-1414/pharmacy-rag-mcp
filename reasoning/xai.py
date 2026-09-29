def generate_xai_explanation(
    argumentation_result,
    safety_result,
    route,
    medicine,
    tools_used
):
    """
    Concise Explainable AI explanation.

    Shows:
    - evidence route
    - medicine
    - sources/tools
    - top two evidence arguments
    - evidence-support confidence
    - why the evidence supports the answer
    - clickable source links when available
    - final grounding decision

    Does not display:
    - safety status
    - evidence evaluation
    - evidence type
    - full evidence dump
    - drug interactions
    """

    if not argumentation_result:
        return (
            "### 🔍 Explainable AI\n\n"
            "No evidence was available for explanation."
        )

    supported = argumentation_result.get("supported", [])
    qualified = argumentation_result.get("qualified", [])

    all_results = supported + qualified

    if not all_results:
        return (
            "### 🔍 Explainable AI\n\n"
            "No evidence was available to explain the answer."
        )

    # Sort by evidence-support score
    ranked = sorted(
        all_results,
        key=lambda x: float(x.get("score", 0.0)),
        reverse=True
    )

    # Only the top two arguments
    top_arguments = ranked[:2]

    threshold = float(
        argumentation_result.get(
            "grounding_threshold",
            80.0
        )
    )

    decision = argumentation_result.get(
        "decision",
        "UNKNOWN"
    )

    lines = []

    lines.append("### 🔍 Explainable AI")
    lines.append("")
    lines.append("**Why did the system give this answer?**")
    lines.append("")

    lines.append(f"**Route:** {route}")
    lines.append(f"**Medicine:** {medicine}")

    if tools_used:
        lines.append(
            f"**Sources used:** {', '.join(tools_used)}"
        )

    lines.append("")

    for index, result in enumerate(top_arguments, start=1):

        score = float(
            result.get("score", 0.0)
        )

        items = result.get("items", [])

        if items:
            effect = items[0].get(
                "effect",
                "Reported evidence"
            )
        else:
            effect = "Reported evidence"

        # Collect unique sources
        sources = []
        source_urls = {}

        for item in items:

            source = item.get("source", "")

            if source and source not in sources:
                sources.append(source)

            # Support several possible URL field names
            url = (
                item.get("source_url")
                or item.get("url")
                or item.get("source_link")
            )

            if source and url:
                source_urls[source] = url

        # Determine explanation
        if score >= threshold:

            if len(sources) >= 2:
                reason = (
                    f"{effect.capitalize()} is directly supported "
                    f"by the retrieved evidence and corroborated "
                    f"by multiple sources."
                )
            elif len(sources) == 1:
                reason = (
                    f"{effect.capitalize()} is directly supported "
                    f"by the retrieved {sources[0]} evidence."
                )
            else:
                reason = (
                    f"{effect.capitalize()} is directly supported "
                    f"by the retrieved evidence."
                )

        else:

            reason = (
                f"{effect.capitalize()} was found in the evidence, "
                f"but its support did not fully meet the "
                f"{threshold:.0f}% grounding threshold."
            )

        lines.append(
            f"#### Argument {index}: {effect.capitalize()}"
        )

        lines.append(
            f"**Evidence-support confidence:** {score:.1f}%"
        )

        lines.append(
            f"**Why:** {reason}"
        )

        # Clickable source links
        if source_urls:

            lines.append("")
            lines.append("**Sources:**")

            for source, url in source_urls.items():

                lines.append(
                    f"- [{source} ↗]({url})"
                )

        elif sources:

            lines.append("")
            lines.append(
                "**Sources:** " +
                ", ".join(sources)
            )

        lines.append("")

    # Final decision
    lines.append("#### Decision")

    if decision == "ACCEPT":

        lines.append(
            f"**ACCEPT** — The supporting evidence met the "
            f"project-defined {threshold:.0f}% grounding threshold."
        )

    elif decision == "REJECT":

        lines.append(
            f"**REJECT** — The available evidence did not meet "
            f"the project-defined {threshold:.0f}% grounding threshold."
        )

    else:

        lines.append(
            f"**QUALIFIED** — Some evidence did not fully meet "
            f"the project-defined {threshold:.0f}% grounding threshold."
        )

    lines.append("")
    lines.append(
        "_Note: Evidence-support confidence is a project-defined "
        "grounding score, not medical probability or clinical certainty._"
    )

    return "\n".join(lines)