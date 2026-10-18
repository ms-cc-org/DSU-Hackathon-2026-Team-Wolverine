"""DroughtLens: See Drought Coming. Plan Ahead.

The farmer-facing app for Nebraska and Iowa corn and soybean farmers. It is built on Team Wolverine's Drought Category
Reality Check (see wolverine/ and wolverine_app.py) and on every dataset in data/.

Run:  streamlit run dashboard_app.py
"""
from pathlib import Path

import streamlit as st
from PIL import Image

st.set_page_config(page_title="DroughtLens", page_icon=Image.open(Path(__file__).parent / "assets" / "logo" / "favicon-64.png"), layout="wide")

from droughtlens import theme  # noqa: E402
from droughtlens.views import advisor, common, fields, login, outlook, overview, plan, trust  # noqa: E402

PAGES = {"overview": overview, "outlook": outlook, "fields": fields, "plan": plan, "advisor": advisor, "trust": trust, "login": login}

theme.apply_theme()
common.init_state()
common.navbar()

page = st.session_state.page
if page in common.GATED and not common.signed_in():
    st.session_state.next_page = page
    page = "login"
try:
    PAGES[page].show()
except Exception as exc:  # a failed page should read as a message, not a stack trace
    st.error("Something went wrong loading this page. Your saved fields and plans are safe. Try another page, or refresh.")
    st.caption(f"Technical detail for the team: {type(exc).__name__}: {exc}")
common.footer()
