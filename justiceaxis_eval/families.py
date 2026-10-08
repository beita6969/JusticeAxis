"""Charge normalisation, charge components and charge families.

`charge_families` maps a free-text charge label to one or more offence families with keyword rules. The rules are
ordered; the family of an offence is the first rule that matches its text. A custom table (a JSON list of
[family, [regex, ...]] pairs) can replace the defaults with `load_family_map`.
"""
import json
import re

DEFAULT_FAMILIES = [
    ("homicide", [r"\bmurder", r"manslaughter", r"homicide", r"causing death", r"death by (dangerous|careless)", r"killing"]),
    ("sexual", [r"\brape", r"sexual", r"indecent", r"child (abuse|sex)"]),
    ("terrorism_state", [r"terror", r"treason", r"espionage", r"national security"]),
    ("trafficking_slavery", [r"traffick", r"slavery", r"modern slavery", r"people smuggling", r"immigration"]),
    ("kidnap_imprisonment", [r"kidnap", r"false imprisonment", r"abduct", r"hostage"]),
    ("robbery", [r"\brobber"]),
    ("firearms_weapons", [r"firearm", r"\bgun\b", r"shotgun", r"ammunition", r"weapon", r"\bknife\b", r"\bblade", r"bladed", r"imitation"]),
    ("violence", [r"assault", r"wound", r"grievous", r"actual bodily", r"\babh\b", r"\bgbh\b", r"battery", r"violence", r"bodily harm", r"strangulation", r"injur", r"torture", r"degrading treatment"]),
    ("harassment_threats", [r"harass", r"stalk", r"threat", r"intimidat", r"coercive", r"fear (of|or) violence"]),
    ("public_order", [r"affray", r"riot", r"violent disorder", r"public order", r"disorderly", r"nuisance", r"breach of the peace"]),
    ("criminal_damage_arson", [r"criminal damage", r"arson", r"damag", r"vandal"]),
    ("drugs", [r"drug", r"controlled substance", r"cannabis", r"cocaine", r"heroin", r"class [abc]\b", r"supply", r"narcotic", r"possession with intent"]),
    ("fraud_financial", [r"fraud", r"laundering", r"forgery", r"bribe", r"corruption", r"false representation", r"embezzle", r"criminal property"]),
    ("theft_burglary", [r"theft", r"\bsteal", r"burglar", r"handling stolen", r"shoplift", r"taking (a )?(vehicle|conveyance)", r"vehicle taking", r"larceny", r"trespass"]),
    ("road_traffic", [r"driving", r"\bdrive", r"road traffic", r"speeding", r"disqualif", r"insurance", r"licen[cs]e", r"vehicle", r"failing to stop", r"drink", r"motoring", r"traffic"]),
    ("justice_obstruction", [r"perver", r"obstruct", r"resist", r"escape", r"contempt", r"perjury", r"misconduct in public office", r"conceal"]),
    ("animal_environment", [r"poach", r"wildlife", r"animal", r"environment", r"game act", r"fishing"]),
    ("child_welfare", [r"child neglect", r"neglect", r"cruelty to a child", r"endanger"]),
]

_STOP = {"the", "a", "an", "of", "and", "to", "in", "for", "with", "by", "on", "at", "as"}
_COUNTWORDS = {"count", "counts", "charge", "charges", "charged", "reported", "alleged", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"}
_STATUTE = re.compile(r"\b(s\.?|ss\.?|sec\.?|section|sections|art\.?|article|articles)\s*\d+[a-z]?(\(\w+\))*|\b\d{4}\b|\b(act|code|law|regulations?)\b", re.I)


def normalise_component(text):
    t = (text or "").lower()
    t = re.sub(r"\([^)]*\)", " ", t)
    t = _STATUTE.sub(" ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    words = [w for w in t.split() if w not in _STOP and w not in _COUNTWORDS and not w.isdigit()]
    return " ".join(words)


def charge_components(charge):
    """Split a charge label into normalised offence components (a set)."""
    if not charge:
        return frozenset()
    parts = re.split(r";|\band\b|,|/|\bplus\b", str(charge), flags=re.I)
    comps = {normalise_component(p) for p in parts}
    comps.discard("")
    return frozenset(comps)


def load_family_map(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [(fam, list(pats)) for fam, pats in raw]


def _compile(table):
    return [(fam, [re.compile(p, re.I) for p in pats]) for fam, pats in table]


_DEFAULT_COMPILED = _compile(DEFAULT_FAMILIES)


def charge_families(charge, family_table=None):
    """Ordered list of families named by a charge label (first = primary). Unknown offences give ['other']."""
    compiled = _DEFAULT_COMPILED if family_table is None else _compile(family_table)
    fams = []
    for part in re.split(r";|\band\b|,|/", str(charge or ""), flags=re.I):
        part = part.strip()
        if not part:
            continue
        hit = None
        for fam, pats in compiled:
            if any(p.search(part) for p in pats):
                hit = fam
                break
        fams.append(hit or "other")
    out = []
    for f in fams:
        if f not in out:
            out.append(f)
    return out or ["other"]
