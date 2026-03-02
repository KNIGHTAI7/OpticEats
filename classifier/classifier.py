"""
OpticEats — Stage 3: Ingredient Classifier
============================================
Classifies each ingredient as GOOD / BAD / NEUTRAL with a reason.

Classification priority (highest to lowest):
  1. E-number lookup      — most reliable, specific
  2. Exact name match     — direct knowledge base hit
  3. Partial name match   — handles OCR variants
  4. Keyword match        — catches broad patterns
  5. LLM fallback         — for unknown ingredients (optional)
  6. Default NEUTRAL      — when nothing matches

Each new unknown ingredient is logged to unknown_ingredients.log
so you can manually add them to the knowledge base over time.
This is how the model "learns" — the KB grows with usage.
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# LOAD KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────────────────────

KB_PATH = Path(__file__).parent / "knowledge_base.json"

def load_knowledge_base() -> dict:
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

_KB = None

def get_kb() -> dict:
    global _KB
    if _KB is None:
        _KB = load_knowledge_base()
    return _KB


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICATION RESULT STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

def make_result(name, label, reason, method, e_name=None):
    return {
        "name"        : name,
        "label"       : label,       # "GOOD" / "BAD" / "NEUTRAL"
        "reason"      : reason,
        "method"      : method,      # how it was classified
        "e_name"      : e_name,      # e-number full name if applicable
        "emoji"       : {"GOOD": "🟢", "BAD": "🔴", "NEUTRAL": "🟡"}.get(label, "⚪")
    }


# ─────────────────────────────────────────────────────────────────────────────
# PRIORITY 1 — E-NUMBER LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def classify_by_enumber(enumber: str) -> dict | None:
    """
    Looks up an e-number code in the knowledge base.
    Tries exact match first, then strips roman numeral suffix.

    Example:
        "322(i)" -> tries "322(i)", then "322"
        "500(ii)" -> tries "500(ii)", then "500"
    """
    kb = get_kb()
    edb = kb.get("e_numbers", {})
    code = enumber.strip().lower()

    # Exact match
    if code in edb:
        entry = edb[code]
        return make_result(
            name   = f"E{code.upper()}",
            label  = entry["label"],
            reason = entry["reason"],
            method = "e_number_exact",
            e_name = entry["name"]
        )

    # Try stripping roman numeral: 322(i) -> 322
    base = re.sub(r'\([ivxIVX]+\)$', '', code).strip()
    if base in edb:
        entry = edb[base]
        return make_result(
            name   = f"E{code.upper()}",
            label  = entry["label"],
            reason = entry["reason"],
            method = "e_number_base",
            e_name = entry["name"]
        )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# PRIORITY 2 — EXACT NAME MATCH
# ─────────────────────────────────────────────────────────────────────────────

def classify_by_exact_name(name: str) -> dict | None:
    """Exact lookup of ingredient name in knowledge base (case-insensitive)."""
    kb  = get_kb()
    idb = kb.get("ingredients", {})
    key = name.strip().upper()

    if key in idb:
        entry = idb[key]
        return make_result(
            name   = name,
            label  = entry["label"],
            reason = entry["reason"],
            method = "exact_match"
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PRIORITY 3 — PARTIAL NAME MATCH
# Handles OCR variants and abbreviations
# ─────────────────────────────────────────────────────────────────────────────

def classify_by_partial_name(name: str) -> dict | None:
    """
    Checks if any known ingredient name is contained within the
    given name, or vice versa. Handles OCR-merged strings.

    Example:
        "RAISING AGENTS (VANILLA)" still matches "RAISING AGENTS"
        "DOUGH CONDITIONER" matches "DOUGH CONDITIONER"
    """
    kb  = get_kb()
    idb = kb.get("ingredients", {})
    name_upper = name.strip().upper()

    best_match     = None
    best_match_len = 0

    for known_key, entry in idb.items():
        # Check if known key is inside our name (e.g. "RAISING AGENTS" in "RAISING AGENTS (VANILLA)")
        if known_key in name_upper:
            if len(known_key) > best_match_len:
                best_match_len = len(known_key)
                best_match     = (known_key, entry)

        # Check if our name is inside known key (handles abbreviations)
        elif name_upper in known_key and len(name_upper) > 4:
            if len(name_upper) > best_match_len:
                best_match_len = len(name_upper)
                best_match     = (known_key, entry)

    if best_match:
        known_key, entry = best_match
        return make_result(
            name   = name,
            label  = entry["label"],
            reason = entry["reason"],
            method = f"partial_match → {known_key}"
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PRIORITY 4 — KEYWORD MATCH
# ─────────────────────────────────────────────────────────────────────────────

def classify_by_keywords(name: str) -> dict | None:
    """
    Checks ingredient name against keyword lists for broad pattern matching.
    Example: anything containing "hydrogenated" -> BAD
    """
    kb       = get_kb()
    keywords = kb.get("ingredient_keywords", {})
    name_lower = name.strip().lower()

    # Check BAD keywords first (most important to catch)
    for kw in keywords.get("BAD", []):
        if kw.lower() in name_lower:
            return make_result(
                name   = name,
                label  = "BAD",
                reason = f"Contains '{kw}' — associated with harmful food additives.",
                method = f"keyword_match → {kw}"
            )

    # Then GOOD
    for kw in keywords.get("GOOD", []):
        if kw.lower() in name_lower:
            return make_result(
                name   = name,
                label  = "GOOD",
                reason = f"Contains '{kw}' — associated with healthy ingredients.",
                method = f"keyword_match → {kw}"
            )

    # Then NEUTRAL
    for kw in keywords.get("NEUTRAL", []):
        if kw.lower() in name_lower:
            return make_result(
                name   = name,
                label  = "NEUTRAL",
                reason = f"Contains '{kw}' — generally safe additive.",
                method = f"keyword_match → {kw}"
            )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# PRIORITY 5 — LLM FALLBACK (Optional)
# Uses Anthropic API if API key is available
# ─────────────────────────────────────────────────────────────────────────────

def classify_by_llm(name: str) -> dict | None:
    """
    Fallback classifier using an LLM for unknown ingredients.
    Requires ANTHROPIC_API_KEY environment variable to be set.

    Setup:
        Windows: set ANTHROPIC_API_KEY=your_key_here
        Linux/Mac: export ANTHROPIC_API_KEY=your_key_here

    Returns classification dict or None if API unavailable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You are a food safety expert. Classify this food ingredient:

