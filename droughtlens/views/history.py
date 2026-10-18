"""History: the Drought Category Reality Check, the 2013-2025 test, the county's weather and drought record, and the six
research questions. Everything is observed history; nothing here predicts."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from wolverine import reality_table as rt
from wolverine.contracts import MIN_CELL_N, STRICT_ANOM, TOLERANCE_PTS

from droughtlens import data
from droughtlens.charts import BAR_TEXT, STATE_COLORS, style
from droughtlens.data import CROP_NAMES, STATE_NAMES
from droughtlens.insights import county_profile, season_comparison
from droughtlens.reality import (MASTER_ANOM, SHARP, YIELD_UNITS, analysis, below, cell, crop_adj, first_bucket, heat_thresholds, peak_share,
                                 research, verdict)
from droughtlens.theme import (AMBER, DROUGHT_LEVELS, FOREST, LEVEL_COLOR, LEVEL_NAME, LEVEL_SHORT, MUTED, OLIVE, RED, SILK, SOIL,
                               callout, chapter, html, question, tip)

MASTER_TREND = "Master trend (all years)"
STRICT_TREND = "Strict trend (2000–2012 only)"


def check_table(chk, state):
    """Plain-language table: the 2000-2012 estimate, what 2013-2025 did, and the verdict, per drought level."""
    rows = ""
    for lv, name, *_ in DROUGHT_LEVELS:
        r = cell(chk, state, lv)
        if r is None:
            continue
        css, text = verdict(r)
        mark = {"ok": "✓", "miss": "✗", "na": "–"}[css]
        test = f"{below(r.test_mean)}<br><span class='small'>{r.test_n} county-years</span>" if r.test_n > 0 else "<span class='small'>No records</span>"
        rows += (f"<tr><td><b>{name}</b></td><td>{below(r.train_mean)}<br><span class='small'>{r.train_n} county-years</span></td>"
                 f"<td>{test}</td><td class='{css}'>{mark} {text}</td></tr>")
    return ("<table class='vt'><tr><th>Drought level</th><th>2000–2012 (our estimate)</th><th>2013–2025 (what happened)</th>"
            f"<th>Did it hold up?</th></tr>{rows}</table>")


def same_label(crop):
    a = analysis(crop)
    table, check = a["table"], a["check"]
    crop_name = CROP_NAMES[crop].lower()
    chapter("History", "Same drought label, different cost",
            f"Each bar is the average {crop_name} yield change, compared with normal for that county, in 2000 to 2012. Below zero means yield lost.",
            hint=("For each state and drought level we averaged yield_anomaly_pct over every county-year in 2000 to 2012 whose worst weekly drought level was that one. "
                  "yield_anomaly_pct is how far a year's yield sat from the county's own trend line, so a normal year is 0%. The same label (for example D3) can cost different amounts in different states."))
    d3 = rt.same_meaning(table, level=4, crop=crop)
    sc = rt.score(check)
    if d3["same"]:
        reco = (f"At extreme drought (D3), {crop_name} lost about the same in Iowa ({abs(d3['ia']):.0f}%) and Nebraska ({abs(d3['ne']):.0f}%), "
                "so one drought trigger can serve both states.")
    else:
        reco = (f"Don't read the drought map the same way in every state: at D3, plan for about a {abs(d3['ia']):.0f}% yield loss on Iowa {crop_name} "
                f"but about {abs(d3['ne']):.0f}% in Nebraska. These estimates held up on 2013–2025: {sc['share_within_tol']:.0%} of the "
                f"table's cells landed within {TOLERANCE_PTS:g} points.")
    html(f"<div class='quote'>{reco}</div>")
    m1, m2, m3 = st.columns(3)
    m1.metric("Iowa at D3", below(d3["ia"], 1))
    m2.metric("Nebraska at D3", below(d3["ne"], 1))
    m3.metric("Gap", f"{abs(d3['gap']):.1f} points", "about the same" if d3["same"] else "not the same", delta_color="off")
    fig = go.Figure()
    for abbr in ("IA", "NE"):
        g = table[table.state_alpha == abbr].sort_values("level")
        fig.add_trace(go.Bar(x=[LEVEL_SHORT[int(lv)] for lv in g.level], y=g.mean_loss, name=STATE_NAMES[abbr], marker_color=STATE_COLORS[abbr], customdata=g.n,
                             text=[f"{v:.0f}%" for v in g.mean_loss], hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
    fig.update_layout(barmode="group")
    style(fig, 340).update_yaxes(title="Yield compared with normal (%)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def held_up(crop, state):
    crop_name = CROP_NAMES[crop].lower()
    chapter("History", "Did it hold up on years we hadn't used?",
            f"We built the numbers from 2000 to 2012, then checked them against 2013 to 2025. An estimate counts as holding up if later years landed within {TOLERANCE_PTS:g} points of it.",
            hint=(f"A drought level is checked only when it has at least {MIN_CELL_N} county-years in both periods. 'Average miss' weights each level by its 2013 to 2025 county-years. "
                  "The master trend is fitted on all 26 years, so it sees the later years and flatters the check. The strict trend is fitted on 2000 to 2012 only, a true out-of-sample test."))
    strict = st.session_state.get("trend_version", MASTER_TREND) == STRICT_TREND
    chk = analysis(crop, STRICT_ANOM if strict else MASTER_ANOM)["check"]
    s = rt.score(chk)
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Estimates within {TOLERANCE_PTS:g} points", f"{s['share_within_tol']:.0%}")
    m2.metric("Average miss", f"{s['weighted_mae']:.1f} points")
    m3.metric("Estimates we could check", f"{s['cells_scored']} of {len(chk)}")
    st.markdown(f"**{STATE_NAMES[state]} {crop_name}, drought level by level**")
    html(check_table(chk, state))
    g = chk[(chk.state_alpha == state) & (chk.train_n > 0)].sort_values("level")
    fig = go.Figure()
    for col, label, color, n in (("train_mean", "2000–2012 (our estimate)", FOREST, "train_n"), ("test_mean", "2013–2025 (what happened)", AMBER, "test_n")):
        fig.add_trace(go.Bar(x=[LEVEL_SHORT[int(lv)] for lv in g.level], y=g[col], name=label, marker_color=color, customdata=g[n],
                             text=[f"{v:.0f}%" if pd.notna(v) else "" for v in g[col]], hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
    fig.update_layout(barmode="group")
    style(fig, 320).update_yaxes(title="Yield compared with normal (%)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with st.expander("For the data-curious: every estimate, both states, and a stricter test"):
        st.radio("Trend version", [MASTER_TREND, STRICT_TREND], key="trend_version",
                 help="The master trend is fitted on all 26 years. The strict trend is fitted on 2000–2012 only, so 2013–2025 is a true out-of-sample test.")
        shown = pd.DataFrame({
            "State": chk.state_alpha.map(STATE_NAMES), "Drought level": chk.level_label,
            "2000–2012 mean (%)": chk.train_mean.round(1), "2000–2012 county-years": chk.train_n,
            "2013–2025 mean (%)": chk.test_mean.round(1), "2013–2025 county-years": chk.test_n,
            "Miss (points)": chk.abs_error.round(1), "Did it hold up?": [verdict(r)[1].split(".")[0] for r in chk.itertuples()],
        })
        st.dataframe(shown, width="stretch", hide_index=True)
        pts = chk.dropna(subset=["train_mean", "test_mean"]).assign(State=lambda d: d.state_alpha.map(STATE_NAMES))
        sc_fig = px.scatter(pts, x="train_mean", y="test_mean", color="State", text="level_label", color_discrete_map={"Iowa": FOREST, "Nebraska": AMBER},
                            labels={"train_mean": "2000–2012 mean (%)", "test_mean": "2013–2025 mean (%)"})
        lo = float(min(pts.train_mean.min(), pts.test_mean.min())) - 2
        hi = float(max(pts.train_mean.max(), pts.test_mean.max())) + 2
        sc_fig.add_trace(go.Scatter(x=[lo, hi, hi, lo], y=[lo + TOLERANCE_PTS, hi + TOLERANCE_PTS, hi - TOLERANCE_PTS, lo - TOLERANCE_PTS], fill="toself",
                                    fillcolor="rgba(94,98,88,0.15)", line_width=0, name=f"±{TOLERANCE_PTS:g} points", hoverinfo="skip"))
        sc_fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(dash="dash", color=MUTED), name="Same in both periods"))
        sc_fig.update_traces(textposition="top center", selector=dict(mode="markers+text"))
        st.plotly_chart(style(sc_fig, 380), width="stretch")
        st.caption("Dots inside the shaded band held up. Dots on the dashed line landed exactly where 2000–2012 said they would.")


def county_story(fips, crop):
    p = county_profile(fips, crop, "full")
    county, crop_name = p["county"], CROP_NAMES[crop].lower()
    season = data.season_rows(fips, crop)
    chapter("History", f"Weather and drought in {county}",
            "Observed records for this county: rainfall, temperature, weekly drought, satellite greenness and soil. All of it is history.",
            hint="Rain and temperature come from NOAA ACIS daily records, drought from the weekly U.S. Drought Monitor, greenness from NASA MODIS, soil from NRCS SSURGO. None of it is forecast or modelled by DroughtLens.")

    # Precipitation: one year against the county's average
    st.markdown(f"### Rainfall through the season {tip('Cumulative rain from the first day of the growing season (May 1). The shaded band spans the wettest and driest year; the dashed line is the average of all years. Pick a year to compare.')}",
                unsafe_allow_html=True)
    curves = data.precip_curves(fips, crop, "full")
    years = [int(y) for y in curves.columns]
    worst = season.sort_values(["level", "precip_anomaly_pct"], ascending=[False, True]).dropna(subset=["level"])
    default = int(worst.year.iloc[0]) if len(worst) and int(worst.year.iloc[0]) in years else years[-1]
    year = st.selectbox("Compare a year with the county average", years, index=years.index(default), key="precip_year",
                        help="Starts on this county's driest year by drought level, then rainfall.")
    start = pd.Timestamp(2001, *data.period_window(crop, "full")[:2])
    dates = [start + pd.Timedelta(days=int(d) - 1) for d in curves.index]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=curves.max(axis=1), line_width=0, showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=dates, y=curves.min(axis=1), fill="tonexty", fillcolor="rgba(115,123,67,0.18)", line_width=0, name="Wettest to driest year", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=dates, y=curves.mean(axis=1), line=dict(color=OLIVE, dash="dash", width=2), name="Average year"))
    fig.add_trace(go.Scatter(x=dates, y=curves[year], line=dict(color=RED, width=3), name=str(year)))
    style(fig, 330).update_yaxes(title="Cumulative rain (mm)").update_xaxes(tickformat="%b %d")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    row = season[season.year == year]
    if len(row) and pd.notna(row.precip_anomaly_pct.iloc[0]):
        r = row.iloc[0]
        st.caption(f"{year}: {r.precip_mm:.0f} mm over the season, {abs(r.precip_anomaly_pct):.0f}% {'below' if r.precip_anomaly_pct < 0 else 'above'} this county's normal. "
                   f"Worst drought level that season: {LEVEL_NAME[int(r.level)]}.")

    # Temperature anomalies
    st.markdown(f"### Temperature each season, against this county's average {tip('Average growing-season temperature for each year minus the county average over all years. Red years were warmer than usual, olive years cooler.')}",
                unsafe_allow_html=True)
    t = season.dropna(subset=["tavg_c"])
    anom = t.tavg_c - t.tavg_c.mean()
    fig = go.Figure(go.Bar(x=t.year, y=anom, marker_color=[RED if v > 0 else OLIVE for v in anom], hovertemplate="%{x}: %{y:+.1f} °C<extra></extra>"))
    style(fig, 280, legend=False).update_yaxes(title="°C against county average").update_xaxes(dtick=2)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    if p["temp_trend_per_decade"] is not None:
        st.caption(f"Over {data.FIRST_YEAR}–{data.LAST_YEAR}, growing-season temperature in {county} changed by {p['temp_trend_per_decade']:+.2f} °C per decade. A trend over 26 years is a rough guide only.")

    # Weekly drought
    st.markdown(f"### Drought periods, week by week {tip('For every week since January 2000, the share of the county in D2 (severe) drought or worse, from the U.S. Drought Monitor. Tall stretches are drought periods.')}",
                unsafe_allow_html=True)
    w = data.weekly(fips)
    fig = go.Figure(go.Scatter(x=w.map_date, y=w.d2plus_pct, fill="tozeroy", line=dict(color=RED, width=1.2), fillcolor="rgba(169,75,63,0.35)",
                               hovertemplate="%{x|%b %d, %Y}: %{y:.0f}% of the county<extra></extra>"))
    style(fig, 280, legend=False).update_yaxes(title="% of county in D2 or worse", range=[0, 100])
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # Two periods compared
    st.markdown(f"### Comparing two periods {tip('Averages over the seasons in each period for this county. It shows how conditions changed between the years we built the estimates on and the years we checked them against. It does not predict the future.')}",
                unsafe_allow_html=True)
    cmp = season_comparison(season[season.year <= 2012], season[season.year >= 2013])
    rows = "".join(f"<tr><td>{label}</td>" + "".join(f"<td>{v:.1f}</td>" if v == v else "<td>–</td>" for v in vals) + "</tr>" for label, vals in cmp.iterrows())
    html(f"<table class='vt'><tr><th>{crop_name.capitalize()} seasons</th><th>2000–2012</th><th>2013–2025</th></tr>{rows}</table>")

    # Observed yield against trend
    rep = season[season.yield_status == "reported"].dropna(subset=["yield_anomaly_pct"])
    if len(rep):
        u = YIELD_UNITS[crop]
        st.markdown(f"### Observed yield against trend, {u['per_acre']} {tip('Each dot is one year of reported yield, coloured by that year\'s worst drought level. The dashed line is the county\'s own trend, which is what a normal year looks like. These are observations, not predictions.')}",
                    unsafe_allow_html=True)
        trend = rep.yield_per_acre / (1 + rep.yield_anomaly_pct / 100) * u["factor"]
        fig = go.Figure(go.Scatter(x=rep.year, y=trend, mode="lines", name="Trend", line=dict(color=MUTED, dash="dash", width=2)))
        for lv, name, short, color, *_ in DROUGHT_LEVELS:
            sub = rep[rep.level == lv]
            if len(sub):
                fig.add_trace(go.Scatter(x=sub.year, y=sub.yield_per_acre * u["factor"], mode="markers", name=short, marker=dict(color=color, size=12, line=dict(color="#292D29", width=1)),
                                         hovertemplate="%{x}: %{y:.2f}<extra></extra>" if crop == "CORN" else "%{x}: %{y:.0f}<extra></extra>"))
        style(fig, 340).update_yaxes(title=u["per_acre"].capitalize())
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # Satellite greenness
    m = data.modis(fips).merge(season[["year", "yield_anomaly_pct"]], on="year", how="left")
    if len(m):
        st.markdown(f"### Satellite greenness and yield {tip('Peak greenness seen by NASA MODIS each year, as a percent above or below the county average (bars), with the crop yield change against trend (line). The satellite sees all vegetation in the county, not only your crop, so the two will not match perfectly.')}",
                    unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=m.year, y=m.ndvi_anomaly_pct, name="Greenness vs average (%)", marker_color=SILK))
        fig.add_trace(go.Scatter(x=m.year, y=m.yield_anomaly_pct, mode="lines+markers", name=f"{CROP_NAMES[crop]} yield vs trend (%)", line=dict(color=FOREST, width=2.5)))
        style(fig, 300).update_yaxes(title="Percent").update_xaxes(dtick=2)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # Soil
    st.markdown(f"### Soil {tip('Soil water capacity, the share of the county on drought-prone soil and soil productivity come from USDA NRCS SSURGO. They do not change from year to year. Measured soil moisture is not in our data.')}",
                unsafe_allow_html=True)
    s = p["soil"]
    if s:
        c1, c2, c3 = st.columns(3)
        c1.metric("Soil water capacity", f"{s['aws_mm']:.0f} mm", f"Nebraska and Iowa median {s['aws_median_mm']:.0f} mm", delta_color="off")
        c2.metric("On drought-prone soil", f"{s['droughty_pct']:.0f}% of the county")
        c3.metric("Soil productivity index", f"{(s['nccpi_corn'] if crop == 'CORN' else s['nccpi_soy']):.2f}", help="0 is unproductive, 1 is the most productive soil in the US for this crop.")
    st.caption("Measured soil moisture is not in our data. We have how much water the soil can hold, not how much it holds today.")


def states_differ(crop):
    a = analysis(crop)
    chapter("History", "Why the same label costs different amounts", "Two things explain much of the gap: when the dry spell arrives, and whether the field can be watered.",
            hint="Timing and irrigation groups come from the team's analysis. A season counts as peak if severe drought (D2 or worse) reached the county in July or August, early if only before July.")
    st.markdown("### Peak-season drought versus early drought")
    tm = a["timing"]
    if len(tm):
        fig = go.Figure()
        for when, label, color in (("peak", "Peak (July to August)", RED), ("early", "Early (May to June)", "#D9B25F")):
            g = tm[tm.timing == when]
            fig.add_trace(go.Bar(x=[STATE_NAMES[x] for x in g.state_alpha], y=g.mean_loss, name=label, marker_color=color, customdata=g.n, text=[f"{v:.0f}%" for v in g.mean_loss],
                                 hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
        fig.update_layout(barmode="group")
        style(fig, 320).update_yaxes(title="Yield compared with normal at D3 (%)")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        share = peak_share(a)
        thin = tm[(tm.timing == "early") & (tm.n < MIN_CELL_N)]
        thin_note = (" Early-only D3 seasons are too rare to quote for " + " and ".join(STATE_NAMES[x] for x in thin.state_alpha) + f" (fewer than {MIN_CELL_N} county-years).") if len(thin) else ""
        yrs = a["timing_years"]
        st.markdown(f"**{share:.0%}** of D3 seasons had severe drought (D2 or worse) reach the county in July or August.{thin_note}")
        st.caption(f"Years {yrs[0]}–{yrs[1]}, {a['timing_counties']} counties with a timing label.")
    st.markdown("### Nebraska: irrigated versus dryland counties")
    it = a["irr_table"]
    if len(it):
        fig = go.Figure()
        for grp, label, color in (("mostly irrigated", "Mostly irrigated counties", FOREST), ("mostly dryland", "Mostly dryland counties", AMBER)):
            g = it[it.irrig_group == grp].sort_values("level")
            fig.add_trace(go.Bar(x=[LEVEL_SHORT[int(lv)] for lv in g.level], y=g.mean_loss, name=label, marker_color=color, customdata=g.n, text=[f"{v:.0f}%" for v in g.mean_loss],
                                 hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
        fig.update_layout(barmode="group")
        style(fig, 320).update_yaxes(title="Yield compared with normal (%)")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption("Irrigation data runs 2000–2018. Each Nebraska county gets one average irrigated share and is grouped at 50%. Iowa is rain-fed and is not split.")


def six_questions(crop):
    crop_name, adj = CROP_NAMES[crop].lower(), crop_adj(crop)
    chapter("History", "Six questions the data answers", "Straight from the same records, for the crop you chose. Hover the ? beside a question to see how we worked it out.")
    rs = research(crop)

    question(1, "When a county is in D2 drought or worse during its growing season, how far does yield fall below its own trend?",
             "We take every Iowa and Nebraska county-year of the crop you chose and flag the ones whose worst drought level that season was D2 (severe) or worse. 'Below normal' is yield_anomaly_pct: "
             "how far that year's yield sat from the county's own 26-year trend line. The bars group seasons by how many weeks the county spent in D2 or worse (weeks_in_d2_plus).")
    f1, w1 = rs["q1_flag"], rs["q1_weeks"]
    ia10 = w1[(w1.state_alpha == "IA") & (w1.weeks == "10 or more weeks")]
    callout(f"When a county reached D2 or worse, {adj} yields averaged <b>{below(f1[('IA', True)][0], 1)}</b> in Iowa ({f1[('IA', True)][1]:,} county-years) and "
            f"<b>{below(f1[('NE', True)][0], 1)}</b> in Nebraska ({f1[('NE', True)][1]:,}). In seasons with less drought they ran {below(f1[('IA', False)][0], 1)} and {below(f1[('NE', False)][0], 1)}."
            + (f" The longer the drought lasted, the bigger the drop: Iowa {crop_name} with 10 or more weeks in D2 or worse averaged <b>{below(ia10['mean'].iloc[0], 1)}</b>." if len(ia10) else ""))
    fig = go.Figure()
    for abbr in ("IA", "NE"):
        g = w1[w1.state_alpha == abbr]
        fig.add_trace(go.Bar(x=g.weeks.astype(str), y=g["mean"], name=STATE_NAMES[abbr], marker_color=STATE_COLORS[abbr], customdata=g["size"], text=[f"{v:.0f}%" for v in g["mean"]],
                             hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
    fig.update_layout(barmode="group")
    style(fig, 320).update_yaxes(title="Yield compared with normal (%)").update_xaxes(title="Weeks in D2 drought or worse this season")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    question(2, "In rain-fed Iowa, do counties with more soil water storage lose less yield in drought years?",
             "Iowa only, because Iowa is rain-fed. For each Iowa county we averaged its yield change in D2-or-worse seasons (counties with at least 3 such years), then split the counties into three equal groups by "
             "aws_100cm_mm, the water the top 100 cm of soil can hold. Nebraska is left out on purpose: its lowest-storage counties are the most heavily irrigated, so they look drought-resistant for reasons soil data "
             "can't show. r is the correlation across counties. Near zero means no pattern; the sign shows the direction.")
    q2 = rs["q2"]
    r, th = q2["r"], q2["thirds"]
    strength = "very weak" if abs(r) < 0.2 else "weak" if abs(r) < 0.4 else "moderate"
    lead = ("No. Counties that hold more soil water did not lose less; if anything they lost a little more." if r <= -0.1 else
            "A little. Counties that hold more soil water lost somewhat less." if r >= 0.1 else "No clear pattern.")
    callout(f"<b>{lead}</b> Across {q2['counties']} Iowa counties, {crop_name} in drought years averaged {below(th['change'].iloc[0], 1)} in the lowest-storage third, "
            f"{below(th['change'].iloc[1], 1)} in the middle third and {below(th['change'].iloc[2], 1)} in the highest-storage third (r = {r:+.2f}, a {strength} link).")
    fig = go.Figure(go.Bar(x=[f"{t}<br>({a:.0f} mm of water)" for t, a in zip(th.third, th.aws)], y=th.change, marker_color=FOREST, text=[f"{v:.1f}%" for v in th.change], **BAR_TEXT))
    style(fig, 300, legend=False).update_yaxes(title="Yield compared with normal in drought years (%)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    question(3, "In Nebraska, why does sorghum, the drought-tolerant crop, fall further than corn in drought years?",
             "We compared Nebraska county-years in D2-or-worse seasons for each crop. Irrigated share is each crop's average share of harvested acres that were irrigated (NASS irrigation records; sorghum only "
             "2000–2007). We also counted the Nebraska counties with a reported sorghum yield each year. The data shows what happened; it can't prove why.")
    q3 = rs["q3"]
    ch, ir, cn = q3["change"], q3["irrigated"], q3["counties"]
    corn_irr = analysis("CORN")["irr_check"]
    dry3, irr3 = cell(corn_irr, "NE", 4, "mostly dryland"), cell(corn_irr, "NE", 4, "mostly irrigated")
    callout(f"<b>{'Yes.' if ch['SORGHUM'] < ch['CORN'] else 'No.'}</b> In D2-or-worse seasons Nebraska sorghum averaged <b>{below(ch['SORGHUM'], 1)}</b>, corn <b>{below(ch['CORN'], 1)}</b> and soybeans <b>{below(ch['SOYBEANS'], 1)}</b>. "
            f"Sorghum is mostly grown without irrigation: on average {ir['SORGHUM']:.0%} of its harvested acres were irrigated, against {ir['CORN']:.0%} for corn. "
            f"Dryland corn counties lost far more at D3 ({abs(dry3.train_mean):.0f}%) than irrigated ones ({abs(irr3.train_mean):.0f}%), which fits sorghum's bigger loss. "
            f"And few sorghum counties report after 2010: {cn[2000]} in 2000, {cn[2010]} in 2010, {cn[2015]} in 2015 and {cn[2025]} in 2025, so recent sorghum results rest on very little data.")
    order = [c for c in ("CORN", "SOYBEANS", "SORGHUM") if c in ch.index]
    fig = go.Figure(go.Bar(x=[c.title() for c in order], y=[ch[c] for c in order], marker_color=[FOREST, FOREST, AMBER][:len(order)], text=[f"{ch[c]:.1f}%" for c in order], **BAR_TEXT))
    style(fig, 300, legend=False).update_yaxes(title="Yield compared with normal in D2-or-worse seasons (%)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    question(4, "Is growing-season rain a stronger predictor of yield in rain-fed Iowa than in irrigated California?",
             "For each state and crop we measured how closely growing-season rainfall (precip_anomaly_pct) tracks yield change across all county-years. The bars show r squared: the share of the yield swings "
             "that rainfall alone explains. California corn has few county-years, most of them before 2010, so treat that bar as rough.")
    q4 = {d["label"]: d for d in rs["q4"]}
    ia_c, ca_c, ne_c = q4["Iowa corn"], q4["California corn"], q4["Nebraska corn"]
    gap4 = ia_c["r2"] - ca_c["r2"]
    lead = ("Yes, a little, but rain says little on its own in either place." if gap4 > 0.01 else "Barely. Rain says little on its own in either place." if gap4 > 0 else "No.")
    callout(f"<b>{lead}</b> Rain explained <b>{ia_c['r2']:.0%}</b> of the year-to-year yield swings in Iowa corn and <b>{ca_c['r2']:.0%}</b> in California corn ({ca_c['n']} county-years)"
            f"{', where the link even runs slightly the wrong way' if ca_c['r'] < 0 else ''}. Rain mattered most in Nebraska corn, which is partly irrigated: <b>{ne_c['r2']:.0%}</b>.")
    fig = go.Figure(go.Bar(x=[d["label"] for d in rs["q4"]], y=[d["r2"] * 100 for d in rs["q4"]], marker_color=[FOREST, FOREST, AMBER, RED], customdata=[d["n"] for d in rs["q4"]],
                           text=[f"{d['r2']:.0%}" for d in rs["q4"]], hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
    style(fig, 300, legend=False).update_yaxes(title="Yield swings explained by rain (%)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    question(5, "Is there a number of extreme-heat days above which yield turns sharply negative? Does it differ by crop?",
             "We grouped Iowa and Nebraska county-years by extreme_heat_days (days at or above 35 °C, 95 °F, during the growing season) and averaged the yield change in each group. "
             f"'Turns negative' is the first group whose average is below zero. 'Sharply' means an average at or below {SHARP:.0f}%. Corn and soybeans only.")
    q5 = rs["q5"]
    parts, fig = [], go.Figure()
    for c, color in (("CORN", AMBER), ("SOYBEANS", FOREST)):
        g = q5[q5.crop == c]
        neg, sharp = heat_thresholds(c)
        parts.append(f"{CROP_NAMES[c]} {'turns' if c == 'CORN' else 'turn'} negative at <b>{neg or 'no group'}</b> hot days and fall{'s' if c == 'CORN' else ''} sharply at <b>{sharp or 'no group'}</b> "
                     f"({below(g['mean'].iloc[-1], 1)} in the hottest group)")
        fig.add_trace(go.Scatter(x=g.heat.astype(str), y=g["mean"], mode="lines+markers", name=CROP_NAMES[c], line=dict(color=color, width=3), marker=dict(size=9), customdata=g["size"],
                                 hovertemplate="%{x} hot days: %{y:.1f}% (%{customdata} county-years)<extra></extra>"))
    fig.add_hline(y=SHARP, line_dash="dash", line_color=MUTED, annotation_text=f"{SHARP:.0f}% (sharp loss)", annotation_position="bottom left")
    callout(". ".join(parts) + ". The crops follow a similar path.")
    style(fig, 340).update_yaxes(title="Yield compared with normal (%)").update_xaxes(title="Days at or above 35 °C (95 °F) this season")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    question(6, "Once soil quality is accounted for, how much of the yield gap between counties is left for drought to explain?",
             "Within each year, we compared every county's yield with the average county that year, so the rising trend over time doesn't count. First we measured how much of that gap soil quality (nccpi_crop) explains. "
             "Then we added drought (weeks in D2 or worse and mean DSCI) and measured how much more it explains. Figures are shares of the county-to-county gap. Nebraska is shown too, but irrigation hides "
             "much of what soil and drought do there.")
    q6 = rs["q6"]
    ia6, ne6 = q6["IA"], q6["NE"]
    callout(f"Soil quality explains <b>{ia6['soil']:.1%}</b> of the county-to-county yield gap in Iowa {crop_name}. With soil accounted for, drought explains <b>{ia6['drought']:.1%}</b> more, and about "
            f"<b>{ia6['rest']:.0%}</b> of the gap is explained by neither. In Nebraska, soil explains {ne6['soil']:.1%} and drought adds {ne6['drought']:.1%}. Drought is a real but small part of the gap between counties.")
    fig = go.Figure()
    for key, label, color in (("soil", "Soil quality", FOREST), ("drought", "Drought, added after soil", AMBER)):
        fig.add_trace(go.Bar(x=[STATE_NAMES[a] for a in ("IA", "NE")], y=[q6[a][key] * 100 for a in ("IA", "NE")], name=label, marker_color=color,
                             text=[f"{q6[a][key]:.1%}" for a in ("IA", "NE")], **BAR_TEXT))
    fig.update_layout(barmode="group")
    style(fig, 300).update_yaxes(title="Share of the county-to-county yield gap explained (%)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def show(record):
    ss = st.session_state
    crop = ss.crop
    fips = ss.get("fips") or data.counties().fips.iloc[0]
    state = data.counties().set_index("fips").state_alpha[fips]
    st.caption("History uses the county, crop and state you chose on the Outlook tab.")
    with st.spinner("Loading the records..."):
        same_label(crop)
        held_up(crop, state)
        county_story(fips, crop)
        states_differ(crop)
        six_questions(crop)
