from __future__ import annotations

import streamlit as st

from tools.timeline_builder_ui import render_timeline_builder
from tools.sunset_checker import render_sunset_checker
from tools.post_processing_calculator import render_post_processing_calculator
from tools.codb_calculator import render_wedding_codb_calculator
from tools.photographer_score import render_wedding_photographer_score
from tools.finance_dashboard import render_finance_dashboard  # <-- use the real name

st.set_page_config(
    page_title="Photo Ops Suite | Caitee Smith Photography",
    page_icon="assets/favicon.png",
    layout="wide",
)

st.markdown(
    """
    <style>
        div[data-testid="stExpander"] {
            border-radius: 16px;
            border: 1px solid #E6E9ED;
            background-color: #F1F3F5;
        }

        button[kind="primary"] {
            border-radius: 999px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

PHOTO_OPS_TOOLS = [
    "Timeline Builder",
    "Sunset & Golden Hour",
    "Post-Processing Calculator",
    "CODB Calculator",
    "What's Your Wedding Photographer Score?",
]

PERSONAL_TOOLS = [
    "Personal Finance Dashboard",
]


def main():
    with st.sidebar:
        st.image("assets/logo.png", width=125)

        st.markdown(
            """
            <style>
            .brand-link { color:#2C2C2C !important; font-weight:400; }
            .brand-link:hover { text-decoration: underline !important; }
            </style>

            <a class="brand-link" href="https://www.caiteesmithphotography.com" target="_blank">
            caiteesmithphotography.com
            </a>
            """,
            unsafe_allow_html=True,
        )

        st.header("Photo Ops Suite")

        section = st.radio(
            "Section",
            ["Wedding Tools", "Personal Tools"],
            index=0,
            key="sidebar_section",
        )

        if section == "Wedding Tools":
            tool = st.radio("Choose a tool", PHOTO_OPS_TOOLS, index=0, key="sidebar_wedding_tool")
        else:
            tool = st.radio("Choose a tool", PERSONAL_TOOLS, index=0, key="sidebar_personal_tool")

    # Routing
    if tool == "Timeline Builder":
        render_timeline_builder()
    elif tool == "Sunset & Golden Hour":
        render_sunset_checker()
    elif tool == "Post-Processing Calculator":
        render_post_processing_calculator()
    elif tool == "CODB Calculator":
        render_wedding_codb_calculator()
    elif tool == "What's Your Wedding Photographer Score?":
        render_wedding_photographer_score()
    elif tool == "Personal Finance Dashboard":
        render_finance_dashboard()


if __name__ == "__main__":
    main()