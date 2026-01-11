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
        
        st.sidebar.header("Photo Ops Suite")

        if "tool" not in st.session_state:
            st.session_state["tool"] = "timeline"
            st.markdown("### 🧰 Tools")

            def tool_button(label, key):
                active = st.session_state["tool"] == key
                if st.button(
                    label,
                    use_container_width=True
                ):
                    st.session_state["tool"] = key

            tool_button("📅 Timeline Builder", "timeline")
            tool_button("🌅 Sunset Checker", "sunset")
            tool_button("🖥️ Post-Processing Calculator", "post")

if __name__ == "__main__":
    main()