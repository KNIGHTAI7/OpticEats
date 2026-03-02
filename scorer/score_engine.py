"""
OpticEats — Stage 4: Score Engine (v3 — Context-Aware)
==========================================================
Key improvements in v3:
  - GOOD + NEUTRAL together are measured as "safe ingredient ratio"
  - BAD at high position = heavy penalty; BAD at low position = minor penalty
  - Product gets more credit when neutrals dominate (e.g. cocoa, cocoa butter)
  - Percentage-aware bonuses and penalties
"""

SCORE_CATEGORIES = [
    (0.0,  3.0,  "BAD",       "🔴", "This product contains mostly harmful or ultra-processed ingredients. Avoid regular consumption."),
    (3.0,  5.0,  "AVERAGE",   "🟠", "This product has a mix of good and bad ingredients. Consume occasionally and in moderation."),
    (5.0,  7.0,  "GOOD",      "🟡", "This product is reasonably healthy. A decent choice for occasional consumption."),
    (7.0,  10.1, "EXCELLENT", "🟢", "This product is made with mostly healthy ingredients. A great choice!"),
]


def get_category(score):
    for low, high, name, emoji, note in SCORE_CATEGORIES:
        if low <= score < high:
            return {"name": name, "emoji": emoji, "note": note}
    return {"name": "BAD", "emoji": "🔴", "note": SCORE_CATEGORIES[0][4]}


def factor_label_ratio(classified):
    """
    Core ratio — treats GOOD and NEUTRAL as positive, BAD as negative.
    Formula:
      score = ((good * 1.0 + neutral * 0.6) / total) * 10  - (bad/total) * 5
    This means:
      - All GOOD = 10.0
      - All NEUTRAL = 6.0 (neutral products are decent, not bad)
      - All BAD = 0.0 after penalty
    """
    total   = len(classified)
    good    = sum(1 for i in classified if i["label"] == "GOOD")
    bad     = sum(1 for i in classified if i["label"] == "BAD")
    neutral = total - good - bad

    positive = (good * 1.0 + neutral * 0.7) / total * 10
    penalty  = (bad / total) * 5
    score    = max(0.0, min(10.0, positive - penalty))

    note = (f"Label ratio: {good}G/{bad}B/{neutral}N of {total} "
            f"→ positive={positive:.1f} penalty={penalty:.1f}")
    return score, note


def factor_position_weight(classified):
    """
    BAD in top positions = heavy penalty (high quantity by law).
    BAD in lower positions = minor penalty (trace amount).
    GOOD as first = bonus.
    """
    delta   = 0.0
    details = []

    for i, ing in enumerate(classified):
        if ing["label"] == "BAD":
            if i == 0:
                delta -= 2.0
                details.append(f"'{ing['name']}' pos 1 (-2.0)")
            elif i <= 2:
                delta -= 0.8
                details.append(f"'{ing['name']}' pos {i+1} (-0.8)")
            elif i <= 5:
                delta -= 0.3
                details.append(f"'{ing['name']}' pos {i+1} (-0.3)")
            else:
                delta -= 0.1
                details.append(f"'{ing['name']}' pos {i+1} (-0.1)")

        elif ing["label"] == "GOOD" and i == 0:
            delta += 0.8
            details.append(f"'{ing['name']}' is first (+0.8)")

    note = f"Position weight: {delta:+.1f}" + (f" ({'; '.join(details)})" if details else "")
    return delta, note


def factor_enumber_penalty(classified):
    """Each confirmed BAD e-number = -0.3"""
    bad_enums = []
    for ing in classified:
        for e in ing.get("e_details", []):
            if e["label"] == "BAD":
                bad_enums.append(e.get("e_name", e["name"]))
    penalty = len(bad_enums) * 0.3
    note    = (f"E-number penalty: -{penalty:.1f} "
               f"({len(bad_enums)} harmful: {', '.join(bad_enums) if bad_enums else 'none'})")
    return -penalty, note


def factor_percentage(classified):
    """
    Explicit percentage bonus/penalty.
    GOOD at 50%+ = big bonus (dominant healthy ingredient).
    BAD at 20%+  = big penalty (dominant harmful ingredient).
    """
    delta   = 0.0
    details = []
    for ing in classified:
        pct = ing.get("percentage")
        if pct is None:
            continue
        if ing["label"] == "GOOD":
            if pct >= 50:
                delta += 1.0
                details.append(f"'{ing['name']}' {pct}% dominant GOOD (+1.0)")
            elif pct >= 30:
                delta += 0.6
                details.append(f"'{ing['name']}' {pct}% major GOOD (+0.6)")
            elif pct >= 10:
                delta += 0.3
                details.append(f"'{ing['name']}' {pct}% (+0.3)")
        elif ing["label"] == "NEUTRAL":
            if pct >= 50:
                delta += 0.5
                details.append(f"'{ing['name']}' {pct}% dominant NEUTRAL (+0.5)")
            elif pct >= 20:
                delta += 0.2
                details.append(f"'{ing['name']}' {pct}% (+0.2)")
        elif ing["label"] == "BAD":
            if pct >= 30:
                delta -= 1.5
                details.append(f"'{ing['name']}' {pct}% dominant BAD (-1.5)")
            elif pct >= 15:
                delta -= 0.8
                details.append(f"'{ing['name']}' {pct}% (-0.8)")
            elif pct >= 5:
                delta -= 0.3
                details.append(f"'{ing['name']}' {pct}% (-0.3)")

    note = f"Percentage factor: {delta:+.2f}" + (f" ({'; '.join(details)})" if details else "")
    return delta, note


