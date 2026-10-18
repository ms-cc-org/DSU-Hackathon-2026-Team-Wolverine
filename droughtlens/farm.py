"""Farmers' fields and preparedness plans: storage, plan generation and export.

Plans are generated from the project's data. Each statement is tagged Data (read from our files) or General guidance
(common practice, not derived from our data), so a farmer can tell them apart. No irrigation volumes, no costly
interventions and no planting changes are ever recommended: the data here cannot support them.
"""
import json
import os
import uuid
from datetime import date, datetime
from html import escape
from pathlib import Path

from droughtlens import data
from droughtlens.data import CROP_NAMES, PERIODS, STATE_NAMES, FIRST_YEAR, LAST_YEAR
from droughtlens.insights import county_profile, has_yield_record
from wolverine import reality_table as rt

from droughtlens.reality import analysis, below, cell, crop_adj, get_panel, heat_thresholds, lc_first, loss_phrase, loss_text, peak_share, research, state_estimate, total_amount, typical_yield
from droughtlens.theme import LEVEL_NAME

# Git-ignored: farmers' fields and plans stay on this server. DROUGHTLENS_STORE points tests elsewhere.
STORE = Path(os.environ.get("DROUGHTLENS_STORE", Path(__file__).resolve().parents[1] / "app_data" / "farm_data.json"))
STORE_DIR = STORE.parent

STAGES = {
    "Not yet planted": "early",
    "Planted and emerging": "early",
    "Vegetative growth": "early",
    "Flowering and pollination": "peak",
    "Pod or grain fill": "peak",
    "Maturity and harvest": "late",
}
IRRIGATION = {"Irrigated": "mostly irrigated", "Rain only (dryland)": "mostly dryland", "Not sure": None}
IRRIGATION_LABEL = {v: k for k, v in IRRIGATION.items()}
SECTIONS = [
    ("assessment", "1. Farm assessment"),
    ("priorities", "2. Immediate priorities"),
    ("short_term", "3. Short-term preparation"),
    ("crop_specific", "4. Crop-specific considerations"),
    ("monitoring", "5. Monitoring schedule"),
    ("summary", "6. Plan summary"),
]
DATA, GUIDE = "**Data:**", "**General guidance:**"


class StoreError(Exception):
    """The farm data file could not be read or written."""


# --- Storage ----------------------------------------------------------------
def load_user(user):
    try:
        if not STORE.exists():
            return {"fields": [], "plans": []}
        blob = json.loads(STORE.read_text(encoding="utf-8"))
        return blob.get(user, {"fields": [], "plans": []})
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreError(f"We could not read your saved fields and plans ({exc}).") from exc


def save_user(user, record):
    try:
        STORE_DIR.mkdir(exist_ok=True)
        blob = json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else {}
        blob[user] = record
        tmp = STORE.with_suffix(".tmp")
        tmp.write_text(json.dumps(blob, indent=2), encoding="utf-8")
        tmp.replace(STORE)
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreError(f"We could not save your changes ({exc}).") from exc


def new_field(name, fips, crops, acres=None, planting_date=None, stage=None, irrigation=None):
    return {"id": uuid.uuid4().hex[:8], "name": name.strip(), "fips": fips, "crops": crops, "acres": acres,
            "planting_date": planting_date.isoformat() if planting_date else None, "stage": stage, "irrigation": irrigation,
            "created": datetime.now().isoformat(timespec="minutes")}


def _state(fips):
    return data.counties().set_index("fips").state_alpha[fips]


def field_label(f):
    return f"{f['name']} · {data.county_name(f['fips'])}, {STATE_NAMES[_state(f['fips'])]}"


