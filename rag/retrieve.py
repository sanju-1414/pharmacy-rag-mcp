from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

import re
import os


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CHROMA_FOLDER = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        "chroma_db"
    )
)


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

print("\nLoading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# ============================================================
# CONNECT TO CHROMADB
# ============================================================

vectorstore = Chroma(
    persist_directory=CHROMA_FOLDER,
    embedding_function=embeddings,
    collection_name="medicine_knowledge"
)


# ============================================================
# GET MEDICINES FROM UPLOADED DOCUMENTS
# ============================================================

def get_available_medicines():

    """
    Get medicine names dynamically from the source filenames
    stored in ChromaDB.

    No medicine names are hard-coded.
    """

    collection_data = vectorstore.get(
        include=["metadatas"]
    )

    metadatas = collection_data.get(
        "metadatas",
        []
    )

    medicines = set()

    for metadata in metadatas:

        if not metadata:
            continue

        source = metadata.get(
            "source",
            ""
        )

        if not source:
            continue

        filename = os.path.basename(
            source
        )

        medicine_name = os.path.splitext(
            filename
        )[0]

        medicine_name = (
            medicine_name
            .replace("_", " ")
            .replace("-", " ")
            .strip()
            .lower()
        )

        if medicine_name:

            medicines.add(
                medicine_name
            )

    return sorted(
        medicines,
        key=len,
        reverse=True
    )


# ============================================================
# DETECT MEDICINE
# ============================================================

def detect_medicine(query):

    """
    Detect medicine only from medicines available in the
    uploaded/indexed documents.
    """

    query_lower = query.lower().strip()

    available_medicines = (
        get_available_medicines()
    )

    for medicine in available_medicines:

        pattern = (
            r"\b"
            + re.escape(medicine)
            + r"\b"
        )

        if re.search(
            pattern,
            query_lower
        ):

            return medicine

    return None


# ============================================================
# DETECT QUESTION INTENT
# ============================================================

def detect_intent(query):

    """
    Detect the information type requested by the user.

    This does NOT use hard-coded medicine names.
    It only identifies the type of information being requested.
    """

    query_lower = query.lower()


    # ========================================================
    # ADVERSE REACTIONS / SIDE EFFECTS
    # ========================================================

    adverse_patterns = [

        r"\badverse reaction",
        r"\badverse reactions",
        r"\bside effect",
        r"\bside effects",
        r"\bunwanted effect",
        r"\bunwanted effects",
        r"\breaction to",
        r"\breactions to"
    ]

    for pattern in adverse_patterns:

        if re.search(
            pattern,
            query_lower
        ):

            return "ADVERSE_REACTIONS"


    # ========================================================
    # WARNINGS
    # ========================================================

    warning_patterns = [

        r"\bwarning",
        r"\bwarnings",
        r"\bwhat should i be careful about",
        r"\bwhat should i watch out for"
    ]

    for pattern in warning_patterns:

        if re.search(
            pattern,
            query_lower
        ):

            return "WARNINGS"


    # ========================================================
    # CONTRAINDICATIONS
    # ========================================================

    contraindication_patterns = [

        r"\bcontraindication",
        r"\bcontraindications",
        r"\bwho should not take",
        r"\bwho should not use",
        r"\bwhen should .* not take",
        r"\bwhen should .* not use"
    ]

    for pattern in contraindication_patterns:

        if re.search(
            pattern,
            query_lower
        ):

            return "CONTRAINDICATIONS"


    # ========================================================
    # INTERACTIONS
    # ========================================================

    interaction_patterns = [

        r"\binteraction",
        r"\binteractions",
        r"\binteract with",
        r"\bdrug interaction",
        r"\bdrug interactions"
    ]

    for pattern in interaction_patterns:

        if re.search(
            pattern,
            query_lower
        ):

            return "INTERACTIONS"


    # ========================================================
    # OVERDOSE
    # ========================================================

    overdose_patterns = [

        r"\boverdose",
        r"\boverdosing",
        r"\btook too much",
        r"\btaken too much",
        r"\btoo much"
    ]

    for pattern in overdose_patterns:

        if re.search(
            pattern,
            query_lower
        ):

            return "OVERDOSE"


    # ========================================================
    # USES
    # ========================================================

    use_patterns = [

        r"\buses\b",
        r"\buse of",
        r"\bused for",
        r"\bwhat is .* used for",
        r"\bwhat does .* treat",
        r"\bwhat is .* for"
    ]

    for pattern in use_patterns:

        if re.search(
            pattern,
            query_lower
        ):

            return "USES"


    # ========================================================
    # PRECAUTIONS
    # ========================================================

    precaution_patterns = [

        r"\bprecaution",
        r"\bprecautions",
        r"\bcareful with",
        r"\bcareful when taking"
    ]

    for pattern in precaution_patterns:

        if re.search(
            pattern,
            query_lower
        ):

            return "PRECAUTIONS"


    # ========================================================
    # GENERAL INFORMATION
    # ========================================================

    return "GENERAL"


# ============================================================
# INTENT KEYWORDS
# ============================================================

INTENT_KEYWORDS = {

    "ADVERSE_REACTIONS": [
        "adverse reaction",
        "adverse reactions",
        "side effect",
        "side effects",
        "unwanted effect",
        "unwanted effects",
        "reaction",
        "reactions"
    ],

    "WARNINGS": [
        "warning",
        "warnings"
    ],

    "CONTRAINDICATIONS": [
        "contraindication",
        "contraindications",
        "should not take",
        "should not use"
    ],

    "INTERACTIONS": [
        "interaction",
        "interactions",
        "interact"
    ],

    "OVERDOSE": [
        "overdose",
        "overdosing",
        "too much",
        "took too much"
    ],

    "USES": [
        "uses",
        "use",
        "used for",
        "treat",
        "treats"
    ],

    "PRECAUTIONS": [
        "precaution",
        "precautions",
        "careful"
    ]
}


# ============================================================
# CHECK WHETHER CHUNK MATCHES INTENT
# ============================================================

def chunk_matches_intent(
    text,
    intent
):

    """
    Determine whether retrieved evidence contains terminology
    relevant to the detected question intent.
    """

    if intent == "GENERAL":

        return True


    text_lower = text.lower()


    keywords = INTENT_KEYWORDS.get(
        intent,
        []
    )


    for keyword in keywords:

        if keyword in text_lower:

            return True


    return False


# ============================================================
# RETRIEVE DOCUMENTS
# ============================================================

def retrieve_documents(
    query,
    k=3
):

    detected_medicine = detect_medicine(
        query
    )

    intent = detect_intent(
        query
    )


    # ========================================================
    # RETRIEVE MORE CANDIDATES
    # ========================================================

    raw_results = (
        vectorstore
        .similarity_search_with_score(
            query,
            k=k * 5
        )
    )


    seen_chunks = set()


    # ========================================================
    # MEDICINE-SPECIFIC RETRIEVAL
    # ========================================================

    if detected_medicine:

        medicine_results = []


        for doc, score in raw_results:

            source = str(
                doc.metadata.get(
                    "source",
                    ""
                )
            ).lower()


            source_without_extension = (
                os.path.splitext(
                    os.path.basename(source)
                )[0]
                .replace("_", " ")
                .replace("-", " ")
                .strip()
            )


            chunk_text = (
                doc.page_content.strip()
            )


            # ------------------------------------------------
            # REMOVE EXACT DUPLICATES
            # ------------------------------------------------

            if chunk_text in seen_chunks:

                continue


            seen_chunks.add(
                chunk_text
            )


            # ------------------------------------------------
            # MEDICINE FILTER
            # ------------------------------------------------

            if source_without_extension != (
                detected_medicine
            ):

                continue


            medicine_results.append(
                (doc, score)
            )


        # ====================================================
        # FIRST TRY: INTENT-SPECIFIC EVIDENCE
        # ====================================================

        intent_results = []


        for doc, score in medicine_results:

            if chunk_matches_intent(
                doc.page_content,
                intent
            ):

                intent_results.append(
                    (doc, score)
                )


        if intent_results:

            return intent_results[:k]


        # ====================================================
        # FALLBACK:
        # MEDICINE-SPECIFIC RESULTS
        # ====================================================

        return medicine_results[:k]


    # ========================================================
    # GENERAL QUERY
    # ========================================================

    unique_results = []


    for doc, score in raw_results:

        chunk_text = (
            doc.page_content.strip()
        )


        if chunk_text in seen_chunks:

            continue


        seen_chunks.add(
            chunk_text
        )


        unique_results.append(
            (doc, score)
        )


        if len(unique_results) >= k:

            break


    return unique_results


# ============================================================
# CHECK RAG SUFFICIENCY
# ============================================================

def check_rag_sufficiency(
    results,
    query,
    threshold=1.0
):

    """
    RAG is sufficient when:

    1. Results exist.
    2. Medicine is detected from uploaded documents.
    3. Results belong to that medicine.
    4. Best similarity distance is within threshold.
    """


    if not results:

        return False


    detected_medicine = detect_medicine(
        query
    )


    if detected_medicine is None:

        return False


    medicine_results = []


    for doc, score in results:

        source = str(
            doc.metadata.get(
                "source",
                ""
            )
        ).lower()


        source_without_extension = (
            os.path.splitext(
                os.path.basename(source)
            )[0]
            .replace("_", " ")
            .replace("-", " ")
            .strip()
        )


        if source_without_extension == (
            detected_medicine
        ):

            medicine_results.append(
                (doc, score)
            )


    if not medicine_results:

        return False


    best_score = min(
        score
        for doc, score in medicine_results
    )


    if best_score > threshold:

        return False


    return True


# ============================================================
# TEST RETRIEVAL
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # SHOW DOCUMENT MEDICINES
    # ========================================================

    available_medicines = (
        get_available_medicines()
    )


    print(
        "\n========== MEDICINES FOUND IN UPLOADED DOCUMENTS ==========\n"
    )


    for medicine in available_medicines:

        print(
            f"- {medicine}"
        )


    # ========================================================
    # GET QUESTION
    # ========================================================

    question = input(
        "\nEnter your question: "
    )


    # ========================================================
    # MEDICINE DETECTION
    # ========================================================

    detected = detect_medicine(
        question
    )


    print(
        "\n========== MEDICINE DETECTION ==========\n"
    )


    print(
        f"Detected medicine: {detected}"
    )


    # ========================================================
    # INTENT DETECTION
    # ========================================================

    intent = detect_intent(
        question
    )


    print(
        "\n========== QUESTION INTENT ==========\n"
    )


    print(
        f"Detected intent: {intent}"
    )


    # ========================================================
    # RETRIEVAL
    # ========================================================

    results = retrieve_documents(
        question
    )


    print(
        "\n========== RAG RESULTS ==========\n"
    )


    if not results:

        print(
            "No medicine-specific RAG results found."
        )

    else:

        for i, (doc, score) in enumerate(
            results,
            1
        ):

            print(
                f"--- RESULT {i} ---"
            )


            print(
                f"Source: "
                f"{doc.metadata.get('source')}"
            )


            print(
                f"Page: "
                f"{doc.metadata.get('page')}"
            )


            print(
                f"Extraction method: "
                f"{doc.metadata.get('extraction_method', 'Not available')}"
            )


            print(
                f"Similarity distance: {score}"
            )


            print(
                "\nText:"
            )


            print(
                doc.page_content[:1500]
            )


            print(
                "\n" + "=" * 60
            )


    # ========================================================
    # RAG SUFFICIENCY
    # ========================================================

    rag_sufficient = (
        check_rag_sufficiency(
            results,
            question
        )
    )


    print(
        "\n========== RAG SUFFICIENCY =========="
    )


    if rag_sufficient:

        print(
            "✅ RAG SUFFICIENT"
        )

        print(
            "Retrieved evidence belongs "
            "to the requested medicine."
        )

    else:

        print(
            "❌ RAG INSUFFICIENT"
        )

        print(
            "External MCP tools may be required."
        )