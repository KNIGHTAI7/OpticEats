"""
OpticEats — Stage 3 Test Script
=================================
Tests the full pipeline: Stage1 (OCR) -> Stage2 (Parser) -> Stage3 (Classifier)

Usage:
    python test_classifier.py                    # uses built-in sample
    python test_classifier.py --image ../sample.png   # live image
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier import classify_ingredients, summarise_classification

# Built-in sample — Stage 2 output from your biscuit image
SAMPLE_PARSED = [
    {"name": "WHEAT FLOUR (ATTA)",   "percentage": 63.0, "e_numbers": [],       "raw": "WHEAT FLOUR (ATTA) (63%)"},
    {"name": "REFINED PALM OIL",     "percentage": None, "e_numbers": [],       "raw": "REFINED PALM OIL"},
    {"name": "SUGAR",                "percentage": None, "e_numbers": [],       "raw": "SUGAR"},
    {"name": "WHEAT BRAN",           "percentage": 4.7,  "e_numbers": [],       "raw": "WHEAT BRAN (4.7%)"},
    {"name": "LIQUID GLUCOSE",       "percentage": None, "e_numbers": [],       "raw": "LIQUID GLUCOSE"},
    {"name": "MILK SOLIDS",          "percentage": None, "e_numbers": [],       "raw": "MILK SOLIDS"},
    {"name": "MALTODEXTRIN",         "percentage": None, "e_numbers": [],       "raw": "MALTODEXTRIN"},
    {"name": "RAISING AGENTS",       "percentage": None, "e_numbers": ["500(ii)", "503(ii)"], "raw": "RAISING AGENTS [500(ii), 503(ii)]"},
    {"name": "MALT EXTRACT",         "percentage": None, "e_numbers": [],       "raw": "MALT EXTRACT"},
    {"name": "DOUGH CONDITIONER",    "percentage": None, "e_numbers": ["223"],  "raw": "DOUGH CONDITIONER [223]"},
]


def print_banner():
    print("""
╔═══════════════════════════════════════════╗
║     OpticEats — Ingredient Classifier     ║
║              Stage 3 Test                 ║
╚═══════════════════════════════════════════╝
""")


def run_full_pipeline(image_path: str):
    from ocr.extractor import extract_ingredients_text
    from parser.ingredient_parser import parse_ingredients

    print(f"[Pipeline] Stage 1 — OCR: {image_path}")
    ocr_result = extract_ingredients_text(image_path)
    if not ocr_result["success"]:
        print(f"OCR failed: {ocr_result.get('error')}")
        sys.exit(1)

    print(f"[Pipeline] Stage 2 — Parsing...")
    parsed = parse_ingredients(ocr_result["clean_text"])

    print(f"[Pipeline] Stage 3 — Classifying...")
    return classify_ingredients(parsed)


def main():
    print_banner()
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=None, help="Image path for full pipeline test")
    parser.add_argument("--save-json", action="store_true")
    args = parser.parse_args()

    if args.image:
        classified = run_full_pipeline(args.image)
    else:
        print("Using built-in sample data (Stage 2 output from biscuit image)\n")
        classified = classify_ingredients(SAMPLE_PARSED)

    print(summarise_classification(classified))

    print("JSON OUTPUT:")
    print("─" * 55)
    output = [{k: v for k, v in c.items() if k != "e_details"} for c in classified]
    print(json.dumps(output, indent=2))

    if args.save_json:
        with open("classified_ingredients.json", "w") as f:
            json.dump(classified, f, indent=2)
        print("\nSaved: classified_ingredients.json")


if __name__ == "__main__":
    main()
