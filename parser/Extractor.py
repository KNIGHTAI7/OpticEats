"""
OpticEats — Stage 1: OCR Extractor
====================================
Extracts raw ingredient text from a food package image.

Supports two backends:
  1. EasyOCR  (default, offline, open-source)
  2. Google Cloud Vision API  (optional, higher accuracy for production)

Install dependencies:
    pip install easyocr pillow opencv-python numpy
    
    # Optional (for Google Vision):
    pip install google-cloud-vision
"""

import re
import cv2
import numpy as np
from PIL import Image
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE PREPROCESSING
# Better image = better OCR accuracy. Always preprocess first.
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_image(image_path: str) -> np.ndarray:
    """
    Prepares the image for OCR:
      - Resize if too small (OCR struggles under 300dpi equivalent)
      - Convert to grayscale
      - Adaptive thresholding to sharpen text vs background
      - Denoise to remove packaging texture noise
      
    Returns a numpy array (OpenCV image) ready for OCR.
    """
    # Load image
    img = cv2.imread(str(image_path))
    if img is None:
        # Try loading via PIL first (handles more formats)
        pil_img = Image.open(image_path).convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # ── Step 1: Upscale if image is too small ──
    h, w = img.shape[:2]
    min_dim = 1000  # px — good baseline for OCR
    if min(h, w) < min_dim:
        scale = min_dim / min(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)

    # ── Step 2: Convert to grayscale ──
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Step 3: Adaptive threshold (handles uneven lighting on curved packaging) ──
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,   # size of neighbourhood area
        C=10            # constant subtracted from mean
    )

    # ── Step 4: Denoise ──
    denoised = cv2.fastNlMeansDenoising(thresh, h=15)

    return denoised


