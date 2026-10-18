"""Agricultural Advisor: a chat that answers from DroughtLens's data, with findings kept apart from guidance."""
from html import escape

import streamlit as st

from droughtlens import advisor, data, farm
from droughtlens.theme import callout, html
from droughtlens.views.common import context, goto, user_record


def _inline(text):
    """Escape, then turn **bold** into <b> (raw HTML blocks are not parsed as markdown)."""
    out, bold = "", False
    for chunk in escape(text).split("**"):
        out += f"<b>{chunk}</b>" if bold else chunk
        bold = not bold
    return out


def _list(items):
    return "<br>".join(f"• {_inline(i)}" for i in items)


def ask(question):
    """Button and chat callback: answer from the data and add both messages to the conversation."""
    ss = st.session_state
    record, _ = user_record()
    ctx = context(record)
    topic = advisor.route(question)
    ans = advisor.answer(topic, ctx)
    if ans["action"] == "plan":
        ans = _draft_plan(ctx, record, ans)
    ss.chat.append({"role": "user", "text": question})
    ss.chat.append({"role": "assistant", "answer": ans, "topic": topic, "context": f"{ctx['county']}, {data.STATE_NAMES[ctx['state']]} · {data.CROP_NAMES[ctx['crop']]}"})


def _draft_plan(ctx, record, ans):
    """Create and save a plan. With no saved field, save one from the current selection and say so."""
    field = ctx["field"]
    if field is None:
        name = f"{ctx['county'].replace(' County', '')} farm"
        field = next((f for f in record["fields"] if f["name"] == name), None)
        if field is None:
            field = farm.new_field(name, ctx["fips"], [ctx["crop"]])
            record["fields"].append(field)
            ans["notes"].append(f"You had no saved field for this county, so I saved one called “{name}” from your current selection. Add acres, stage and water under My Fields to sharpen the plan.")
    try:
        plan = farm.new_plan(field)
        record["plans"].append(plan)
        farm.save_user(ctx["user"], record)
    except farm.StoreError as exc:
        return {"findings": [], "guidance": [], "notes": [f"I could not save the plan: {exc}"], "action": None}
    st.session_state.active_field, st.session_state.current_plan = field["id"], plan["id"]
    ans["findings"] = [f"I drafted a plan for **{field['name']}** from the data and saved it. Each line is tagged Data or General guidance, and you can edit it in My Farm Plan."]
    ans["action"] = "open_plan"
    return ans


def render(msg, i):
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["text"])
        return
    a = msg["answer"]
    with st.chat_message("assistant"):
        if a["findings"]:
            callout("<span class='tagline'>Data-backed findings</span>" + _list(a["findings"]), "finding")
        if a["guidance"]:
            callout("<span class='tagline'>General guidance</span>" + _list(a["guidance"]) + "<br><span class='small'>Common practice, not derived from our data.</span>", "guidance")
        if a["notes"]:
            callout("<span class='tagline'>Good to know</span>" + _list(a["notes"]), "warning")
        if a["action"] == "open_plan":
            st.button("Open my farm plan", key=f"open_plan_{i}", type="primary", on_click=goto, args=("plan",))
        st.caption(f"Based on {msg['context']}. From DroughtLens data using fixed rules. Not an official drought assessment or a weather forecast.")


def show():
    ss = st.session_state
    record, store_error = user_record()
    ctx = context(record)
    html("<div class='eyebrow'>Agricultural Advisor</div>")
    html("<h2 style='margin-top:.2rem'>Ask about drought on your farm</h2>")
    where = f"{ctx['county']}, {data.STATE_NAMES[ctx['state']]} · {data.CROP_NAMES[ctx['crop']]}" + (f" · field “{ctx['field']['name']}”" if ctx["field"] else "")
    st.caption(f"The Advisor is using: {where}. Change the county or crop on the Drought Outlook tab, or pick a field under My Fields.")
    if store_error:
        st.warning(store_error)

    with st.chat_message("assistant"):
        st.write(advisor.INTRO)
        st.caption(advisor.SCOPE_NOTE)
    st.markdown("**Try asking**")
    cols = st.columns(len(advisor.SUGGESTED))
    for i, (col, q) in enumerate(zip(cols, advisor.SUGGESTED)):
        col.button(q, key=f"sugg_{i}", on_click=ask, args=(q,), width="stretch")

    for i, msg in enumerate(ss.chat):
        render(msg, i)
    typed = st.chat_input("Ask about drought risk, your crops, or your plan")
    if typed:
        ask(typed)
        st.rerun()
    if ss.chat and st.button("Clear conversation", key="clear_chat"):
        ss.chat = []
        st.rerun()
