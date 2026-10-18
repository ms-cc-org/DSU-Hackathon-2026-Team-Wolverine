"""Nebraska and Iowa only: turn typed text into a supported county, or refuse it."""
import re

from droughtlens import data

SUPPORT_MESSAGE = "DroughtLens currently supports farmers in Nebraska and Iowa. Select a supported location to continue."

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington state": "WA", "west virginia": "WV", "wisconsin": "WI",
    "wyoming": "WY", "district of columbia": "DC",
}


def resolve_location(text):
    """Returns (status, fips, message).

    status is 'ok' (a supported county), 'ambiguous' (the county name exists in both states), 'unsupported'
    (outside Nebraska and Iowa, or not a county we have) or 'empty'. Nothing is ever substituted silently.
    """
    t = " ".join(re.sub(r"[,.]", " ", text.lower()).split())
    if not t:
        return "empty", None, ""

    named = {abbr for name, abbr in US_STATES.items() if re.search(rf"\b{re.escape(name)}\b", t)}
    tokens = t.split()
    if len(tokens) > 1 and len(tokens[-1]) == 2 and tokens[-1].upper() in US_STATES.values():
        named.add(tokens[-1].upper())
    if named - set(data.STATE_NAMES):
        return "unsupported", None, SUPPORT_MESSAGE

    # strip state words and 'county' to leave the county name
    for name in US_STATES:
        t = re.sub(rf"\b{re.escape(name)}\b", " ", t)
    if tokens and len(tokens[-1]) == 2 and tokens[-1].upper() in {"NE", "IA"}:
        t = re.sub(rf"\b{tokens[-1]}\b", " ", t)
    t = " ".join(re.sub(r"\bcounty\b", " ", t).split())
    if not t:
        return "unsupported", None, SUPPORT_MESSAGE

    cs = data.counties()
    cs = cs.assign(key=cs.county_name.str.lower().str.replace(" county", "", regex=False))
    hits = cs[cs.key == t]
    if named:
        hits = hits[hits.state_alpha.isin(named)]
    if hits.empty:
        return "unsupported", None, SUPPORT_MESSAGE
    if len(hits) > 1:
        return "ambiguous", None, f"{hits.county_name.iloc[0]} exists in both Nebraska and Iowa. Add the state, for example “{hits.county_name.iloc[0]}, Iowa”."
    row = hits.iloc[0]
    return "ok", row.fips, f"{row.county_name}, {data.STATE_NAMES[row.state_alpha]}"