def preprocess_for_easyocr(image_path: str) -> np.ndarray:
    """
    EasyOCR works better with the original colour image + mild sharpening.
    Returns numpy array.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        pil_img = Image.open(image_path).convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # Upscale if small
    h, w = img.shape[:2]
    if min(h, w) < 800:
        scale = 800 / min(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)

    # Sharpen kernel
    kernel = np.array([[0, -1, 0],
                        [-1, 5, -1],
                        [0, -1, 0]])
    sharpened = cv2.filter2D(img, -1, kernel)

    # Convert BGR → RGB for EasyOCR
    return cv2.cvtColor(sharpened, cv2.COLOR_BGR2RGB)


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND 1: EasyOCR  (Recommended for development)
# ─────────────────────────────────────────────────────────────────────────────

# Lazy-load the reader so it only loads once across multiple calls
_easyocr_reader = None

def _get_easyocr_reader():
    """Returns a cached EasyOCR reader instance."""
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        print("[OpticEats OCR] Loading EasyOCR model (first run may take ~30s)...")
        _easyocr_reader = easyocr.Reader(
            ['en'],           # languages — add 'hi' for Hindi etc.
            gpu=False,        # set True if you have a CUDA GPU
            verbose=False
        )
        print("[OpticEats OCR] EasyOCR ready.")
    return _easyocr_reader


def extract_with_easyocr(image_path: str) -> dict:
    """
    Extract text from image using EasyOCR.
    
    Returns:
        {
          "raw_text": str,          # full joined text
          "blocks": list[dict],     # individual text blocks with confidence
          "backend": "easyocr"
        }
    """
    reader = _get_easyocr_reader()
    img_array = preprocess_for_easyocr(image_path)
    
    results = reader.readtext(
        img_array,
        detail=1,             # return bounding boxes + confidence
        paragraph=False,      # keep individual words/phrases separate
        min_size=10,          # ignore tiny noise
        text_threshold=0.5,   # confidence threshold for text detection
        low_text=0.3,
        width_ths=0.7,        # merge horizontally close text boxes
        height_ths=0.7,
        contrast_ths=0.1,
        adjust_contrast=0.5,
    )

    blocks = []
    for (bbox, text, confidence) in results:
        blocks.append({
            "text": text.strip(),
            "confidence": round(confidence, 3),
            "bbox": bbox  # [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
        })

    # Sort blocks top-to-bottom, left-to-right (reading order)
    blocks.sort(key=lambda b: (b["bbox"][0][1], b["bbox"][0][0]))

    raw_text = " ".join(b["text"] for b in blocks if b["confidence"] > 0.1)

    return {
        "raw_text": raw_text,
        "blocks": blocks,
        "backend": "easyocr"
    }


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND 2: Google Cloud Vision  (Recommended for production)
# ─────────────────────────────────────────────────────────────────────────────

def extract_with_google_vision(image_path: str, credentials_json: str = None) -> dict:
    """
    Extract text using Google Cloud Vision API.
    
    Setup:
        1. Create a Google Cloud project at console.cloud.google.com
        2. Enable the Vision API
        3. Create a service account → download JSON key
        4. Pass the path to that JSON as credentials_json
        
    Returns same structure as extract_with_easyocr().
    """
    try:
        from google.cloud import vision
        import os
        if credentials_json:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_json
    except ImportError:
        raise ImportError(
            "Google Vision not installed. Run: pip install google-cloud-vision"
        )

    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)  # better than text_detection for dense text

    if response.error.message:
        raise RuntimeError(f"Google Vision API error: {response.error.message}")

    raw_text = response.full_text_annotation.text

    blocks = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                para_text = " ".join(
                    "".join(s.text for s in word.symbols)
                    for word in paragraph.words
                )
                confidence = paragraph.confidence
                blocks.append({
                    "text": para_text.strip(),
                    "confidence": round(confidence, 3),
                    "bbox": None  # skip for now
                })

    return {
        "raw_text": raw_text,
        "blocks": blocks,
        "backend": "google_vision"
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST-PROCESSING: Clean & Normalise Raw OCR Output
# ─────────────────────────────────────────────────────────────────────────────

def clean_ocr_text(raw_text: str) -> str:
    """
    Cleans up common OCR errors on food packaging text.
    
    Fixes:
      - Stray characters (|, !, ~)
      - Broken line joins
      - Normalise e-numbers: [322(i)] → [322(i)] consistent format
      - Standardise separators
      - Strip everything before "INGREDIENTS:" label
    """
    text = raw_text

    # ── Fix 1: Extract from INGREDIENTS: onward ──
    # Food labels always have "INGREDIENTS:" as the header
    match = re.search(r'INGREDIENTS?\s*[:\-]?\s*', text, re.IGNORECASE)
    if match:
        text = text[match.end():]  # keep only ingredient portion

    # ── Fix 2: Remove common OCR noise characters ──
    text = re.sub(r'[|~`\\^]', '', text)

    # ── Fix 3: Normalise whitespace ──
    text = re.sub(r'\s+', ' ', text).strip()

    # ── Fix 4: Fix broken brackets around e-numbers ──
    # e.g. "322 (i)" → "322(i)", " (500 ii)" → "(500ii)"
    text = re.sub(r'\(\s*(\d+)\s*\)', r'(\1)', text)
    text = re.sub(r'\[\s*(\d+)\s*\]', r'[\1]', text)

    # ── Fix 5: Ensure commas separate ingredients (not just spaces) ──
    # Some OCR outputs drop commas
    # Heuristic: if two capitalised words appear with no comma, don't touch
    # (We handle this more carefully in the parser)

    # ── Fix 6: Strip trailing noise like page numbers, barcodes ──
    text = re.sub(r'\b\d{8,}\b', '', text)  # barcodes (8+ digit numbers)

    # ── Fix 7: Normalise percent signs ──
    text = re.sub(r'(\d+)\s*[%℅]', r'\1%', text)

    # ── Fix 8: Remove repeated punctuation ──
    text = re.sub(r'[,;]{2,}', ',', text)

    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PUBLIC FUNCTION — This is what the rest of OpticEats calls
# ─────────────────────────────────────────────────────────────────────────────

def extract_ingredients_text(
    image_path: str,
    backend: str = "easyocr",
    google_credentials: str = None
) -> dict:
    """
    Master extraction function for OpticEats.
    
    Args:
        image_path        : Path to the ingredient image file
        backend           : "easyocr" (default) or "google_vision"
        google_credentials: Path to Google service account JSON (only for google_vision)
    
    Returns:
        {
          "raw_text"    : str,   # OCR output before cleaning
          "clean_text"  : str,   # Cleaned ingredient string ready for parser
          "blocks"      : list,  # Individual detected text blocks
          "backend"     : str,   # Which OCR engine was used
          "image_path"  : str,   # Original image path
          "success"     : bool
        }
    
    Example:
        >>> result = extract_ingredients_text("biscuit.jpg")
        >>> print(result["clean_text"])
        'WHEAT FLOUR (ATTA) (63%), REFINED PALM OIL, SUGAR, ...'
    """
    image_path = str(Path(image_path).resolve())

    if not Path(image_path).exists():
        return {
            "raw_text": "",
            "clean_text": "",
            "blocks": [],
            "backend": backend,
            "image_path": image_path,
            "success": False,
            "error": f"Image not found: {image_path}"
        }

    try:
        if backend == "google_vision":
            result = extract_with_google_vision(image_path, google_credentials)
        else:
            result = extract_with_easyocr(image_path)

        clean = clean_ocr_text(result["raw_text"])
        
        print(f"\n[OpticEats OCR] ✅ Extraction complete ({backend})")
        print(f"[OpticEats OCR] Raw length  : {len(result['raw_text'])} chars")
        print(f"[OpticEats OCR] Clean length: {len(clean)} chars")
        print(f"[OpticEats OCR] Cleaned text preview:\n  {clean[:200]}...\n")

        return {
            "raw_text"  : result["raw_text"],
            "clean_text": clean,
            "blocks"    : result["blocks"],
            "backend"   : backend,
            "image_path": image_path,
            "success"   : True
        }

    except Exception as e:
        return {
            "raw_text"  : "",
            "clean_text": "",
            "blocks"    : [],
            "backend"   : backend,
            "image_path": image_path,
            "success"   : False,
            "error"     : str(e)
        }
