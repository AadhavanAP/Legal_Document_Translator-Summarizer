# Legal Document Translator & Summarizer

A production-ready Streamlit application that extracts, translates, and summarizes legal documents written in Indian languages (Kannada, Hindi, Tamil, Telugu, Malayalam) into clear English — powered by free-tier AI APIs.

---

## Features

- **Multi-format input** — PDF (multi-page) and images (JPG, PNG)
- **OCR** — Tesseract extracts Indic script text from scanned documents
- **Two free AI backends** — Google Gemini 2.0 Flash or Groq Llama 3.1 8B (user-selectable)
- **High-quality translation** — LLM-powered, preserves legal terminology and document structure
- **Structured legal summaries** — document type, parties, subject, obligations, dates
- **5 Indic languages** — Kannada, Hindi, Tamil, Telugu, Malayalam
- **Comprehensive error handling** — every failure (API, OCR, PDF, network) shows a plain-English explanation with a fix
- **Dark theme UI** — responsive two-column layout, sidebar config

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI framework | [Streamlit](https://streamlit.io) |
| OCR engine | [Tesseract](https://github.com/tesseract-ocr/tesseract) + [pytesseract](https://github.com/madmaze/pytesseract) |
| PDF → image | [pdf2image](https://github.com/Belval/pdf2image) + Poppler |
| Image handling | [Pillow](https://python-pillow.org) |
| AI — translation & summary | [Google Gemini 2.0 Flash](https://aistudio.google.com) or [Groq Llama 3.1 8B](https://groq.com) |

---

## Prerequisites

### 1. Tesseract OCR + Indic language packs

```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu / Debian
sudo apt install tesseract-ocr \
  tesseract-ocr-kan tesseract-ocr-hin \
  tesseract-ocr-tam tesseract-ocr-tel tesseract-ocr-mal

# Windows
# Download installer from https://github.com/UB-Mannheim/tesseract/wiki
# During install, check "Additional language data" and select the languages you need
# Add the install directory to your system PATH
```

### 2. Poppler (PDF processing)

```bash
# macOS
brew install poppler

# Ubuntu / Debian
sudo apt install poppler-utils

# Windows
# Download from https://github.com/oschwartz10612/poppler-windows/releases
# Extract and add the bin/ folder to your system PATH
```

### 3. A free AI API key (pick one or both)

| Provider | Free tier | Get key |
|----------|-----------|---------|
| **Google Gemini** | 1,500 req/day · 15 RPM | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| **Groq** | 6,000 tokens/min | [console.groq.com/keys](https://console.groq.com/keys) |

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-username/Legal_Document_Translator-Summarizer.git
cd Legal_Document_Translator-Summarizer

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt
```

---

## Running the App

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## How to Use

1. **Sidebar → AI Provider** — select Google Gemini or Groq
2. **Sidebar → API Key** — paste your free API key and click **Test Connection**
3. **Sidebar → Source Language** — select the language your document is written in
4. **Upload** a PDF or image file
5. Click **Translate & Summarize**

Results are displayed as:
- Extracted original text (per page for PDFs)
- Full English translation
- Structured 5-point legal summary

---

## Project Structure

```
Legal_Document_Translator-Summarizer/
├── app.py            # Main application (single file)
├── requirements.txt  # Python dependencies
├── .gitignore        # Git ignore rules
├── LICENSE           # MIT License
└── README.md         # This file
```

---

## Error Handling

Every error surface shows a plain-English message with a specific fix:

| Category | Errors handled |
|----------|---------------|
| API — Gemini | Invalid key, quota exhausted, rate limit, permission denied, model unavailable, SSL, timeout, service down, safety block |
| API — Groq | Invalid key, rate limit, daily quota, model unavailable, context too long, network error, timeout, service down |
| Missing packages | `pip install google-generativeai` / `pip install groq` instructions shown inline |
| OCR | Tesseract not installed, language pack missing, no text detected, low resolution warning |
| PDF | Poppler not installed, password-protected PDF, corrupted file, file too large |
| Image | Unreadable file, corrupted/truncated image |

---

## Common Issues

**`TesseractNotFoundError`**
Tesseract is not installed or not on your PATH. Install it per the prerequisites above and restart the app.

**`PDFPageCountError` / Poppler error**
Poppler is not installed. Install it per the prerequisites above and restart the app.

**Gemini 429 — quota exhausted**
Your key's daily free-tier limit is reached. Wait until tomorrow or switch to Groq in the sidebar.

**No text detected on a page**
The scan resolution may be too low (aim for ≥150 DPI) or the wrong source language is selected.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Copyright (c) 2025 Aadhavan A P
