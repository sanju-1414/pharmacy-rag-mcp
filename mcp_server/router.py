import sys
import os
import re
import asyncio


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

RAG_DIR = os.path.join(
    PROJECT_ROOT,
    "rag"
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if RAG_DIR not in sys.path:
    sys.path.insert(0, RAG_DIR)


# ============================================================
# RAG IMPORT
# ============================================================

from rag.retrieve import (
    retrieve_documents,
    check_rag_sufficiency
)


# ============================================================
# MEDICINE DETECTION USING RxNorm
# ============================================================

def detect_medicine_for_mcp(query: str):

    words = re.findall(
        r"[A-Za-z][A-Za-z-]*",
        query
    )

    candidates = []

    # Single words
    for word in words:

        candidates.append(
            word
        )

    # Two-word medicine names
    for i in range(
        len(words) - 1
    ):

        candidates.append(
            words[i] + " " + words[i + 1]
        )

    ignored_words = {
        "what",
        "are",
        "the",
        "side",
        "effects",
        "of",
        "is",
        "for",
        "about",
        "can",
        "i",
        "take",
        "does",
        "do",
        "with",
        "and",
        "my",
        "doctor",
        "prescribed",
        "medicine",
        "drug",
        "drugs",
        "should",
        "know",
        "worried",
        "warnings",
        "warning",
        "precautions",
        "contraindications",
        "interactions",
        "interaction",
        "used",
        "use",
        "overdose"
    }

    import requests

    for candidate in candidates:

        candidate_lower = (
            candidate.lower()
        )

        if candidate_lower in ignored_words:
            continue

        try:

            url = (
                "https://rxnav.nlm.nih.gov/"
                "REST/rxcui.json"
            )

            response = requests.get(
                url,
                params={
                    "name": candidate
                },
                timeout=10
            )

            if response.status_code != 200:
                continue

            data = response.json()

            rxnorm_ids = (
                data
                .get("idGroup", {})
                .get("rxnormId", [])
            )

            if rxnorm_ids:

               return {
    "medicine": candidate_lower,
    "rxcui": rxnorm_ids[0]
}

        except Exception:

            continue

    return None


# ============================================================
# MCP SERVER CALL
# ============================================================

def call_mcp(medicine: str):

    server_path = os.path.join(
        PROJECT_ROOT,
        "mcp_server",
        "server.py"
    )

    try:

        from mcp import (
            ClientSession,
            StdioServerParameters
        )

        from mcp.client.stdio import (
            stdio_client
        )

        server_params = (
            StdioServerParameters(
                command=sys.executable,
                args=[server_path]
            )
        )

        async def run_mcp():

            async with stdio_client(
                server_params
            ) as (
                read_stream,
                write_stream
            ):

                async with ClientSession(
                    read_stream,
                    write_stream
                ) as session:

                    await session.initialize()

                    result = (
                        await session.call_tool(
                            "get_drug_information",
                            {
                                "medicine": medicine
                            }
                        )
                    )

                    return result

        result = asyncio.run(
            run_mcp()
        )

        # ====================================================
        # CONVERT MCP RESULT TO PYTHON DICTIONARY
        # ====================================================

        if hasattr(
            result,
            "content"
        ):

            for item in result.content:

                if hasattr(
                    item,
                    "text"
                ):

                    text = item.text

                    if text:

                        import json

                        try:

                            return json.loads(
                                text
                            )

                        except json.JSONDecodeError:

                            return {
                                "raw_text": text
                            }

        return {
            "raw_result": str(
                result
            )
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# ============================================================
# RAG DISTANCE
# ============================================================

def get_top_rag_distance(
    rag_results
):

    if not rag_results:
        return None

    first_result = (
        rag_results[0]
    )

    if isinstance(
        first_result,
        tuple
    ):

        for item in first_result:

            if isinstance(
                item,
                (int, float)
            ):

                return item

        return None

    if isinstance(
        first_result,
        dict
    ):

        return first_result.get(
            "distance"
        )

    return None


# ============================================================
# QUERY ROUTER
# ============================================================

def route_query(query: str):

    rag_results = (
        retrieve_documents(
            query,
            k=3
        )
    )

    rag_sufficient = (
        check_rag_sufficiency(
            rag_results,
            query
        )
    )

    if rag_sufficient:

        return {
            "route": "RAG",
            "query": query,
            "rag_results": rag_results,
            "mcp_result": None,
            "medicine": None,
            "rxcui": None
        }

    medicine, rxcui = (
        detect_medicine_for_mcp(
            query
        )
    )

    if not medicine:

        return {
            "route": "MCP",
            "query": query,
            "rag_results": rag_results,
            "mcp_result": None,
            "medicine": None,
            "rxcui": None,
            "error": (
                "RAG was insufficient and "
                "no medicine could be validated "
                "through RxNorm."
            )
        }

    mcp_result = call_mcp(
        medicine
    )

    return {
        "route": "MCP",
        "query": query,
        "rag_results": rag_results,
        "mcp_result": mcp_result,
        "medicine": medicine,
        "rxcui": rxcui
    }


# ============================================================
# TERMINAL TEST
# ============================================================

if __name__ == "__main__":

    question = input(
        "Enter your question: "
    ).strip()

    result = route_query(
        question
    )

    print(
        "\n========== ROUTING RESULT =========="
    )

    print(
        f"Question: {question}"
    )

    print(
        f"Route: {result.get('route')}"
    )

    top_distance = (
        get_top_rag_distance(
            result.get(
                "rag_results"
            )
        )
    )

    print(
        f"Top RAG result score: "
        f"{top_distance}"
    )

    print(
        "\n========== MCP CALL =========="
    )

    print(
        f"Detected medicine: "
        f"{result.get('medicine')}"
    )

    print(
        f"RxCUI: "
        f"{result.get('rxcui')}"
    )

    print(
        "\n========== MCP RESULT =========="
    )

    print(
        result.get(
            "mcp_result"
        )
    )

    if result.get("error"):

        print(
            "\n========== ERROR =========="
        )

        print(
            result.get(
                "error"
            )
        )