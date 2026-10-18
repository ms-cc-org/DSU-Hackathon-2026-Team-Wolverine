"""My Farm Plan: generate a preparedness plan from the data, edit it, save it, revisit it and export it."""
from datetime import datetime

import streamlit as st

from droughtlens import farm
from droughtlens.theme import chapter, html
from droughtlens.views.common import goto, user_record


def _edited(plan):
    """The plan with whatever is currently typed in the section boxes."""
    sections = {k: st.session_state.get(f"plan_{plan['id']}_{k}", plan["sections"][k]) for k, _ in farm.SECTIONS}
    return {**plan, "sections": sections}


def _save(record, plan):
    for i, p in enumerate(record["plans"]):
        if p["id"] == plan["id"]:
            record["plans"][i] = {**plan, "updated": datetime.now().isoformat(timespec="minutes")}
    farm.save_user(st.session_state.user, record)


def show():
    ss = st.session_state
    record, store_error = user_record()
    html("<div class='eyebrow'>My Farm Plan</div>")
    if store_error:
        st.error(store_error)
    chapter("Plan", "Your drought preparedness plan",
            "Generated from your field and our records, then yours to edit. Every line is tagged Data (read from our files) or General guidance (common practice, not from our data).",
            hint=("The plan is assembled by fixed rules from the same tables the rest of DroughtLens shows for your county, crop, growing stage and water setting. "
                  "DroughtLens never recommends costly interventions, irrigation volumes or planting changes, because the data cannot support them."))

    fields = record["fields"]
    if not fields:
        st.info("A plan starts from a saved field. Add your first field, then come back to generate its plan.")
        st.button("Add a field", type="primary", on_click=goto, args=("fields",))
        return

    ids = [f["id"] for f in fields]
    if ss.get("active_field") not in ids:
        ss.active_field = ids[0]
    pick = st.selectbox("Field", ids, index=ids.index(ss.active_field), format_func=lambda i: farm.field_label(next(f for f in fields if f["id"] == i)), key="plan_field")
    ss.active_field = pick
    field = next(f for f in fields if f["id"] == pick)

    plans = sorted((p for p in record["plans"] if p["field_id"] == field["id"]), key=lambda p: p["updated"], reverse=True)
    c1, c2 = st.columns([1.4, 2], vertical_alignment="bottom")
    if c1.button("Generate a new plan from my data" if plans else "Generate my plan", type="primary", width="stretch", key="gen_plan"):
        with st.spinner("Reading your county's records..."):
            try:
                plan = farm.new_plan(field)
                record["plans"].append(plan)
                farm.save_user(ss.user, record)
            except farm.StoreError as exc:
                st.error(str(exc))
            else:
                ss.current_plan = plan["id"]
                st.rerun()
    if not plans:
        st.info("You have no plan for this field yet. Generate one to see all six sections.")
        return

    ids_p = [p["id"] for p in plans]
    if ss.get("current_plan") not in ids_p:
        ss.current_plan = ids_p[0]
    with c2:
        cur = st.selectbox("Saved plans for this field", ids_p, index=ids_p.index(ss.current_plan), key="plan_pick",
                           format_func=lambda i: f"Saved {next(p for p in plans if p['id'] == i)['updated'].replace('T', ' ')}")
        ss.current_plan = cur
    plan = next(p for p in plans if p["id"] == cur)

    html("<div class='callout finding'><span class='tagline'>Data</span>Read from our records for your county.</div>"
         "<div class='callout guidance'><span class='tagline'>General guidance</span>Common practice, not derived from our data. Check it against your own judgment, your agent and your extension office.</div>")
    for key, title in farm.SECTIONS:
        st.markdown(f"### {title}")
        st.text_area(title, value=plan["sections"][key], height=max(120, 28 * (plan["sections"][key].count("\n") + 2)), key=f"plan_{plan['id']}_{key}", label_visibility="collapsed")

    live = _edited(plan)
    a, b, c, d = st.columns(4)
    if a.button("Save changes", type="primary", width="stretch", key="save_plan"):
        try:
            _save(record, live)
        except farm.StoreError as exc:
            st.error(str(exc))
        else:
            st.success("Saved. You can come back to this plan any time.")
    b.download_button("Download (Markdown)", farm.to_markdown(live), file_name=f"drought-plan-{field['name'].replace(' ', '-')}.md", mime="text/markdown", width="stretch")
    c.download_button("Download (printable)", farm.to_html(live), file_name=f"drought-plan-{field['name'].replace(' ', '-')}.html", mime="text/html", width="stretch",
                      help="Open the file in a browser and use Print to save it as a PDF.")
    if d.button("Delete this plan", width="stretch", key="delete_plan"):
        record["plans"] = [p for p in record["plans"] if p["id"] != plan["id"]]
        try:
            farm.save_user(ss.user, record)
        except farm.StoreError as exc:
            st.error(str(exc))
        else:
            ss.pop("current_plan", None)
            st.rerun()
    with st.expander("Read the plan as formatted text"):
        st.markdown(farm.to_markdown(live))