def calculate_score(classified):
    if not classified:
        return {
            "score": 0.0, "category": "BAD", "emoji": "🔴",
            "note": "No ingredients found.", "breakdown": [],
            "good_list": [], "bad_list": [], "neutral_list": [], "highlights": {}
        }

    print("\n[OpticEats Score] Calculating OpticEats Score...")

    f1_score, f1_note = factor_label_ratio(classified)
    f2_delta, f2_note = factor_position_weight(classified)
    f3_delta, f3_note = factor_enumber_penalty(classified)
    f4_delta, f4_note = factor_percentage(classified)

    raw_score   = f1_score + f2_delta + f3_delta + f4_delta
    final_score = round(max(0.0, min(10.0, raw_score)), 1)

    print(f"  F1 Label ratio    : {f1_score:+.2f}  {f1_note}")
    print(f"  F2 Position weight: {f2_delta:+.2f}  {f2_note}")
    print(f"  F3 E-num penalty  : {f3_delta:+.2f}  {f3_note}")
    print(f"  F4 Percentage     : {f4_delta:+.2f}  {f4_note}")
    print(f"  {'─'*50}")
    print(f"  Raw: {raw_score:.2f}  →  Final: {final_score} / 10.0")

    category = get_category(final_score)
    print(f"  Category: {category['emoji']} {category['name']}\n")

    good_list    = [i["name"] for i in classified if i["label"] == "GOOD"]
    bad_list     = [i["name"] for i in classified if i["label"] == "BAD"]
    neutral_list = [i["name"] for i in classified if i["label"] == "NEUTRAL"]

    bad_enums = []
    for ing in classified:
        for e in ing.get("e_details", []):
            if e["label"] == "BAD":
                bad_enums.append(e.get("e_name", e["name"]))

    total = len(classified)
    highlights = {
        "total_ingredients"   : total,
        "good_count"          : len(good_list),
        "bad_count"           : len(bad_list),
        "neutral_count"       : len(neutral_list),
        "bad_percentage"      : round((len(bad_list) / total) * 100),
        "harmful_enumbers"    : bad_enums,
        "top_ingredient"      : classified[0]["name"] if classified else "",
        "top_ingredient_label": classified[0]["label"] if classified else "",
    }

    return {
        "score"        : final_score,
        "category"     : category["name"],
        "emoji"        : category["emoji"],
        "note"         : category["note"],
        "breakdown"    : [f1_note, f2_note, f3_note, f4_note,
                          f"Raw: {raw_score:.2f} → Final: {final_score}"],
        "good_list"    : good_list,
        "bad_list"     : bad_list,
        "neutral_list" : neutral_list,
        "highlights"   : highlights
    }


def display_score(score_result):
    score    = score_result["score"]
    category = score_result["category"]
    emoji    = score_result["emoji"]
    hl       = score_result["highlights"]
    bar      = "█" * int(score) + "░" * (10 - int(score))

    print("\n" + "═"*60)
    print(f"  {'OpticEats Score':^56}")
    print("═"*60)
    print(f"\n  {emoji}  {score} / 10.0   [{category}]")
    print(f"  [{bar}]")
    print(f"\n  {score_result['note']}")
    print(f"\n  🟢{hl['good_count']}  🔴{hl['bad_count']}  🟡{hl['neutral_count']}  of {hl['total_ingredients']}")
    if hl["harmful_enumbers"]:
        print(f"  🧪 {', '.join(hl['harmful_enumbers'])}")
    print(f"\n  Breakdown:")
    for line in score_result["breakdown"]:
        print(f"    • {line}")
    guide = [(0,3,"BAD","🔴"),(3,5,"AVERAGE","🟠"),(5,7,"GOOD","🟡"),(7,10,"EXCELLENT","🟢")]
    print("\n  Score Guide:")
    for low, high, name, em in guide:
        marker = "  ◀ YOU ARE HERE" if category == name else ""
        print(f"    {em}  {low}–{high}  {name}{marker}")
    print("\n" + "═"*60 + "\n")
