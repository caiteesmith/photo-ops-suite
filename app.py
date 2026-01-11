from __future__ import annotations
from tools.timeline_builder_ui import render_timeline_builder
from tools.sunset_checker import render_sunset_checker
from tools.post_processing_calculator import render_post_processing_calculator

import streamlit as st

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

def main():
    with st.sidebar:
        st.image("assets/csp-logo-lilac.png", width=150)
        st.markdown("[caiteesmithphotography.com](https://www.caiteesmithphotography.com)")
        st.sidebar.header("Photo Ops Suite")
        tool = st.sidebar.radio(
            "Choose a tool",
            ["Timeline Builder", "Sunset & Golden Hour", "Post-Processing Calculator"],
            index=0,
        )

    if tool == "Timeline Builder":
        render_timeline_builder()
    elif tool == "Sunset & Golden Hour":
        render_sunset_checker()
    elif tool == "Post-Processing Calculator":
        render_post_processing_calculator()

if __name__ == "__main__":
    main()