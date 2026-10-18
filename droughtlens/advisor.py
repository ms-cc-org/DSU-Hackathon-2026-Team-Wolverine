"""The Agricultural Advisor: answers questions from DroughtLens's own data.

It is not a language model. Each answer is assembled by fixed rules from the same tables the rest of the app shows,
for the location, crop and field the farmer has selected. It keeps data-backed findings apart from general guidance,
and when the data cannot answer a question it says so instead of guessing.
"""
from droughtlens import data
from droughtlens.data import CROP_NAMES, PERIODS, STATE_NAMES, FIRST_YEAR, LAST_YEAR
from droughtlens.farm import STAGES
from droughtlens.insights import county_profile, has_yield_record
from droughtlens.reality import (analysis, below, crop_adj, cell, heat_thresholds, lc_first, loss_phrase, loss_text, peak_share,
                                 research, state_estimate, total_amount, typical_yield, get_panel)
from droughtlens.theme import LEVEL_NAME

INTRO = ("Welcome to DroughtLens. I'm your Agricultural Advisor. Let's explore drought conditions for your farm and identify "
         "practical steps to help you prepare.")
SCOPE_NOTE = ("I answer from DroughtLens's data using fixed rules, not a language model. I can only say what the data supports, "
              f"and it ends at {data.latest_observation():%B %d, %Y}: I have no live conditions and no forecast.")
SUGGESTED = [
    "What drought risks should I prepare for?",
    "How could drought affect my corn?",
    "Compare drought considerations for corn and soybeans.",
    "Create a drought preparedness plan for my farm.",
    "Explain the historical data behind this prediction.",
]
GENERAL = [
    "Check where your county stands on the U.S. Drought Monitor this week.",
    "Walk the field and check soil moisture at several spots.",
    "Confirm your crop insurance coverage and reporting dates with your agent.",
    "Talk with your county extension office about what you are seeing.",
]


def _crops(ctx):
    return ctx["field"]["crops"] if ctx.get("field") else [ctx["crop"]]


def _period(ctx):
    f = ctx.get("field")
    return STAGES.get(f.get("stage"), ctx["period"]) if f and f.get("stage") else ctx["period"]


def _irrig(ctx):
    f = ctx.get("field")
    return f.get("irrigation") if f and ctx["state"] == "NE" else None


def route(question):
    """Pick the topic for a question: one of risks, crop:CORN, crop:SOYBEANS, compare, plan, explain, live, soil, heat, water, unknown."""
    q = question.lower()
    if any(w in q for w in ("forecast", "tomorrow", "next week", "this week", "current condition", "today", "price", "market", "will it rain", "predict")) \
            and "historical data behind" not in q:
        return "live"
    if any(w in q for w in ("compare", "versus", " vs ", "difference between")):
        return "compare"
    if any(w in q for w in ("create", "make me", "generate", "preparedness plan", "farm plan", "write a plan", "draft")):
        return "plan"
    if any(w in q for w in ("explain", "historical", "history", "data behind", "how do you know", "why does", "where does", "source")):
        return "explain"
    if "corn" in q and "soy" not in q:
        return "crop:CORN"
    if "soy" in q and "corn" not in q:
        return "crop:SOYBEANS"
    if any(w in q for w in ("heat", "hot", "temperature")):
        return "heat"
    if any(w in q for w in ("soil", "moisture", "water storage")):
        return "soil"
    if any(w in q for w in ("irrigat", "dryland", "pivot")):
        return "water"
    if any(w in q for w in ("risk", "prepare", "drought", "worry", "expect")):
        return "risks"
    return "unknown"


def _county_findings(ctx, crop):
    p = county_profile(ctx["fips"], crop, _period(ctx))
    out = []
    months = PERIODS[p["period"]][1]
    if p["years"]:
        out.append(f"In {p['d2_years']} of {p['years']} seasons ({FIRST_YEAR}–{LAST_YEAR}), {p['county']} reached D2 (severe) drought or worse during {months}. "
                   f"The longest spell was {p['worst_year']} ({p['worst_weeks']} weeks in D2 or worse).")
    if has_yield_record(p) and p["dry_change"] is not None:
        out.append(f"{p['county']} {crop_adj(crop)} yields averaged {below(p['dry_change'], 1)} in the {p['dry_years']} seasons that reached D2 or worse, "
                   f"against {below(p['other_change'], 1)} in other seasons.")
    elif not has_yield_record(p):
        out.append(f"I have no reported {CROP_NAMES[crop].lower()} yields for {p['county']}, so there is no county yield history. The state-level figures still apply.")
    return p, out


