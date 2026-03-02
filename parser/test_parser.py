"""
OpticEats — Stage 2 Test Script
=================================
Tests the ingredient parser using the actual OCR output from Stage 1.

Usage:
    # Test with hardcoded sample (your biscuit image output):
    python test_parser.py

    # Test with a live image (runs Stage 1 + Stage 2 together):
    python test_parser.py --image path/to/image.jpg
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.ingredient_parser import parse_ingredients, summarise_ingredients


# ── This is the actual OCR output from your biscuit image (Stage 1 result) ──
SAMPLE_OCR_OUTPUT = (
    "WHEAT FLOUR (ATTA) (639), REFINED PALM OIL, SUGAR; WHEAT "
    "BRAN (4.79), LIQUID GLUCOSE, MILK SOLIDS, MALTODEXTRIN, "
    "RAISING AGENTS [Sool] & 503()], HODISED SALT, "
    "EMULSIFIERS [322/}, 471 & 472e], NATURAL, "
    "NATURE IDENTICAL & ARTIFICIAL (VANILLA} FLAVOURING SUBSTANCES, "
    "MALT EXTRACT AND DOUGH CONDITLONER (2231. "
    "(Numbers in brackets as per International Numbering System) "
    "#Made with wheat flour (atta}"
)


def print_banner():
    print("""
╔═══════════════════════════════════════════╗
║       OpticEats — Ingredient Parser       ║
║             Stage 2 Test                  ║
╚═══════════════════════════════════════════╝
""")


def run_with_sample():
    """Run parser on the hardcoded sample OCR text."""
    print("📋 INPUT (raw OCR text from Stage 1):")
    print("─" * 55)
    print(SAMPLE_OCR_OUTPUT)
    print()

    ingredients = parse_ingredients(SAMPLE_OCR_OUTPUT)

    print(summarise_ingredients(ingredients))

    print("\n📊 JSON OUTPUT (feeds into Stage 3):")
    print("─" * 55)
    print(json.dumps(ingredients, indent=2))

    return ingredients


def run_with_image(image_path: str):
    """Run full pipeline: Stage 1 (OCR) → Stage 2 (Parser)."""
    from ocr.extractor import extract_ingredients_text

    print(f"🖼  Running Stage 1 OCR on: {image_path}")
    ocr_result = extract_ingredients_text(image_path)

    if not ocr_result["success"]:
        print(f"❌ OCR failed: {ocr_result.get('error')}")
        sys.exit(1)

    print(f"✅ OCR complete. Clean text length: {len(ocr_result['clean_text'])} chars\n")

    ingredients = parse_ingredients(ocr_result["clean_text"])
    print(summarise_ingredients(ingredients))

    print("\n📊 JSON OUTPUT:")
    print("─" * 55)
    print(json.dumps(ingredients, indent=2))

    return ingredients


def validate_output(ingredients: list[dict]):
    """Quick validation checks on the parsed output."""
    print("\n🔍 VALIDATION CHECKS:")
    print("─" * 55)

    # Check 1: At least 5 ingredients found
    count = len(ingredients)
    status = "✅" if count >= 5 else "⚠️ "
    print(f"  {status} Ingredient count       : {count} (expected ≥5)")

    # Check 2: Wheat flour is first
    first = ingredients[0]["name"] if ingredients else ""
    status = "✅" if "WHEAT" in first else "⚠️ "
    print(f"  {status} First ingredient        : {first}")

    # Check 3: Percentages extracted
    with_pct = [i for i in ingredients if i["percentage"] is not None]
    status = "✅" if len(with_pct) >= 1 else "⚠️ "
    print(f"  {status} Ingredients with %      : {len(with_pct)}")

    # Check 4: E-numbers found
    with_enu = [i for i in ingredients if i["e_numbers"]]
    status = "✅" if len(with_enu) >= 1 else "⚠️ "
    print(f"  {status} Ingredients with E-nums : {len(with_enu)}")

    # Check 5: Noise filtered out
    noise_found = any(
        x in i["name"] for i in ingredients
        for x in ["NUMBERS IN", "MADE WITH", "CONTAINS WHEAT", "INTERNATIONAL"]
    )
    status = "❌" if noise_found else "✅"
    print(f"  {status} Noise filtered           : {'NO - fix needed!' if noise_found else 'Clean'}")

    print("─" * 55)


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Test OpticEats ingredient parser")
    parser.add_argument("--image", default=None,
                        help="Image path to run full Stage1+Stage2 pipeline")
    parser.add_argument("--save-json", action="store_true",
                        help="Save parsed result as JSON")
    args = parser.parse_args()

    if args.image:
        ingredients = run_with_image(args.image)
    else:
        print("ℹ️  No image provided — using built-in sample OCR text\n")
        ingredients = run_with_sample()

    validate_output(ingredients)

    if args.save_json:
        out_file = "parsed_ingredients.json"
        with open(out_file, "w") as f:
            json.dump(ingredients, f, indent=2)
        print(f"\n💾 Saved to: {out_file}")


if __name__ == "__main__":
    main()