# --- Plan generation ----------------------------------------------------------
def _assessment(field, crops, period, today):
    fips, state = field["fips"], _state(field["fips"])
    county, st_name = data.county_name(fips), STATE_NAMES[state]
    months = PERIODS[period][1]
    lines = [f"**Field:** {field['name']} · {county}, {st_name}"
             + (f" · {field['acres']:,} acres" if field.get("acres") else "")
             + f" · crops: {', '.join(CROP_NAMES[c] for c in crops)}",
             f"**Growing stage you entered:** {field.get('stage') or 'not entered'}. "
             f"This plan looks at the {PERIODS[period][0].lower()} ({months}); see assumptions below.",
             f"**Water:** {IRRIGATION_LABEL.get(field.get('irrigation'), 'not entered')}"]
    for crop in crops:
        p = county_profile(fips, crop, period)
        name = CROP_NAMES[crop].lower()
        freq = (f"- {DATA} In {p['d2_years']} of {p['years']} seasons ({FIRST_YEAR}–{LAST_YEAR}), {county} reached D2 (severe) drought or worse "
                f"during {months}. The longest spell was {p['worst_year']}, with {p['worst_weeks']} weeks in D2 or worse.") if p["years"] else None
        if freq and freq not in lines:      # early and peak windows are the same for both crops
            lines.append(freq)
        if has_yield_record(p) and p["dry_change"] is not None:
            lines.append(f"- {DATA} {county} {crop_adj(crop)} yields averaged {below(p['dry_change'], 1)} in the {p['dry_years']} seasons that reached D2 or worse, "
                         f"against {below(p['other_change'], 1)} in other seasons.")
        elif not has_yield_record(p):
            lines.append(f"- {DATA} We have no reported {name} yields for {county}, so there is no county yield history here. State-level figures below still apply.")
        for lv in (3, 4):
            row, _, verdict_text = state_estimate(crop, state, lv, field.get("irrigation") if state == "NE" else None)
            if row is not None:
                lines.append(f"- {DATA} At {lc_first(LEVEL_NAME[lv])}, {st_name} {name} averaged {loss_phrase(row.train_mean)} in 2000–2012. {verdict_text}")
        area = p["area"]
        if area:
            lines.append(f"- {DATA} NASS recorded {area[1]:,.0f} acres of {name} harvested in {county} in {area[0]}.")
    lines.append(f"- {DATA} **Current conditions: not available.** The latest Drought Monitor reading in DroughtLens data is {data.latest_observation():%B %d, %Y}.")
    lines.append(f"- {DATA} **Forecast: not available.** DroughtLens does not forecast weather or drought.")
    return "\n".join(lines)


def _priorities(field, crops, period):
    county = data.county_name(field["fips"])
    out = [f"- {GUIDE} Check where {county} stands on the U.S. Drought Monitor this week (droughtmonitor.unl.edu). DroughtLens does not show live conditions.",
           f"- {GUIDE} Walk the field. Note the crop stage and any signs of stress, and compare with the stage you entered.",
           f"- {GUIDE} Check soil moisture in the root zone at several spots, not just one.",
           f"- {GUIDE} Confirm your crop insurance coverage and reporting dates with your agent."]
    state = _state(field["fips"])
    if state == "NE" and field.get("irrigation") == "mostly dryland":
        crop = crops[0]
        d, i = cell(analysis(crop)["irr_check"], "NE", 4, "mostly dryland"), cell(analysis(crop)["irr_check"], "NE", 4, "mostly irrigated")
        if d is not None and i is not None:
            out.append(f"- {DATA} You said this field is rain-only. At extreme drought (D3) in 2000–2012, Nebraska dryland {CROP_NAMES[crop].lower()} counties had "
                       f"{loss_phrase(d.train_mean)}, against {loss_phrase(i.train_mean)} in irrigated counties.")
    return "\n".join(out)


