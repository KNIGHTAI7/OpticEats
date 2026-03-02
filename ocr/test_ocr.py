"""
OpticEats — Stage 1 Test Script
================================
Run this to verify your OCR setup is working correctly.

Usage:
    python test_ocr.py                          # uses sample image
    python test_ocr.py path/to/your/image.jpg   # your own image
    python test_ocr.py path/to/image.jpg --backend google_vision --credentials creds.json
"""

import sys
import json
import argparse
from pathlib import Path

# Add parent directory so we can import opticeats modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr.extractor import extract_ingredients_text


def print_banner():
    print("""
╔═══════════════════════════════════════════╗
║         OpticEats — OCR Stage 1           ║
║         Text Extraction Test              ║
╚═══════════════════════════════════════════╝
""")


def print_result(result: dict):
    print("=" * 55)
    print(f"  Backend    : {result['backend'].upper()}")
    print(f"  Image      : {Path(result['image_path']).name}")
    print(f"  Success    : {'✅ YES' if result['success'] else '❌ NO'}")
    print("=" * 55)

    if not result["success"]:
        print(f"\n  ❌ Error: {result.get('error', 'Unknown error')}")
        return

    print("\n📄 RAW OCR OUTPUT:")
    print("-" * 55)
    print(result["raw_text"])

    print("\n✨ CLEANED TEXT (ready for ingredient parser):")
    print("-" * 55)
    print(result["clean_text"])

    print(f"\n📦 TEXT BLOCKS DETECTED: {len(result['blocks'])}")
    print("-" * 55)
    for i, block in enumerate(result["blocks"][:10], 1):  # show first 10
        conf_bar = "█" * int(block["confidence"] * 10)
        print(f"  {i:2}. [{conf_bar:<10}] {block['confidence']:.2f}  →  {block['text']}")
    if len(result["blocks"]) > 10:
        print(f"  ... and {len(result['blocks']) - 10} more blocks")

    print("\n" + "=" * 55)


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Test OpticEats OCR extraction")
    parser.add_argument("image", nargs="?", default=None,
                        help="Path to ingredient image (JPG/PNG)")
    parser.add_argument("--backend", choices=["easyocr", "google_vision"],
                        default="easyocr",
                        help="OCR backend to use (default: easyocr)")
    parser.add_argument("--credentials", default=None,
                        help="Path to Google Cloud credentials JSON")
    parser.add_argument("--save-json", action="store_true",
                        help="Save result as JSON file")
    args = parser.parse_args()

    # Determine image path
    if args.image:
        image_path = args.image
    else:
        # Look for a sample image in common locations
        candidates = [
            "sample.jpg", "sample.png",
            "test.jpg", "test.png",
            "../sample.jpg",
        ]
        image_path = next((p for p in candidates if Path(p).exists()), None)
        if not image_path:
            print("⚠️  No image provided and no sample image found.")
            print("Usage: python test_ocr.py your_image.jpg")
            sys.exit(1)

    print(f"🔍 Processing: {image_path}")
    print(f"🔧 Backend   : {args.backend}\n")

    # Run extraction
    result = extract_ingredients_text(
        image_path=image_path,
        backend=args.backend,
        google_credentials=args.credentials
    )

    # Print results
    print_result(result)

    # Optionally save
    if args.save_json:
        out_path = Path(image_path).stem + "_ocr_result.json"
        save_result = {k: v for k, v in result.items() if k != "blocks"}
        save_result["block_count"] = len(result["blocks"])
        with open(out_path, "w") as f:
            json.dump(save_result, f, indent=2)
        print(f"\n💾 Result saved to: {out_path}")


if __name__ == "__main__":
    main()
