"""
OpticEats — Stage 4 Test Script
=================================
Tests scoring using Stage 3 classified output.

Usage:
    python test_scorer.py                        # uses built-in classified sample
    python test_scorer.py --image ../sample.png  # full pipeline
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scorer.score_engine import calculate_score, display_score


# Classified output from Stage 3 (your biscuit image)
SAMPLE_CLASSIFIED = [
    {"name": "WHEAT FLOUR (ATTA)", "percentage": 63.0, "e_numbers": [],               "label": "GOOD",    "e_details": []},
    {"name": "REFINED PALM OIL",   "percentage": None, "e_numbers": [],               "label": "BAD",     "e_details": []},
    {"name": "SUGAR",              "percentage": None, "e_numbers": [],               "label": "BAD",     "e_details": []},
    {"name": "WHEAT BRAN",         "percentage": 4.7,  "e_numbers": [],               "label": "GOOD",    "e_details": []},
    {"name": "LIQUID GLUCOSE",     "percentage": None, "e_numbers": [],               "label": "BAD",     "e_details": []},
    {"name": "MILK SOLIDS",        "percentage": None, "e_numbers": [],               "label": "NEUTRAL", "e_details": []},
    {"name": "MALTODEXTRIN",       "percentage": None, "e_numbers": [],               "label": "BAD",     "e_details": []},
    {"name": "RAISING AGENTS",     "percentage": None, "e_numbers": ["500(ii)","503(ii)"], "label": "NEUTRAL",
     "e_details": [
        {"name": "500(ii)", "label": "GOOD",    "reason": "Baking soda — natural leavening agent.", "e_name": "Sodium Bicarbonate"},
        {"name": "503(ii)", "label": "NEUTRAL", "reason": "Baking leavener. Dissipates completely during baking.", "e_name": "Ammonium Bicarbonate"},
     ]},
    {"name": "MALT EXTRACT",       "percentage": None, "e_numbers": [],               "label": "NEUTRAL", "e_details": []},
    {"name": "DOUGH CONDITIONER",  "percentage": None, "e_numbers": ["223"],          "label": "BAD",
     "e_details": [
        {"name": "223", "label": "BAD", "reason": "Sulphite preservative. Can trigger asthma and severe allergic reactions.", "e_name": "Sodium Metabisulphite"},
     ]},
]


def print_banner():
    print("""
╔═══════════════════════════════════════════╗
║       OpticEats — Score Engine            ║
║              Stage 4 Test                 ║
╚═══════════════════════════════════════════╝
""")


def run_full_pipeline(image_path):
    from ocr.extractor import extract_ingredients_text
    from parser.ingredient_parser import parse_ingredients
    from classifier.classifier import classify_ingredients

    print(f"[Pipeline] Stage 1 — OCR")
    ocr = extract_ingredients_text(image_path)
    if not ocr["success"]:
        print(f"OCR failed: {ocr.get('error')}")
        sys.exit(1)

    print(f"[Pipeline] Stage 2 — Parsing")
    parsed = parse_ingredients(ocr["clean_text"])

    print(f"[Pipeline] Stage 3 — Classifying")
    classified = classify_ingredients(parsed)

    print(f"[Pipeline] Stage 4 — Scoring")
    return classified


def main():
    print_banner()
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=None)
    parser.add_argument("--save-json", action="store_true")
    args = parser.parse_args()

    if args.image:
        classified = run_full_pipeline(args.image)
    else:
        print("Using built-in Stage 3 sample data\n")
        classified = SAMPLE_CLASSIFIED

    result = calculate_score(classified)
    display_score(result)

    if args.save_json:
        with open("score_result.json", "w") as f:
            json.dump(result, f, indent=2)
        print("Saved: score_result.json")


if __name__ == "__main__":
    main()
