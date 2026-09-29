import streamlit as st

from reasoning.pipeline import run_pipeline


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Pharmacy AI Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# PAGE STYLING
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #d6e3ef;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    div[data-baseweb="input"] {
        background-color: white;
        border-radius: 10px;
    }

    .stButton > button {
        border-radius: 10px;
        height: 45px;
        font-weight: 600;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# HEADER
# =========================================================

st.title("💊 Pharmacy AI Assistant")

st.caption(
    "Evidence-based medication information powered by "
    "RAG, external medical APIs, and Explainable AI."
)

st.divider()


# =========================================================
# FEATURE CARDS
# =========================================================

col1, col2 = st.columns(2)


with col1:

    with st.container(border=True):

        st.markdown("## 📚")

        st.subheader("Evidence Based")

        st.write(
            "Answers are grounded in retrieved medicine "
            "information and trusted external sources."
        )

        st.info("📖 Trusted evidence")


with col2:

    with st.container(border=True):

        st.markdown("## 🔍")

        st.subheader("Explainable AI")

        st.write(
            "Understand the evidence, sources, and reasoning "
            "behind the response."
        )

        st.success("✓ Transparent reasoning")


st.divider()


# =========================================================
# QUESTION SECTION
# =========================================================

st.subheader("💬 Ask your medication question")

st.caption(
    "Ask about side effects, warnings, precautions, "
    "or other medication information."
)


question = st.text_input(
    "Medication question",
    placeholder=(
        "Example: What are the side effects of doxycycline?"
    ),
    label_visibility="collapsed"
)


# =========================================================
# ANALYZE BUTTON
# =========================================================

if st.button(
    "🔎 Analyze Question",
    use_container_width=True
):

    if not question.strip():

        st.warning("Please enter a question.")

    else:

        with st.spinner(
            "🔬 Analyzing evidence and generating response..."
        ):

            try:

                result = run_pipeline(question)

            except Exception as e:

                st.error(
                    "An error occurred while processing the question."
                )

                st.exception(e)

                st.stop()


        # =================================================
        # GET RESULTS FROM PIPELINE
        # =================================================

        answer = result.get(
            "answer",
            "No answer was generated."
        )

        xai_explanation = result.get(
            "xai",
            "No explainable AI information is available."
        )

        route = result.get(
            "route",
            "Unknown"
        )

        medicine = result.get(
            "medicine",
            "Not identified"
        )

        tools_used = result.get(
            "tools_used",
            []
        )


        # =================================================
        # FINAL ANSWER
        # =================================================

        st.divider()

        st.subheader("💬 Final Answer")

        with st.container(border=True):

            st.markdown("### 💊 Medication Information")

            st.markdown(answer)


        # =================================================
        # ANALYSIS INFORMATION
        # =================================================

        st.divider()

        st.subheader("🔬 Analysis Information")

        info_col1, info_col2 = st.columns(2)


        # ---------------- Evidence Route ------------------

        with info_col1:

            st.metric(
                "Evidence Route",
                str(route).upper()
            )


        # ---------------- Medicine -------------------------

        with info_col2:

            st.metric(
                "Medicine",
                str(medicine)
            )


        # =================================================
        # TOOLS / SOURCES
        # =================================================

        if tools_used:

            st.write("**Sources / Tools Used:**")

            source_cols = st.columns(len(tools_used))

            for i, tool in enumerate(tools_used):

                with source_cols[i]:

                    st.info(str(tool))


        # =================================================
        # XAI EXPLANATION
        # =================================================

        st.divider()

        st.subheader("🔍 Explainable AI")

        with st.expander(
            "🧠 View how the answer was generated",
            expanded=True
        ):

            if isinstance(xai_explanation, str):

                # IMPORTANT:
                # st.markdown() makes the source URLs
                # inside the XAI clickable.
                st.markdown(xai_explanation)

            else:

                st.write(xai_explanation)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "💊 Pharmacy AI Assistant  •  "
    "RAG  •  MCP  •  Explainable AI"
)

st.caption(
    "This system provides evidence-based medication information "
    "and is not a substitute for professional medical advice."
)