def _short_term(field, crops):
    county, state = data.county_name(field["fips"]), _state(field["fips"])
    out = []
    for lv, label, guide in ((2, "D1 (moderate) or worse", "Walk fields at least weekly and revisit this plan."),
                             (3, "D2 (severe) or worse", "Talk with your crop insurance agent and your county extension office about what you are seeing."),
                             (4, "D3 (extreme) or worse", "Review your options with your agent and extension office, and keep notes and photos of crop conditions.")):
        facts = []
        for crop in crops:
            row, _, _ = state_estimate(crop, state, lv, field.get("irrigation") if state == "NE" else None)
            if row is not None:
                facts.append(f"{CROP_NAMES[crop].lower()} {loss_text(row.train_mean)}")
        out.append(f"- **If the Drought Monitor puts {county} in {label}:** {GUIDE} {guide}"
                   + (f" {DATA} In {STATE_NAMES[state]}, 2000–2012 averages at {LEVEL_NAME[lv].split('(')[1].rstrip(')')}: {'; '.join(facts)}." if facts else ""))
    return "\n".join(out)


def _crop_specific(field, crops):
    state, county = _state(field["fips"]), data.county_name(field["fips"])
    out = []
    for crop in crops:
        name, a = CROP_NAMES[crop], analysis(crop)
        share = peak_share(a)
        neg, sharp = heat_thresholds(crop)
        out.append(f"**{name}**")
        if share is not None:
            out.append(f"- {DATA} {share:.0%} of extreme-drought (D3) {crop_adj(crop)} seasons had severe drought reach the county in July or August.")
        if neg:
            out.append(f"- {DATA} {crop_adj(crop).capitalize()} yields turn negative at {neg} days of 35 °C (95 °F) or hotter in a season, and fall sharply at {sharp}.")
        q1 = research(crop)["q1_weeks"]
        g = q1[(q1.state_alpha == state)]
        if len(g):
            worst = g.iloc[-1]
            out.append(f"- {DATA} {STATE_NAMES[state]} {name.lower()} with {worst.weeks} in D2 or worse averaged {below(worst['mean'], 1)}.")
        p = county_profile(field["fips"], crop, "full")
        if field.get("acres") and has_yield_record(p):
            typical = typical_yield(get_panel(), state, county, crop)
            row, _, _ = state_estimate(crop, state, 4, field.get("irrigation") if state == "NE" else None)
            if row is not None and typical == typical:
                lost = max(typical * -row.train_mean / 100 * field["acres"], 0)
                out.append(f"- {DATA} At D3, the 2000–2012 average would mean about {total_amount(crop, lost)} less {name.lower()} on {field['acres']:,} acres. This is a historical average, not a forecast.")
        out.append(f"- {GUIDE} Compare what you see in the field with the stage you entered, and note it each time you scout.")
    return "\n".join(out)


def _monitoring(field, crops):
    state = _state(field["fips"])
    q1 = research(crops[0])["q1_weeks"]
    g = q1[q1.state_alpha == state].set_index("weeks")["mean"]
    neg, sharp = heat_thresholds(crops[0])
    triggers = [f"- **Review the plan when** {data.county_name(field['fips'])} moves up one Drought Monitor level (for example from D0 to D1, or D1 to D2)."]
    if "5–9 weeks" in g.index and "10 or more weeks" in g.index:
        triggers.append(f"- **Review again when** weeks in D2 or worse pass 5 and again at 10. {DATA} {STATE_NAMES[state]} {CROP_NAMES[crops[0]].lower()} averaged "
                        f"{below(g['5–9 weeks'], 1)} with 5 to 9 such weeks and {below(g['10 or more weeks'], 1)} with 10 or more.")
    if neg:
        triggers.append(f"- **Review when** the season reaches {neg} days at 35 °C (95 °F) or hotter. {DATA} Yields turn negative around there, and fall sharply at {sharp}.")
    return "\n".join([
        f"- **Weekly:** {GUIDE} check the Drought Monitor map for {data.county_name(field['fips'])}.",
        f"- **Weekly in July and August:** {GUIDE} walk the field. {DATA} Most extreme-drought seasons had severe drought reach the county in these months.",
        f"- **At the start of each period (June 1, July 1, September 1):** {GUIDE} reassess and update this plan.",
        *triggers,
        f"- {GUIDE} If anything here conflicts with what you see in the field or hear from your agent or extension office, trust them and tell us what you saw."])