Ingredient: {name}

Respond in EXACTLY this JSON format with no extra text:
{{
  "label": "GOOD" or "BAD" or "NEUTRAL",
  "reason": "One clear sentence explaining why."
}}

Guidelines:
- GOOD: Natural, nutritious, or beneficial ingredients
- BAD: Harmful, ultra-processed, or linked to health issues
- NEUTRAL: Safe but not particularly beneficial or harmful"""

        message = client.messages.create(
            model      = "claude-haiku-4-5-20251001",
            max_tokens = 150,
            messages   = [{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text.strip()
        # Clean markdown fences if present
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        data = json.loads(raw)
        label  = data.get("label", "NEUTRAL").upper()
        reason = data.get("reason", "Classified by AI.")

        if label not in ("GOOD", "BAD", "NEUTRAL"):
            label = "NEUTRAL"

        return make_result(
            name   = name,
            label  = label,
            reason = reason,
            method = "llm_fallback"
        )

    except Exception as e:
        print(f"[OpticEats Classifier] LLM fallback failed for '{name}': {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LOG UNKNOWN INGREDIENTS
# This is how OpticEats "learns" over time
# ─────────────────────────────────────────────────────────────────────────────

LOG_PATH = Path(__file__).parent / "unknown_ingredients.log"

def log_unknown(name: str):
    """Logs unrecognised ingredients so they can be added to the KB later."""
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | UNKNOWN | {name}\n")


# ─────────────────────────────────────────────────────────────────────────────
# MASTER CLASSIFY FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def classify_ingredient(ingredient: dict) -> dict:
    """
    Classifies a single parsed ingredient dict from Stage 2.

    Args:
        ingredient: {"name": str, "percentage": float|None, "e_numbers": list[str], "raw": str}

    Returns:
        Extended dict with added fields:
        {
          ...original fields...,
          "label"       : "GOOD" / "BAD" / "NEUTRAL",
          "reason"      : str,
          "method"      : str,
          "emoji"       : "🟢" / "🔴" / "🟡",
          "e_details"   : list[dict]   # classification of each e-number
        }
    """
    name      = ingredient.get("name", "")
    enumbers  = ingredient.get("e_numbers", [])
    result    = None

    # ── Step 1: Classify e-numbers (they override ingredient label if BAD) ──
    e_details = []
    has_bad_enumber = False
    for ecode in enumbers:
        e_result = classify_by_enumber(ecode)
        if e_result:
            e_details.append(e_result)
            if e_result["label"] == "BAD":
                has_bad_enumber = True
        else:
            e_details.append(make_result(
                name   = ecode,
                label  = "NEUTRAL",
                reason = "E-number not in knowledge base. Generally safe — verify if concerned.",
                method = "e_number_unknown"
            ))

    # ── Step 2: Classify the ingredient name ──
    result = (
        classify_by_exact_name(name)   or
        classify_by_partial_name(name) or
        classify_by_keywords(name)     or
        classify_by_llm(name)
    )

    # ── Step 3: If has BAD e-number, ingredient is BAD regardless of name match ──
    if has_bad_enumber:
        bad_e_names = [
            e.get("e_name", e["name"])
            for e in e_details if e["label"] == "BAD"
        ]
        bad_reason = f"Contains harmful additive(s): {', '.join(bad_e_names)}."
        if result is None:
            # No name match — classify entirely from e-number
            result = make_result(
                name   = name,
                label  = "BAD",
                reason = bad_reason,
                method = "e_number_driven"
            )
        elif result["label"] != "BAD":
            # Name matched as good/neutral but e-number overrides
            result["label"]  = "BAD"
            result["reason"] += f" However, {bad_reason}"
            result["emoji"]  = "🔴"

    # ── Step 4: Default to NEUTRAL if nothing matched ──
    if result is None:
        log_unknown(name)
        result = make_result(
            name   = name,
            label  = "NEUTRAL",
            reason = "Ingredient not in knowledge base. Logged for future review.",
            method = "default_neutral"
        )

    # Merge everything back
    return {
        **ingredient,
        "label"    : result["label"],
        "reason"   : result["reason"],
        "method"   : result["method"],
        "emoji"    : result["emoji"],
        "e_details": e_details
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFY ALL INGREDIENTS
# ─────────────────────────────────────────────────────────────────────────────

def classify_ingredients(ingredients: list[dict]) -> list[dict]:
    """
    Classifies all ingredients from Stage 2 parser output.

    Args:
        ingredients: list of dicts from parse_ingredients()

    Returns:
        Same list with label, reason, emoji and e_details added to each item.
    """
    print("\n[OpticEats Classifier] Starting Stage 3 — Classification...")
    print(f"[OpticEats Classifier] Classifying {len(ingredients)} ingredients\n")

    classified = []
    for ing in ingredients:
        result = classify_ingredient(ing)
        classified.append(result)
        print(f"  {result['emoji']}  [{result['label']:<7}]  {result['name']}"
              + (f"  (method: {result['method']})" if "unknown" in result.get("method","") or "default" in result.get("method","") else ""))

    good    = sum(1 for r in classified if r["label"] == "GOOD")
    bad     = sum(1 for r in classified if r["label"] == "BAD")
    neutral = sum(1 for r in classified if r["label"] == "NEUTRAL")

    print(f"\n[OpticEats Classifier] Done — 🟢 {good} GOOD  🔴 {bad} BAD  🟡 {neutral} NEUTRAL\n")
    return classified


def summarise_classification(classified: list[dict]) -> str:
    """Returns a formatted terminal-friendly classification summary."""
    good    = [i for i in classified if i["label"] == "GOOD"]
    bad     = [i for i in classified if i["label"] == "BAD"]
    neutral = [i for i in classified if i["label"] == "NEUTRAL"]

    lines = [f"\n{'═'*60}"]
    lines.append("  OpticEats — Ingredient Classification Report")
    lines.append(f"{'═'*60}")

    lines.append(f"\n  🟢 GOOD ({len(good)})")
    lines.append(f"  {'─'*56}")
    for i in good:
        lines.append(f"  ✔  {i['name']}")
        lines.append(f"     {i['reason']}")

    lines.append(f"\n  🔴 BAD ({len(bad)})")
    lines.append(f"  {'─'*56}")
    for i in bad:
        lines.append(f"  ✘  {i['name']}")
        lines.append(f"     {i['reason']}")
        for e in i.get("e_details", []):
            if e["label"] == "BAD":
                lines.append(f"     ⚗  E{e['name']} — {e['reason']}")

    lines.append(f"\n  🟡 NEUTRAL ({len(neutral)})")
    lines.append(f"  {'─'*56}")
    for i in neutral:
        lines.append(f"  ●  {i['name']}")

    lines.append(f"\n{'═'*60}\n")
    return "\n".join(lines)