def _state_findings(ctx, crop, levels=(3, 4)):
    out = []
    state = ctx["state"]
    for lv in levels:
        row, _, text = state_estimate(crop, state, lv, _irrig(ctx))
        if row is not None:
            out.append(f"At {lc_first(LEVEL_NAME[lv])}, {STATE_NAMES[state]} {CROP_NAMES[crop].lower()} averaged {loss_phrase(row.train_mean)} in 2000–2012. {text}")
    return out


def _unavailable():
    return (f"Current conditions and forecasts are not available here. The latest Drought Monitor reading in my data is "
            f"{data.latest_observation():%B %d, %Y}.")


def answer(topic, ctx):
    """Returns {'findings': [...], 'guidance': [...], 'notes': [...], 'action': None or 'plan'}."""
    out = {"findings": [], "guidance": [], "notes": [], "action": None}

    if topic == "risks":
        for crop in _crops(ctx):
            p, lines = _county_findings(ctx, crop)
            out["findings"] += [f"**{CROP_NAMES[crop]}.** {x}" for x in lines] + _state_findings(ctx, crop)
            neg, sharp = heat_thresholds(crop)
            if neg:
                out["findings"].append(f"{CROP_NAMES[crop]} yields turn negative at {neg} days of 35 °C (95 °F) or hotter in a season and fall sharply at {sharp}.")
        out["findings"].append(_unavailable())
        out["guidance"] = GENERAL
        return out

    if topic.startswith("crop:") or topic == "unknown_crop":
        crop = topic.split(":")[1]
        p, lines = _county_findings(ctx, crop)
        a = analysis(crop)
        share = peak_share(a)
        out["findings"] += lines + _state_findings(ctx, crop)
        if share is not None:
            out["findings"].append(f"{share:.0%} of extreme-drought (D3) {crop_adj(crop)} seasons had severe drought reach the county in July or August.")
        neg, sharp = heat_thresholds(crop)
        if neg:
            out["findings"].append(f"{CROP_NAMES[crop]} yields turn negative at {neg} days of 35 °C or hotter and fall sharply at {sharp}.")
        acres = ctx.get("acres")
        row, _, _ = state_estimate(crop, ctx["state"], 4, _irrig(ctx))
        if acres and row is not None and has_yield_record(p):
            typical = typical_yield(get_panel(), ctx["state"], p["county"], crop)
            lost = max(typical * -row.train_mean / 100 * acres, 0)
            out["findings"].append(f"At D3, the 2000–2012 average would mean about {total_amount(crop, lost)} less {CROP_NAMES[crop].lower()} on {acres:,} acres. "
                                   "That is a historical average, not a forecast.")
        elif not acres:
            out["notes"].append("Add your acres under My Fields and I can turn the percentages into tons or bushels.")
        out["findings"].append(_unavailable())
        out["guidance"] = GENERAL
        return out

    if topic == "compare":
        state = ctx["state"]
        for crop in ("CORN", "SOYBEANS"):
            _, lines = _county_findings(ctx, crop)
            parts = []
            for lv in (3, 4):
                row, _, _ = state_estimate(crop, state, lv, _irrig(ctx))
                if row is not None:
                    parts.append(f"{LEVEL_NAME[lv].split('(')[1].rstrip(')')} {loss_text(row.train_mean)}")
            neg, sharp = heat_thresholds(crop)
            share = peak_share(analysis(crop))
            out["findings"].append(f"**{CROP_NAMES[crop]}** in {STATE_NAMES[state]}: 2000–2012 averages {', '.join(parts)}. "
                                   f"{share:.0%} of D3 seasons had severe drought in July or August. Yields turn negative at {neg} hot days and fall sharply at {sharp}. "
                                   + (lines[1] if len(lines) > 1 else ""))
        out["findings"].append("The two crops respond to heat and drought timing in similar ways in this data. Where they differ is in the size of the loss at each level.")
        out["guidance"] = ["Review each crop's fields separately when you scout.", "Ask your agent how coverage differs between corn and soybeans."]
        return out

    if topic == "explain":
        crop = ctx["crop"]
        state = ctx["state"]
        row, css, text = state_estimate(crop, state, 4, _irrig(ctx))
        out["findings"].append("DroughtLens does not make predictions. It shows what each Drought Monitor level has cost corn and soybean yields in the past, "
                               "and whether those past costs held steady in later years.")
        if row is not None:
            out["findings"].append(f"For {STATE_NAMES[state]} {CROP_NAMES[crop].lower()} at extreme drought (D3): the 2000–2012 average was {below(row.train_mean, 1)} "
                                   f"across {row.train_n} county-years. We then checked it on 2013–2025 ({row.test_n} county-years). {text}")
        out["findings"].append(f"Each yield change is measured against that county's own trend line, so a normal year is 0%. The records run {FIRST_YEAR} to {LAST_YEAR}: "
                               "USDA NASS yields, U.S. Drought Monitor weekly drought, NOAA ACIS weather, NRCS soil and NASA MODIS greenness.")
        p, lines = _county_findings(ctx, crop)
        out["findings"] += lines
        out["notes"].append("The History tab shows the check cell by cell, and the Data sources page lists every file.")
        return out

    if topic == "plan":
        out["action"] = "plan"
        out["findings"].append("I can draft a plan from the data for your selected field or county. Every line is tagged as Data or General guidance, and you can edit it.")
        return out

    if topic == "live":
        out["findings"].append(_unavailable())
        out["findings"].append("DroughtLens has no weather forecast, live drought map or market data, and it does not predict future drought.")
        out["guidance"] = ["Check the U.S. Drought Monitor (droughtmonitor.unl.edu) and the National Weather Service for current conditions and forecasts.",
                           "Talk with your county extension office for local conditions."]
        return out

    if topic == "heat":
        for crop in _crops(ctx):
            g = research(crop)["q5"]
            g = g[g.crop == crop]
            neg, sharp = heat_thresholds(crop)
            hottest = g.iloc[-1]
            out["findings"].append(f"{CROP_NAMES[crop]}: yield turns negative at {neg} days of 35 °C (95 °F) or hotter in a season and falls sharply at {sharp} "
                                   f"({below(hottest['mean'], 1)} in the hottest group, Iowa and Nebraska together).")
        out["guidance"] = GENERAL[:2]
        return out

    if topic == "soil":
        p = county_profile(ctx["fips"], ctx["crop"], "full")
        s = p["soil"]
        if s:
            out["findings"].append(f"{p['county']} soils hold about {s['aws_mm']:.0f} mm of plant-available water in the top metre (the Nebraska and Iowa median is {s['aws_median_mm']:.0f} mm).")
        q2 = research(ctx["crop"])["q2"]
        out["findings"].append(f"In Iowa, counties with more soil water storage did not clearly lose less in drought years (r = {q2['r']:+.2f}, a very weak link).")
        out["notes"].append("I have soil water capacity, not measured soil moisture. Check moisture in the field.")
        out["guidance"] = GENERAL[:2]
        return out

    if topic == "water":
        if ctx["state"] == "NE":
            for crop in _crops(ctx):
                d, i = cell(analysis(crop)["irr_check"], "NE", 4, "mostly dryland"), cell(analysis(crop)["irr_check"], "NE", 4, "mostly irrigated")
                if d is not None and i is not None:
                    out["findings"].append(f"At extreme drought (D3) in 2000–2012, Nebraska dryland {CROP_NAMES[crop].lower()} counties had {loss_phrase(d.train_mean)}; irrigated counties had {loss_phrase(i.train_mean)}.")
        else:
            out["findings"].append("Iowa is rain-fed and NASS publishes no irrigation series for Iowa, so I have nothing on irrigation there.")
        out["notes"].append("I do not advise irrigation volumes or schedules: the data cannot support them.")
        return out

    out["findings"].append("I can't answer that from the data I have.")
    out["notes"].append("Try asking about drought risk for your county, how drought could affect corn or soybeans, a comparison of the two crops, "
                        "the heat, soil or irrigation findings, or ask me to create a preparedness plan.")
    return out
