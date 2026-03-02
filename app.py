"""
OpticEats — Streamlit App (v2)
================================
Fix 1: Native Streamlit components replace raw HTML tables (no more raw HTML bleed)
Fix 2: Smarter score engine v2 imported
Run with: streamlit run app.py
"""

import sys
import time
import tempfile
import os
from pathlib import Path

import streamlit as st
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

from ocr.extractor import extract_ingredients_text
from parser.ingredient_parser import parse_ingredients
from classifier.classifier import classify_ingredients
from scorer.score_engine import calculate_score, get_category


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="OpticEats",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Only global styles + score card. NO table HTML.
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;700;900&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0E1A14; color: #EDEAE2; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1150px; }

/* Header */
.oe-header   { text-align:center; padding:2.5rem 0 0.5rem 0; }
.oe-logo-row { display:flex; align-items:center; justify-content:center; gap:18px; margin-bottom:6px; }
.oe-title    { font-family:'Raleway',sans-serif; font-size:3rem; font-weight:900;
               color:#EDEAE2; letter-spacing:-2px; line-height:1; margin:0; }
.oe-title span { color:#4CAF7D; font-weight:300; }
.oe-tagline  { font-size:11px; letter-spacing:4px; text-transform:uppercase;
               color:#4CAF7D; opacity:0.7; margin-top:6px; }
.oe-divider  { border:none; border-top:1px solid rgba(76,175,125,0.2);
               margin:1.5rem auto; max-width:500px; }

/* Section labels */
.section-label { font-size:10px; letter-spacing:3px; text-transform:uppercase;
                 color:#4CAF7D; opacity:0.8; margin-bottom:8px; }

/* Streamlit widget overrides */
div[data-baseweb="select"] > div { background:#162B1E !important;
    border:1px solid rgba(76,175,125,0.3) !important; border-radius:10px !important; }
.stFileUploader > div { background:#162B1E !important;
    border:2px dashed rgba(76,175,125,0.3) !important; border-radius:12px !important; }
.stButton > button { background:#4CAF7D !important; color:#0E1A14 !important;
    font-family:'Raleway',sans-serif !important; font-weight:700 !important;
    font-size:15px !important; letter-spacing:1px !important;
    border:none !important; border-radius:10px !important;
    padding:0.6rem 2rem !important; width:100% !important; }
.stButton > button:hover { opacity:0.85 !important; }

/* Stat boxes */
.stat-box    { background:#162B1E; border:1px solid rgba(76,175,125,0.15);
               border-radius:12px; padding:1rem; text-align:center; }
.stat-number { font-family:'Raleway',sans-serif; font-size:2rem; font-weight:900; line-height:1; }
.stat-label  { font-size:10px; letter-spacing:2px; text-transform:uppercase;
               color:rgba(237,234,226,0.45); margin-top:4px; }

/* Score card */
.score-card  { background:#162B1E; border:1px solid rgba(76,175,125,0.2);
               border-radius:20px; padding:2rem 2.5rem; text-align:center; }
.score-number{ font-family:'Raleway',sans-serif; font-size:5rem; font-weight:900;
               line-height:1; letter-spacing:-3px; }
.score-denom { font-size:1.5rem; font-weight:300; color:rgba(237,234,226,0.4); }
.score-badge { display:inline-block; font-family:'Raleway',sans-serif; font-size:13px;
               font-weight:700; letter-spacing:3px; text-transform:uppercase;
               padding:5px 18px; border-radius:30px; margin-top:8px; }
.badge-bad      { background:rgba(255,107,107,0.15); color:#FF6B6B; border:1px solid rgba(255,107,107,0.3); }
.badge-average  { background:rgba(255,165,0,0.15);   color:#FFA500; border:1px solid rgba(255,165,0,0.3); }
.badge-good     { background:rgba(255,209,102,0.15); color:#FFD166; border:1px solid rgba(255,209,102,0.3); }
.badge-excellent{ background:rgba(76,175,125,0.15);  color:#4CAF7D; border:1px solid rgba(76,175,125,0.3); }
.score-bar-bg  { background:rgba(255,255,255,0.07); border-radius:99px; height:8px;
                 margin:1.2rem auto; max-width:280px; overflow:hidden; }
.score-bar-fill{ height:100%; border-radius:99px; }
.score-note    { font-size:13px; color:rgba(237,234,226,0.65); margin-top:0.8rem; line-height:1.5; }
.guide-row     { display:flex; align-items:center; gap:10px; padding:6px 0;
                 border-bottom:1px solid rgba(255,255,255,0.05); font-size:13px; }
.guide-row:last-child { border-bottom:none; }
.guide-dot     { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
.guide-here    { font-size:10px; letter-spacing:2px; text-transform:uppercase;
                 color:#4CAF7D; margin-left:auto; }

/* Ingredient pills (used in native rendering) */
.ing-pill { display:inline-block; border-radius:6px; padding:3px 10px;
            font-size:12px; font-weight:600; margin:3px 3px 3px 0; }
.pill-good    { background:rgba(76,175,125,0.15); color:#4CAF7D; border:1px solid rgba(76,175,125,0.3); }
.pill-bad     { background:rgba(255,107,107,0.15); color:#FF6B6B; border:1px solid rgba(255,107,107,0.3); }
.pill-neutral { background:rgba(255,209,102,0.12); color:#FFD166; border:1px solid rgba(255,209,102,0.25); }
.enum-tag  { display:inline-block; background:rgba(76,175,125,0.1); border:1px solid rgba(76,175,125,0.2);
             border-radius:4px; font-size:10px; padding:1px 5px; margin:2px 2px 0 0; color:#4CAF7D; }

/* Note box */
.note-box     { border-radius:12px; padding:1rem 1.2rem; margin-top:1rem; }
.note-bad     { background:rgba(255,107,107,0.08); border:1px solid rgba(255,107,107,0.2); }
.note-average { background:rgba(255,165,0,0.08);   border:1px solid rgba(255,165,0,0.2); }
.note-good    { background:rgba(255,209,102,0.08); border:1px solid rgba(255,209,102,0.2); }
.note-excellent{background:rgba(76,175,125,0.08);  border:1px solid rgba(76,175,125,0.2); }
.note-title   { font-family:'Raleway',sans-serif; font-weight:700; font-size:13px;
                letter-spacing:1px; text-transform:uppercase; margin-bottom:4px; }
.note-text    { font-size:13px; color:rgba(237,234,226,0.75); line-height:1.6; }

/* Disclaimer */
.disclaimer { font-size:11px; color:rgba(237,234,226,0.3); text-align:center;
              margin-top:2.5rem; padding-top:1rem;
              border-top:1px solid rgba(76,175,125,0.1); line-height:1.6; }

/* How it works card */
.how-card { background:#162B1E; border:1px solid rgba(76,175,125,0.15);
            border-radius:16px; padding:1.8rem; }
.step-num { width:28px; height:28px; border-radius:50%;
            background:rgba(76,175,125,0.15); border:1px solid rgba(76,175,125,0.3);
            display:flex; align-items:center; justify-content:center;
            font-size:12px; color:#4CAF7D; flex-shrink:0; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

SCORE_COLOR = {"BAD":"#FF6B6B","AVERAGE":"#FFA500","GOOD":"#FFD166","EXCELLENT":"#4CAF7D"}

CATEGORIES = [
    "🍪 Biscuits & Snacks","🥛 Dairy Products","🥤 Beverages",
    "🥣 Cereals & Breakfast","🍫 Chocolate & Confectionery",
    "🍝 Ready-to-eat / Instant","🧂 Condiments & Sauces",
    "🍞 Bread & Bakery","🥫 Packaged / Canned","🔮 Other",
]


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(image_path):
    with st.spinner("🔍 Reading ingredients from image..."):
        ocr_result = extract_ingredients_text(image_path)
    if not ocr_result["success"]:
        st.error(f"OCR failed: {ocr_result.get('error','Unknown')}")
        return None, None, None, None

    with st.spinner("🔬 Identifying ingredients..."):
        parsed = parse_ingredients(ocr_result["clean_text"])
    if not parsed:
        st.error("No ingredients could be parsed. Please try a clearer photo.")
        return None, None, None, None

    with st.spinner("🧠 Classifying ingredients..."):
        classified = classify_ingredients(parsed)

    with st.spinner("📊 Calculating OpticEats Score..."):
        score_result = calculate_score(classified)
        time.sleep(0.2)

    return ocr_result, parsed, classified, score_result


# ─────────────────────────────────────────────────────────────────────────────
# RENDER HELPERS — Pure Streamlit, no raw HTML tables
# ─────────────────────────────────────────────────────────────────────────────

def render_ingredient_breakdown(classified):
    """
    Renders Good | Bad | Neutral tables using native st.columns.
    No raw HTML — fixes the bleed issue completely.
    """
    good    = [i for i in classified if i["label"] == "GOOD"]
    bad     = [i for i in classified if i["label"] == "BAD"]
    neutral = [i for i in classified if i["label"] == "NEUTRAL"]

    col_g, col_b = st.columns(2, gap="medium")

    # ── GOOD column ──
    with col_g:
        st.markdown(
            '<div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;'
            'color:#4CAF7D;padding:8px 0;border-bottom:1px solid rgba(76,175,125,0.25);'
            'margin-bottom:10px;">🟢 &nbsp; Good Ingredients</div>',
            unsafe_allow_html=True
        )
        if good:
            for ing in good:
                pct_str  = f" ({ing['percentage']}%)" if ing.get("percentage") else ""
                enum_str = " ".join(
                    f'<span class="enum-tag">E{e}</span>'
                    for e in ing.get("e_numbers", [])
                )
                st.markdown(
                    f'<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
                    f'<span style="color:#4CAF7D;font-weight:600;font-size:14px;">'
                    f'{ing["name"]}{pct_str}</span>{enum_str}'
                    f'<div style="font-size:12px;color:rgba(237,234,226,0.5);margin-top:3px;">'
                    f'{ing.get("reason","")}</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="color:rgba(237,234,226,0.3);font-size:13px;padding:8px 0;">'
                'No good ingredients found.</div>',
                unsafe_allow_html=True
            )

    # ── BAD column ──
    with col_b:
        st.markdown(
            '<div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;'
            'color:#FF6B6B;padding:8px 0;border-bottom:1px solid rgba(255,107,107,0.25);'
            'margin-bottom:10px;">🔴 &nbsp; Bad Ingredients</div>',
            unsafe_allow_html=True
        )
        if bad:
            for ing in bad:
                pct_str  = f" ({ing['percentage']}%)" if ing.get("percentage") else ""
                bad_enums = [
                    e for e in ing.get("e_details", []) if e["label"] == "BAD"
                ]
                enum_str = " ".join(
                    f'<span class="enum-tag" style="color:#FF6B6B;'
                    f'border-color:rgba(255,107,107,0.3);">E{e["name"]}</span>'
                    for e in bad_enums
                )
                st.markdown(
                    f'<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
                    f'<span style="color:#FF6B6B;font-weight:600;font-size:14px;">'
                    f'{ing["name"]}{pct_str}</span>{enum_str}'
                    f'<div style="font-size:12px;color:rgba(237,234,226,0.5);margin-top:3px;">'
                    f'{ing.get("reason","")}</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="color:rgba(237,234,226,0.3);font-size:13px;padding:8px 0;">'
                'No bad ingredients found!</div>',
                unsafe_allow_html=True
            )

    # ── NEUTRAL row (below both columns) ──
    if neutral:
        st.markdown(
            '<div style="margin-top:14px;padding-top:12px;'
            'border-top:1px solid rgba(255,255,255,0.06);">'
            '<span style="font-size:10px;letter-spacing:2px;text-transform:uppercase;'
            'color:rgba(237,234,226,0.35);">🟡 Neutral &nbsp;</span>' +
            " &nbsp;·&nbsp; ".join(
                f'<span style="color:#FFD166;font-size:13px;">{n["name"]}</span>'
                for n in neutral
            ) + '</div>',
            unsafe_allow_html=True
        )


def render_score_card(score_result):
    """Renders the OpticEats score card using st.markdown (single block, no table)."""
    score    = score_result["score"]
    category = score_result["category"]
    note     = score_result["note"]
    hl       = score_result["highlights"]
    color    = SCORE_COLOR.get(category, "#4CAF7D")
    pct      = int((score / 10) * 100)
    badge_cls= f"badge-{category.lower()}"

    harmful_html = ""
    if hl.get("harmful_enumbers"):
        enums = ", ".join(hl["harmful_enumbers"])
        harmful_html = (
            f'<div style="margin-top:8px;font-size:12px;color:rgba(255,107,107,0.8);">'
            f'🧪 {enums}</div>'
        )

    guide_html = ""
    for low, high, name, clr in [(0,3,"BAD","#FF6B6B"),(3,5,"AVERAGE","#FFA500"),
                                  (5,7,"GOOD","#FFD166"),(7,10,"EXCELLENT","#4CAF7D")]:
        here = ('<span class="guide-here">◀ YOU ARE HERE</span>'
                if category == name else "")
        guide_html += (
            f'<div class="guide-row">'
            f'<div class="guide-dot" style="background:{clr};"></div>'
            f'<span style="color:rgba(237,234,226,0.5);min-width:55px;">{low}–{high}</span>'
            f'<span style="font-family:Raleway,sans-serif;font-weight:700;color:{clr};">{name}</span>'
            f'{here}</div>'
        )

    st.markdown(f"""
    <div class="score-card">
      <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;
                  color:#4CAF7D;margin-bottom:1rem;">OpticEats Score</div>
      <div class="score-number" style="color:{color};">
        {score}<span class="score-denom"> / 10</span>
      </div>
      <div><span class="score-badge {badge_cls}">{category}</span></div>
      <div class="score-bar-bg">
        <div class="score-bar-fill" style="width:{pct}%;background:{color};"></div>
      </div>
      <div class="score-note">{note}</div>
      {harmful_html}
      <div style="margin-top:1.5rem;text-align:left;">{guide_html}</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="oe-header">
  <div class="oe-logo-row">
    <svg width="54" height="54" viewBox="0 0 100 100" fill="none">
      <path d="M8 50 C20 22,80 22,92 50 C80 78,20 78,8 50 Z"
            stroke="#4CAF7D" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <circle cx="50" cy="50" r="16" fill="#162B1E" stroke="#4CAF7D" stroke-width="2"/>
      <circle cx="50" cy="50" r="5" fill="#4CAF7D"/>
      <line x1="43" y1="40" x2="43" y2="47" stroke="#4CAF7D" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="46" y1="39" x2="46" y2="47" stroke="#4CAF7D" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="44.5" y1="47" x2="44.5" y2="56" stroke="#4CAF7D" stroke-width="1.8" stroke-linecap="round"/>
      <path d="M56 43 C61 43,62 50,57 52 C54 53,54 50,56 43 Z" fill="#4CAF7D"/>
      <path d="M4 38 L4 28 L14 28" stroke="#4CAF7D" stroke-width="1.2" fill="none" stroke-linecap="round" opacity="0.4"/>
      <path d="M96 38 L96 28 L86 28" stroke="#4CAF7D" stroke-width="1.2" fill="none" stroke-linecap="round" opacity="0.4"/>
      <path d="M4 62 L4 72 L14 72" stroke="#4CAF7D" stroke-width="1.2" fill="none" stroke-linecap="round" opacity="0.4"/>
      <path d="M96 62 L96 72 L86 72" stroke="#4CAF7D" stroke-width="1.2" fill="none" stroke-linecap="round" opacity="0.4"/>
    </svg>
    <h1 class="oe-title">Optic<span>Eats</span></h1>
  </div>
  <p class="oe-tagline">See what you eat</p>
</div>
<hr class="oe-divider"/>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# INPUT SECTION
# ─────────────────────────────────────────────────────────────────────────────

col_left, col_right = st.columns([1.1, 1], gap="large")

with col_left:
    st.markdown('<p class="section-label">Step 1 — Select Category</p>', unsafe_allow_html=True)
    category = st.selectbox("Select Category", CATEGORIES, label_visibility="collapsed")

    st.markdown('<p class="section-label" style="margin-top:1.2rem;">Step 2 — Upload Ingredient Image</p>',
                unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Drop image here or click to browse",
        type=["jpg","jpeg","png","webp"],
        label_visibility="collapsed"
    )
    if uploaded:
        st.image(Image.open(uploaded), caption="Uploaded image", width="stretch")

    st.markdown('<div style="margin-top:1.2rem;"></div>', unsafe_allow_html=True)
    analyse_btn = st.button("✦ DONE", width="stretch")

with col_right:
    st.markdown("""
    <div class="how-card">
      <p class="section-label">How it works</p>
      <div style="display:flex;flex-direction:column;gap:1rem;margin-top:0.8rem;">
        <div style="display:flex;gap:14px;align-items:flex-start;">
          <div class="step-num">1</div>
          <div><div style="font-family:Raleway,sans-serif;font-weight:700;font-size:13px;">Select category</div>
          <div style="font-size:12px;color:rgba(237,234,226,0.5);margin-top:2px;">Choose your food product type</div></div>
        </div>
        <div style="display:flex;gap:14px;align-items:flex-start;">
          <div class="step-num">2</div>
          <div><div style="font-family:Raleway,sans-serif;font-weight:700;font-size:13px;">Upload image</div>
          <div style="font-size:12px;color:rgba(237,234,226,0.5);margin-top:2px;">Take a clear photo of the ingredients label</div></div>
        </div>
        <div style="display:flex;gap:14px;align-items:flex-start;">
          <div class="step-num">3</div>
          <div><div style="font-family:Raleway,sans-serif;font-weight:700;font-size:13px;">Click DONE</div>
          <div style="font-size:12px;color:rgba(237,234,226,0.5);margin-top:2px;">OpticEats analyses every ingredient</div></div>
        </div>
        <div style="display:flex;gap:14px;align-items:flex-start;">
          <div class="step-num">4</div>
          <div><div style="font-family:Raleway,sans-serif;font-weight:700;font-size:13px;">Get your score</div>
          <div style="font-size:12px;color:rgba(237,234,226,0.5);margin-top:2px;">See full breakdown and OpticEats Score</div></div>
        </div>
      </div>
      <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid rgba(76,175,125,0.1);">
        <p class="section-label">Score Guide</p>
        <div style="display:flex;flex-direction:column;gap:6px;margin-top:8px;">
          <div style="display:flex;gap:10px;font-size:13px;align-items:center;">
            <span style="color:#FF6B6B;font-family:Raleway,sans-serif;font-weight:700;min-width:50px;">0 – 3</span>
            <span style="color:rgba(237,234,226,0.6);">BAD — Avoid regular consumption</span></div>
          <div style="display:flex;gap:10px;font-size:13px;align-items:center;">
            <span style="color:#FFA500;font-family:Raleway,sans-serif;font-weight:700;min-width:50px;">3 – 5</span>
            <span style="color:rgba(237,234,226,0.6);">AVERAGE — Consume occasionally</span></div>
          <div style="display:flex;gap:10px;font-size:13px;align-items:center;">
            <span style="color:#FFD166;font-family:Raleway,sans-serif;font-weight:700;min-width:50px;">5 – 7</span>
            <span style="color:rgba(237,234,226,0.6);">GOOD — Decent choice</span></div>
          <div style="display:flex;gap:10px;font-size:13px;align-items:center;">
            <span style="color:#4CAF7D;font-family:Raleway,sans-serif;font-weight:700;min-width:50px;">7 – 10</span>
            <span style="color:rgba(237,234,226,0.6);">EXCELLENT — Great choice!</span></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS & RESULTS
# ─────────────────────────────────────────────────────────────────────────────

if analyse_btn:
    if not uploaded:
        st.warning("⚠️  Please upload an ingredient image first.")
    else:
        suffix = Path(uploaded.name).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = tmp.name

        ocr_result, parsed, classified, score_result = run_pipeline(tmp_path)
        os.unlink(tmp_path)

        if classified and score_result:
            st.markdown('<hr class="oe-divider"/>', unsafe_allow_html=True)

            # ── Stats Row ──
            hl = score_result["highlights"]
            s1, s2, s3, s4 = st.columns(4)
            for col, val, label, clr in [
                (s1, hl["total_ingredients"], "Ingredients", "#EDEAE2"),
                (s2, hl["good_count"],         "Good",        "#4CAF7D"),
                (s3, hl["bad_count"],           "Bad",         "#FF6B6B"),
                (s4, hl["neutral_count"],       "Neutral",     "#FFD166"),
            ]:
                with col:
                    st.markdown(
                        f'<div class="stat-box">'
                        f'<div class="stat-number" style="color:{clr};">{val}</div>'
                        f'<div class="stat-label">{label}</div></div>',
                        unsafe_allow_html=True
                    )

            st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

            # ── Main Results Layout ──
            res_left, res_right = st.columns([1.6, 1], gap="large")

            with res_left:
                st.markdown(
                    '<div style="font-family:Raleway,sans-serif;font-size:13px;font-weight:700;'
                    'letter-spacing:3px;text-transform:uppercase;color:#4CAF7D;margin-bottom:1rem;">'
                    'Ingredient Breakdown</div>',
                    unsafe_allow_html=True
                )
                # ← Native Streamlit rendering — no HTML bleed
                render_ingredient_breakdown(classified)

                st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
                with st.expander("🔍 View extracted text (OCR output)"):
                    st.code(ocr_result.get("clean_text",""), language=None)

                with st.expander("📐 Score breakdown"):
                    for line in score_result["breakdown"]:
                        st.markdown(f"• {line}")

            with res_right:
                render_score_card(score_result)

                cat    = score_result["category"]
                clr    = SCORE_COLOR.get(cat, "#4CAF7D")
                st.markdown(
                    f'<div class="note-box note-{cat.lower()}" style="margin-top:1rem;">'
                    f'<div class="note-title" style="color:{clr};">📋 Note</div>'
                    f'<div class="note-text">{score_result["note"]}</div>'
                    f'<div class="note-text" style="margin-top:6px;font-size:11px;opacity:0.6;">'
                    f'Category selected: {category}</div></div>',
                    unsafe_allow_html=True
                )

# ─────────────────────────────────────────────────────────────────────────────
# DISCLAIMER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer">
  OpticEats scores are for informational purposes only and do not constitute medical or dietary advice.<br>
  Always consult a qualified nutritionist or healthcare professional for personalised guidance.
</div>
""", unsafe_allow_html=True)
