# 🥗 OpticEats
### *See what you eat*

🚀 Live Demo
https://opticeats-pc8udprkphya4hc8px7oxg.streamlit.app/

An AI-powered food ingredient analyser — upload a photo of any food label and get an instant health breakdown.

---

## Project Structure

```
opticeats/
│
├── requirements.txt          ← Install dependencies
│
├── ocr/
│   ├── extractor.py          ← Stage 1: OCR text extraction
│   └── test_ocr.py           ← Test script for Stage 1
│
├── parser/                   ← Stage 2: Ingredient parser  (coming next)
│   └── ingredient_parser.py
│
├── classifier/               ← Stage 3: Good/Bad classifier
│   ├── knowledge_base.json
│   └── classifier.py
│
├── scorer/                   ← Stage 4: Health score engine
│   └── score_engine.py
│
├── assets/
│   └── logo.png              ← OpticEats logo
│
└── app.py                    ← Streamlit UI (final step)
```

---

## Stage 1 — OCR Setup

### Step 1: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Test the OCR extractor
```bash
cd ocr
python test_ocr.py path/to/ingredient_image.jpg
```

### Step 3: Expected output
```
✅ Extraction complete (easyocr)
Raw length  : 312 chars
Clean length: 287 chars
Cleaned text preview:
  WHEAT FLOUR (ATTA) (63%), REFINED PALM OIL, SUGAR, WHEAT BRAN (4.7%) ...
```

---

## OCR Backend Options

| Backend | Accuracy | Cost | Best For |
|---------|----------|------|----------|
| EasyOCR | Good | Free | Development & testing |
| Google Vision | Excellent | Free tier: 1000 req/month | Production |

---

## How the OCR Pipeline Works

```
Image File
    ↓
preprocess_image()
  • Upscale if too small
  • Grayscale + threshold
  • Denoise
    ↓
EasyOCR / Google Vision
  • Detect text regions
  • Read each region
  • Return with confidence scores
    ↓
clean_ocr_text()
  • Find INGREDIENTS: header
  • Remove noise characters
  • Fix broken e-numbers
  • Normalise separators
    ↓
clean_text  ← feeds into Stage 2 Parser
```

---

## Google Cloud Vision Setup (Optional)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable **Cloud Vision API**
4. Go to **IAM & Admin → Service Accounts**
5. Create a service account → download JSON key
6. Use it:
```bash
python test_ocr.py image.jpg --backend google_vision --credentials your_key.json
```

---

*Built with ❤️ using EasyOCR, OpenCV, and Python*