def _summary(field, crops, period, today):
    fa = [analysis(c)["check"] for c in crops]
    shares = [rt.score(f)["share_within_tol"] for f in fa]
    return "\n".join([
        f"- **Assessment date:** {today:%B %d, %Y}.",
        f"- **Data sources:** USDA NASS yields and irrigation, NOAA ACIS weather, U.S. Drought Monitor weekly drought ({FIRST_YEAR}–{LAST_YEAR}), NRCS SSURGO soil, NASA MODIS greenness. See the Data sources page.",
        f"- **Latest drought observation in our data:** {data.latest_observation():%B %d, %Y}. There is no live feed and no forecast.",
        f"- **Assumptions:** the growing stage you entered maps to a planning period ({', '.join(f'{k} = {PERIODS[v][0].lower()}' for k, v in STAGES.items())}). "
        "Yield estimates are state-level averages of past seasons at each drought level; the county only sets typical yield. Corn is shown in tons per acre (56 lb per bushel).",
        f"- **Uncertainty:** these are averages of past years, not forecasts. Estimates were built on 2000–2012 and checked on 2013–2025; "
        f"{' and '.join(f'{s:.0%} of the {CROP_NAMES[c].lower()} estimates' for c, s in zip(crops, shares))} landed within 4 points. Some drought levels have too few past years to check; the plan says so where it applies.",
        "- **What this is not:** this plan was generated by DroughtLens from historical data. It is not an official drought assessment, a weather forecast or professional agronomic advice. "
        "For decisions that cost money, talk with your crop insurance agent and your county extension office."])


def build_plan(field, today=None):
    """A preparedness plan for a saved field. Returns a dict of the six sections as markdown text."""
    today = today or date.today()
    crops = field["crops"]
    period = STAGES.get(field.get("stage"), "full") if field.get("stage") else "full"
    return {
        "assessment": _assessment(field, crops, period, today), "priorities": _priorities(field, crops, period),
        "short_term": _short_term(field, crops), "crop_specific": _crop_specific(field, crops),
        "monitoring": _monitoring(field, crops), "summary": _summary(field, crops, period, today),
    }


def new_plan(field, sections=None):
    sections = sections or build_plan(field)
    now = datetime.now().isoformat(timespec="minutes")
    return {"id": uuid.uuid4().hex[:8], "field_id": field["id"], "field_name": field["name"], "crops": field["crops"],
            "created": now, "updated": now, "sections": sections}


# --- Export -------------------------------------------------------------------
def to_markdown(plan):
    parts = [f"# Drought preparedness plan: {plan['field_name']}", f"*DroughtLens · saved {plan['updated']}*", ""]
    for key, title in SECTIONS:
        parts += [f"## {title}", plan["sections"][key], ""]
    return "\n".join(parts)


def _inline(text):
    out, bold = "", False
    for chunk in escape(text).split("**"):
        out += f"<b>{chunk}</b>" if bold else chunk
        bold = not bold
    return out


def to_html(plan):
    body = [f"<h1>Drought preparedness plan: {escape(plan['field_name'])}</h1><p><i>DroughtLens · saved {escape(plan['updated'])}</i></p>"]
    for key, title in SECTIONS:
        body.append(f"<h2>{escape(title)}</h2>")
        in_list = False
        for line in plan["sections"][key].split("\n"):
            if line.startswith("- "):
                body.append(("" if in_list else "<ul>") + f"<li>{_inline(line[2:])}</li>")
                in_list = True
            else:
                body.append(("</ul>" if in_list else "") + (f"<p>{_inline(line)}</p>" if line.strip() else ""))
                in_list = False
        if in_list:
            body.append("</ul>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Drought preparedness plan</title><style>"
            "body{font-family:Georgia,serif;max-width:46rem;margin:2rem auto;padding:0 1rem;color:#292D29;line-height:1.5}"
            "h1,h2{color:#243D2D}h2{border-top:1px solid #ddd;padding-top:1rem}</style></head><body>" + "".join(body) + "</body></html>")
