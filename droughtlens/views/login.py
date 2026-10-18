"""Sign-in. Demo accounts only; this gates the demo and is not real security."""
import streamlit as st

from droughtlens import logo
from droughtlens.theme import html, photo
from droughtlens.views.common import DEMO_USERS, goto


def _sign_in():
    ss = st.session_state
    user, password = ss.get("login_user", "").strip().lower(), ss.get("login_password", "")
    if password and DEMO_USERS.get(user) == password:
        ss.user = user
        ss.login_error = False
        ss.page = ss.pop("next_page", "fields")
    else:
        ss.login_error = True


def show():
    left, right = st.columns([1, 1], gap="large")
    with left:
        html(f"<div style='margin:1.5rem 0 .5rem'>{logo.horizontal(height=58)}</div>")
        html("<div class='sec' style='margin-top:1rem'><div class='eyebrow'>Sign in</div><h2>Welcome back</h2>"
             "<p class='lead'>Sign in to see your county's drought record, your fields and your plan.</p></div>")
        with st.form("login"):
            st.text_input("Username", key="login_user")
            st.text_input("Password", type="password", key="login_password")
            st.form_submit_button("Sign in", type="primary", width="stretch", on_click=_sign_in)
        if st.session_state.get("login_error"):
            st.error("That username or password does not match. Check them and try again.")
        st.markdown("<span class='small'>Team demo: username <b>demo</b>, password <b>demo</b>.</span>", unsafe_allow_html=True)
        st.button("Back to overview", on_click=goto, args=("overview",))
    with right:
        html(f"<div class='photo-band' style='height:480px;margin-top:1.5rem;background-image:url(\"{photo('hero.jpg')}\")'></div>"
             "<div class='small'>Checking soil moisture in a soybean field. USDA photo, public domain.</div>")
