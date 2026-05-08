import streamlit as st
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import re
import os
import tempfile
from typing import List, Tuple, Union

# ─────────────────────────────────────────────
#  Page config — must be first Streamlit call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Legal Document Translator & Summarizer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  Global CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f1117; }

    .card {
        background: #1c1f2e;
        border: 1px solid #2e3250;
        border-radius: 12px;
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.25rem;
    }
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #a78bfa;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.6rem;
    }
    .banner-success {
        background: #14532d33;
        border-left: 4px solid #22c55e;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        color: #86efac;
        font-size: 0.9rem;
    }
    .banner-info {
        background: #1e3a5f33;
        border-left: 4px solid #3b82f6;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        color: #93c5fd;
        font-size: 0.9rem;
    }
    .banner-warn {
        background: #78350f33;
        border-left: 4px solid #f59e0b;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        color: #fcd34d;
        font-size: 0.9rem;
    }
    .banner-error {
        background: #7f1d1d33;
        border-left: 4px solid #ef4444;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        color: #fca5a5;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    .error-title {
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 0.3rem;
    }
    .error-fix {
        font-size: 0.85rem;
        margin-top: 0.4rem;
        color: #f9a8d4;
    }
    .divider { border-top: 1px solid #2e3250; margin: 1.2rem 0; }
    textarea { font-size: 0.88rem !important; }
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  ERROR MESSAGE HELPERS
# ─────────────────────────────────────────────

def friendly_error(title: str, reason: str, fix: str):
    """Render a styled, human-readable error card."""
    st.markdown(
        f'<div class="banner-error">'
        f'<div class="error-title">❌ {title}</div>'
        f'<div>{reason}</div>'
        f'<div class="error-fix">💡 How to fix: {fix}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def parse_api_error(provider: str, error: Exception) -> Tuple[str, str, str]:
    """
    Inspect an API exception and return (title, reason, fix) strings
    that are meaningful to the end user.
    """
    msg = str(error).lower()
    raw = str(error)

    # ── Google Gemini errors ──────────────────
    if provider == "Google Gemini":

        if "api key not valid" in msg or "invalid api key" in msg or "api_key_invalid" in msg:
            return (
                "Invalid Gemini API Key",
                "The API key you entered was rejected by Google. It may be mistyped, revoked, or belong to a different project.",
                "Go to aistudio.google.com/app/apikey, copy your key again carefully, and paste it in the sidebar."
            )

        if "quota" in msg and ("limit: 0" in msg or "exceeded" in msg):
            return (
                "Gemini Free Tier Quota Exhausted",
                "Your API key has hit its daily free-tier request limit (1,500 requests/day or 15 per minute). "
                "This is a Google account-level restriction, not a problem with your document.",
                "Wait until tomorrow for the quota to reset, OR get a fresh key from a different Google account at aistudio.google.com/app/apikey, OR switch to Groq in the sidebar (also free, separate quota)."
            )

        if "rate_limit" in msg or "429" in msg or "resource_exhausted" in msg or "too many requests" in msg:
            return (
                "Gemini Rate Limit Hit",
                "You are sending requests too quickly. Gemini free tier allows 15 requests per minute.",
                "Wait 60 seconds and click the button again. If this keeps happening, switch to Groq in the sidebar."
            )

        if "permission_denied" in msg or "403" in msg:
            return (
                "Gemini API Permission Denied",
                "Your API key does not have permission to use the Gemini API. The key may be restricted to specific APIs or the Generative Language API may not be enabled.",
                "Go to console.cloud.google.com, open your project, navigate to APIs & Services → Enabled APIs, and enable 'Generative Language API'. Or create a new key at aistudio.google.com."
            )

        if "model not found" in msg or "404" in msg:
            return (
                "Gemini Model Not Found",
                "The model 'gemini-2.0-flash' could not be accessed. This may be a temporary availability issue.",
                "Wait a few minutes and try again. If the problem persists, check status.cloud.google.com."
            )

        if "no module named 'google'" in msg or "modulenotfounderror" in msg:
            return (
                "Missing Python Package: google-generativeai",
                "The 'google-generativeai' library is not installed in your Python environment.",
                "Run this in your terminal: pip install google-generativeai"
            )

        if "ssl" in msg or "certificate" in msg:
            return (
                "SSL / Network Error",
                "A secure connection to Google's servers could not be established. This usually means a firewall, VPN, or network proxy is blocking the connection.",
                "Check your internet connection, disable any VPN or proxy, and try again."
            )

        if "timeout" in msg or "timed out" in msg or "deadline" in msg:
            return (
                "Request Timed Out",
                "Google's servers took too long to respond. This is usually a temporary issue.",
                "Wait 30 seconds and try again. If it continues, check status.cloud.google.com."
            )

        if "service unavailable" in msg or "503" in msg or "overloaded" in msg:
            return (
                "Gemini Service Temporarily Unavailable",
                "Google's Gemini API is experiencing high load or temporary downtime.",
                "Wait 1–2 minutes and try again. Check status.cloud.google.com for outage updates."
            )

        if "blocked" in msg or "safety" in msg or "harm" in msg:
            return (
                "Content Blocked by Safety Filter",
                "Gemini's safety system flagged some content in your document. This can occasionally happen with legal documents containing sensitive terminology.",
                "Try uploading the document again. If it keeps failing, switch to Groq in the sidebar which has more lenient content policies for legal text."
            )

        # Gemini fallback
        return (
            "Gemini API Error",
            f"An unexpected error occurred: {raw[:200]}",
            "Check that your API key is correct and your internet connection is active. See aistudio.google.com for more details."
        )

    # ── Groq errors ───────────────────────────
    elif provider == "Groq":

        if "invalid api key" in msg or "authentication" in msg or "401" in msg or "no module named 'groq'" in msg.replace("'", ""):
            if "no module named" in msg:
                return (
                    "Missing Python Package: groq",
                    "The 'groq' library is not installed in your Python environment.",
                    "Run this in your terminal: pip install groq"
                )
            return (
                "Invalid Groq API Key",
                "The API key you entered was rejected by Groq. It may be mistyped or revoked.",
                "Go to console.groq.com/keys, generate a new key, and paste it in the sidebar."
            )

        if "rate limit" in msg or "429" in msg or "too many requests" in msg:
            return (
                "Groq Rate Limit Hit",
                "You have exceeded Groq's free tier rate limit. The free tier allows 6,000 tokens/min for Llama 3.1 8B.",
                "Wait 60 seconds and try again. For large documents, the model will process them slightly slower to stay within limits."
            )

        if "quota" in msg or "daily limit" in msg:
            return (
                "Groq Daily Quota Reached",
                "You have used all of today's free requests on Groq.",
                "Wait until tomorrow (quota resets at midnight UTC) or switch to Google Gemini in the sidebar."
            )

        if "model not found" in msg or "model_not_found" in msg or "404" in msg:
            return (
                "Groq Model Not Available",
                "The model 'llama-3.1-8b-instant' is not available on your Groq account.",
                "Log in to console.groq.com and verify that Llama 3.1 8B is accessible. If not, contact Groq support."
            )

        if "context_length" in msg or "token" in msg and "exceed" in msg:
            return (
                "Document Too Long for Model",
                "Your document has too many characters for Groq's Llama 3.1 8B context window (32K tokens).",
                "Try uploading fewer pages at a time, or switch to Google Gemini which handles longer documents."
            )

        if "ssl" in msg or "certificate" in msg or "connection" in msg:
            return (
                "Network Connection Error",
                "Could not connect to Groq's servers. Your internet connection may be down or blocked.",
                "Check your internet connection and try again. If you are behind a corporate firewall, you may need to whitelist api.groq.com."
            )

        if "timeout" in msg or "timed out" in msg:
            return (
                "Groq Request Timed Out",
                "Groq's servers took too long to respond.",
                "Wait a moment and try again. Check status.groq.com for any outages."
            )

        if "service unavailable" in msg or "503" in msg:
            return (
                "Groq Service Temporarily Unavailable",
                "Groq is experiencing temporary downtime or high load.",
                "Wait 1–2 minutes and retry. Check status.groq.com for updates."
            )

        # Groq fallback
        return (
            "Groq API Error",
            f"An unexpected error occurred: {raw[:200]}",
            "Verify your API key at console.groq.com/keys and check your internet connection."
        )

    # ── Generic fallback ──────────────────────
    return (
        "Unexpected Error",
        f"{raw[:300]}",
        "Check your internet connection and API key, then try again."
    )


def parse_ocr_error(error_str: str, lang: str) -> Tuple[str, str, str]:
    """Return (title, reason, fix) for OCR failures."""
    msg = error_str.lower()

    if "tesseract is not installed" in msg or "tesseractnotfound" in msg or "not found" in msg:
        return (
            "Tesseract OCR Not Installed",
            "Tesseract OCR engine was not found on your system. It is required to extract text from images and PDFs.",
            "Install it with: brew install tesseract tesseract-lang (macOS) | "
            "sudo apt install tesseract-ocr (Linux) | "
            "Download from github.com/UB-Mannheim/tesseract/wiki (Windows). Then restart the app."
        )

    if "failed loading language" in msg or f"(kannada)" in msg or "lang" in msg:
        lang_pkg = {
            "kan": "tesseract-ocr-kan", "hin": "tesseract-ocr-hin",
            "tam": "tesseract-ocr-tam", "tel": "tesseract-ocr-tel",
            "mal": "tesseract-ocr-mal",
        }.get(lang, f"tesseract-ocr-{lang}")
        return (
            f"Tesseract Language Pack Missing: {lang}",
            f"Tesseract is installed but the language data for '{lang}' is not available on your system.",
            f"Install the language pack: sudo apt install {lang_pkg} (Linux) | "
            f"brew install tesseract-lang (macOS — installs all language packs)"
        )

    if "permission" in msg or "access" in msg:
        return (
            "File Permission Error",
            "The app could not read the uploaded file due to permission restrictions.",
            "Try uploading the file again. If the issue persists, check that the file is not locked by another program."
        )

    return (
        "OCR Failed",
        f"Text extraction failed unexpectedly: {error_str[:200]}",
        "Make sure the image is clear and not corrupted. Try a higher resolution scan."
    )


def parse_pdf_error(error_str: str) -> Tuple[str, str, str]:
    """Return (title, reason, fix) for PDF conversion failures."""
    msg = error_str.lower()

    if "poppler" in msg or "pdftoppm" in msg or "pdfinfo" in msg or "no such file" in msg:
        return (
            "Poppler Not Installed",
            "pdf2image requires Poppler utilities (pdftoppm) to convert PDFs to images, but they were not found on your system.",
            "Install Poppler: brew install poppler (macOS) | "
            "sudo apt install poppler-utils (Linux) | "
            "Download from github.com/oschwartz10612/poppler-windows (Windows) and add bin/ to PATH. Then restart the app."
        )

    if "encrypted" in msg or "password" in msg:
        return (
            "PDF is Password Protected",
            "The uploaded PDF is encrypted and cannot be processed without a password.",
            "Open the PDF in Adobe Acrobat or your PDF viewer, remove the password protection (File → Properties → Security), save it, and upload again."
        )

    if "invalid" in msg or "corrupt" in msg or "not a pdf" in msg:
        return (
            "Invalid or Corrupted PDF",
            "The uploaded file does not appear to be a valid PDF, or it may be corrupted.",
            "Try re-downloading or re-exporting the original document as a PDF and upload it again."
        )

    if "permission" in msg or "access" in msg:
        return (
            "File Access Error",
            "The app could not read the PDF file.",
            "Try uploading the file again."
        )

    if "memory" in msg or "killed" in msg:
        return (
            "PDF Too Large to Process",
            "The PDF is too large to convert into images at 300 DPI.",
            "Try splitting the PDF into smaller sections (e.g. 5 pages at a time) and upload each part separately."
        )

    return (
        "PDF Conversion Failed",
        f"Could not convert PDF to images: {error_str[:200]}",
        "Make sure Poppler is installed and the file is a standard, non-corrupted PDF."
    )


def parse_image_error(error_str: str) -> Tuple[str, str, str]:
    """Return (title, reason, fix) for image open failures."""
    msg = error_str.lower()

    if "cannot identify image file" in msg or "unidentified image" in msg:
        return (
            "Unreadable Image File",
            "Pillow could not open the uploaded file as an image. The file may be corrupted or have an incorrect extension.",
            "Try uploading a different copy of the image. Ensure it is a valid JPG or PNG file."
        )

    if "truncated" in msg or "decompression" in msg:
        return (
            "Corrupted or Truncated Image",
            "The image file appears to be incomplete or corrupted.",
            "Re-export or re-scan the document and upload the new file."
        )

    return (
        "Image Load Failed",
        f"Could not open the image: {error_str[:200]}",
        "Try a different image file or convert it to JPG/PNG first."
    )


# ─────────────────────────────────────────────
#  AI CLIENT
# ─────────────────────────────────────────────

KANNADA_RE = re.compile(r'[\u0C80-\u0CFF]')

SUPPORTED_LANGUAGES = {
    "Kannada":   {"tesseract": "kan", "name_en": "Kannada"},
    "Hindi":     {"tesseract": "hin", "name_en": "Hindi"},
    "Tamil":     {"tesseract": "tam", "name_en": "Tamil"},
    "Telugu":    {"tesseract": "tel", "name_en": "Telugu"},
    "Malayalam": {"tesseract": "mal", "name_en": "Malayalam"},
}

INDIC_RANGES = {
    "Kannada":   re.compile(r'[\u0C80-\u0CFF]'),
    "Hindi":     re.compile(r'[\u0900-\u097F]'),
    "Tamil":     re.compile(r'[\u0B80-\u0BFF]'),
    "Telugu":    re.compile(r'[\u0C00-\u0C7F]'),
    "Malayalam": re.compile(r'[\u0D00-\u0D7F]'),
}


class AIClient:
    """Unified translation + summarization client for Gemini or Groq."""

    def __init__(self, provider: str, api_key: str):
        self.provider = provider
        self.api_key = api_key
        self._client = None
        self._init_client()

    def _init_client(self):
        if self.provider == "Google Gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel("gemini-2.0-flash")
            except ModuleNotFoundError:
                raise RuntimeError(
                    "No module named 'google'. Run: pip install google-generativeai"
                )
        elif self.provider == "Groq":
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ModuleNotFoundError:
                raise RuntimeError(
                    "No module named 'groq'. Run: pip install groq"
                )

    def _call(self, prompt: str) -> str:
        if self.provider == "Google Gemini":
            response = self._client.generate_content(prompt)
            return response.text.strip()
        elif self.provider == "Groq":
            response = self._client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()

    def test_connection(self) -> Tuple[bool, str]:
        try:
            result = self._call("Say 'OK' in one word.")
            return True, f"Connected! Model responded: {result}"
        except Exception as e:
            return False, str(e)

    def translate(self, text: str, source_lang: str = "Kannada") -> str:
        prompt = (
            f"You are a professional legal document translator.\n"
            f"Translate the following {source_lang} legal document text to English.\n"
            f"Preserve all legal terminology, names, dates, and document structure accurately.\n"
            f"Return ONLY the translated English text, no explanations.\n\n"
            f"--- {source_lang.upper()} TEXT ---\n{text}\n--- END ---"
        )
        return self._call(prompt)

    def summarize(self, text: str) -> str:
        prompt = (
            "You are a legal document analyst.\n"
            "Read the following translated legal document and produce a clear, concise summary.\n"
            "Structure your summary with:\n"
            "1. **Document Type** — what kind of legal document this is\n"
            "2. **Key Parties** — who is involved\n"
            "3. **Main Subject** — what the document is about\n"
            "4. **Important Terms/Obligations** — key clauses or obligations\n"
            "5. **Dates & Deadlines** — any relevant dates\n\n"
            "Be concise, factual, and use plain English.\n\n"
            f"--- DOCUMENT ---\n{text}\n--- END ---"
        )
        return self._call(prompt)


# ─────────────────────────────────────────────
#  OCR HELPERS
# ─────────────────────────────────────────────

def extract_text(image: Image.Image, lang_code: str = "kan") -> Tuple[str, bool]:
    """Returns (text, success). On failure, text contains a user-friendly error."""
    try:
        text = pytesseract.image_to_string(image, lang=lang_code)
        if not text.strip():
            return ("No text detected in this image.", False)
        return (text.strip(), True)
    except Exception as e:
        return (str(e), False)


def convert_pdf_to_images(pdf_file) -> Union[List, str]:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.read())
            tmp_path = tmp.name
        images = convert_from_path(tmp_path, dpi=300)
        os.unlink(tmp_path)
        return images
    except Exception as e:
        return str(e)


# ─────────────────────────────────────────────
#  SESSION STATE DEFAULTS
# ─────────────────────────────────────────────

for _key, _default in {
    "provider": "Google Gemini",
    "api_key": "",
    "client": None,
    "connected": False,
    "source_lang": "Kannada",
}.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    provider = st.selectbox(
        "AI Provider",
        ["Google Gemini", "Groq"],
        index=["Google Gemini", "Groq"].index(st.session_state["provider"]),
        help="Both are free. Gemini = best quality. Groq = fastest.",
    )

    # Reset connected state when provider changes
    if provider != st.session_state["provider"]:
        st.session_state["connected"] = False
        st.session_state["client"] = None
    st.session_state["provider"] = provider

    if provider == "Google Gemini":
        st.markdown(
            '<div class="banner-info">Get a free key at '
            '<a href="https://aistudio.google.com/app/apikey" target="_blank">aistudio.google.com</a>'
            "<br>Free tier: 1,500 req/day · 15 RPM</div>",
            unsafe_allow_html=True,
        )
        model_label = "gemini-2.0-flash"
    else:
        st.markdown(
            '<div class="banner-info">Get a free key at '
            '<a href="https://console.groq.com/keys" target="_blank">console.groq.com</a>'
            "<br>Free tier: 6,000 tokens/min</div>",
            unsafe_allow_html=True,
        )
        model_label = "llama-3.1-8b-instant"

    st.markdown(f"**Model:** `{model_label}`")
    st.markdown("")

    api_key = st.text_input(
        "API Key",
        type="password",
        value=st.session_state["api_key"],
        placeholder="Paste your API key here…",
    )

    if st.button("🔌 Test Connection", use_container_width=True):
        if not api_key.strip():
            st.markdown(
                '<div class="banner-warn">⚠️ No API key entered. Paste your key in the field above before testing.</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.spinner("Testing connection…"):
                try:
                    client = AIClient(provider, api_key.strip())
                    success, msg = client.test_connection()
                    if success:
                        st.session_state["api_key"] = api_key.strip()
                        st.session_state["client"] = client
                        st.session_state["connected"] = True
                        st.markdown(
                            f'<div class="banner-success">✅ Connected to {provider}!</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.session_state["connected"] = False
                        title, reason, fix = parse_api_error(provider, Exception(msg))
                        friendly_error(title, reason, fix)
                except Exception as e:
                    st.session_state["connected"] = False
                    title, reason, fix = parse_api_error(provider, e)
                    friendly_error(title, reason, fix)

    if st.session_state["connected"]:
        st.markdown(
            f'<div class="banner-success">✅ {provider} Connected</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("## 🌐 Source Language")
    source_lang = st.selectbox(
        "Document language",
        list(SUPPORTED_LANGUAGES.keys()),
        index=list(SUPPORTED_LANGUAGES.keys()).index(st.session_state["source_lang"]),
    )
    st.session_state["source_lang"] = source_lang

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(
        "**How to use:**\n"
        "1. Choose an AI provider & enter your free API key\n"
        "2. Click **Test Connection**\n"
        "3. Select source language\n"
        "4. Upload a PDF or image\n"
        "5. Click **Translate & Summarize**"
    )


# ─────────────────────────────────────────────
#  MAIN AREA
# ─────────────────────────────────────────────

st.markdown("# 📄 Legal Document Translator & Summarizer")
st.markdown(
    "Upload a legal document in any supported Indic language — "
    "get an accurate English translation and a structured summary instantly."
)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

if not st.session_state["connected"]:
    st.markdown(
        '<div class="banner-info">👈 <strong>Step 1:</strong> Select an AI provider, paste your free API key, '
        'and click <em>Test Connection</em> in the sidebar to get started.</div>',
        unsafe_allow_html=True,
    )

# ── File Upload ──────────────────────────────
st.markdown('<div class="section-title">Upload Document</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Supported formats: PDF, JPG, JPEG, PNG",
    type=["pdf", "jpg", "jpeg", "png"],
    label_visibility="visible",
)

if uploaded_file is None:
    st.stop()

lang_cfg = SUPPORTED_LANGUAGES[source_lang]
ocr_lang = lang_cfg["tesseract"]
file_type = uploaded_file.type


# ─────────────────────────────────────────────
#  PDF PROCESSING
# ─────────────────────────────────────────────
if file_type == "application/pdf":

    with st.spinner("Converting PDF pages to images…"):
        pdf_images = convert_pdf_to_images(uploaded_file)

    if isinstance(pdf_images, str):
        # pdf_images is an error string
        title, reason, fix = parse_pdf_error(pdf_images)
        friendly_error(title, reason, fix)
        st.stop()

    if len(pdf_images) == 0:
        friendly_error(
            "Empty PDF",
            "The uploaded PDF contains no pages that could be converted to images.",
            "Check that the PDF file is not empty or corrupted and try again."
        )
        st.stop()

    total_pages = len(pdf_images)
    st.markdown(
        f'<div class="banner-info">📑 PDF loaded — <strong>{total_pages} page(s)</strong> detected.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    # ── OCR all pages ────────────────────────
    all_page_texts = []
    ocr_errors = []
    st.markdown('<div class="section-title">Extracted Text</div>', unsafe_allow_html=True)

    for i, img in enumerate(pdf_images):
        with st.expander(f"Page {i + 1}", expanded=(i == 0)):
            col_img, col_txt = st.columns([1, 1], gap="medium")
            with col_img:
                st.image(img, caption=f"Page {i + 1}", use_container_width=True)
            with col_txt:
                extracted, ok = extract_text(img, ocr_lang)
                all_page_texts.append((extracted, ok))
                if ok:
                    st.text_area(
                        f"Extracted text — page {i + 1}",
                        value=extracted,
                        height=280,
                        key=f"ocr_{i}",
                    )
                elif "No text detected" in extracted:
                    st.markdown(
                        '<div class="banner-warn">⚠️ <strong>No text found on this page.</strong><br>'
                        f'Make sure the document is in <strong>{source_lang}</strong> and the scan is clear. '
                        'Very low resolution or skewed scans can cause this.</div>',
                        unsafe_allow_html=True,
                    )
                    ocr_errors.append(i + 1)
                else:
                    title, reason, fix = parse_ocr_error(extracted, ocr_lang)
                    friendly_error(title, reason, fix)
                    ocr_errors.append(i + 1)

    # Pages with actual text
    valid_pages = [(i, txt) for i, (txt, ok) in enumerate(all_page_texts) if ok]

    if not valid_pages:
        friendly_error(
            "No Text Could Be Extracted From Any Page",
            f"Tesseract OCR found no {source_lang} text in any of the {total_pages} page(s). "
            "Possible causes: wrong source language selected, image too blurry, or the document is image-only without clear text.",
            f"1. Confirm the source language is set to '{source_lang}' in the sidebar. "
            "2. Ensure the scan resolution is at least 150 DPI. "
            "3. If the document is in a different language, change the language selector in the sidebar."
        )
        st.stop()

    if ocr_errors:
        st.markdown(
            f'<div class="banner-warn">⚠️ Pages with no extractable text: {ocr_errors}. '
            f'Only pages with text will be translated.</div>',
            unsafe_allow_html=True,
        )

    if not st.session_state["connected"]:
        st.markdown(
            '<div class="banner-warn">⚠️ <strong>AI provider not connected.</strong> '
            'Enter your API key and click <em>Test Connection</em> in the sidebar to translate and summarize.</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    if st.button("⚡ Translate & Summarize All Pages", use_container_width=True, type="primary"):
        client: AIClient = st.session_state["client"]

        st.markdown('<div class="section-title">Translation</div>', unsafe_allow_html=True)
        translated_pages = []
        translation_failed = False

        for idx, page_text in valid_pages:
            with st.spinner(f"Translating page {idx + 1} of {total_pages}…"):
                try:
                    translated = client.translate(page_text, source_lang)
                    translated_pages.append(translated)
                    with st.expander(f"Page {idx + 1} — Translation", expanded=True):
                        st.text_area("", value=translated, height=200, key=f"trans_{idx}")
                except Exception as e:
                    title, reason, fix = parse_api_error(provider, e)
                    friendly_error(f"Page {idx + 1}: {title}", reason, fix)
                    translation_failed = True
                    break  # Stop on first API error — likely affects all pages

        if translation_failed or not translated_pages:
            st.markdown(
                '<div class="banner-warn">⚠️ Translation was incomplete. Summarization skipped.</div>',
                unsafe_allow_html=True,
            )
            st.stop()

        full_translation = "\n\n".join(translated_pages)

        st.markdown('<div class="section-title">Summary</div>', unsafe_allow_html=True)
        with st.spinner("Generating structured summary…"):
            try:
                summary = client.summarize(full_translation)
                st.markdown(
                    f'<div class="card">{summary.replace(chr(10), "<br>")}</div>',
                    unsafe_allow_html=True,
                )
            except Exception as e:
                title, reason, fix = parse_api_error(provider, e)
                friendly_error(title, reason, fix)
                st.markdown(
                    '<div class="banner-info">ℹ️ The translation above is still available even though the summary failed.</div>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────
#  IMAGE PROCESSING
# ─────────────────────────────────────────────
else:
    try:
        image = Image.open(uploaded_file)
    except Exception as e:
        title, reason, fix = parse_image_error(str(e))
        friendly_error(title, reason, fix)
        st.stop()

    st.markdown('<div class="section-title">Document Preview & Extracted Text</div>', unsafe_allow_html=True)
    col_img, col_txt = st.columns([1, 1], gap="medium")

    with col_img:
        st.image(image, caption="Uploaded image", use_container_width=True)

    with col_txt:
        with st.spinner("Extracting text via OCR…"):
            extracted_text, ocr_ok = extract_text(image, ocr_lang)

        if ocr_ok:
            st.text_area(
                f"Extracted {source_lang} text",
                value=extracted_text,
                height=340,
                key="ocr_image",
            )
        elif "No text detected" in extracted_text:
            friendly_error(
                "No Text Detected in Image",
                f"Tesseract OCR could not find any {source_lang} text in this image.",
                f"1. Make sure the source language in the sidebar is set to '{source_lang}'.\n"
                "2. Ensure the image resolution is at least 150 DPI.\n"
                "3. The image should have good contrast — avoid blurry or skewed scans.\n"
                "4. If the text is printed (not handwritten), OCR works significantly better."
            )
            st.stop()
        else:
            title, reason, fix = parse_ocr_error(extracted_text, ocr_lang)
            friendly_error(title, reason, fix)
            st.stop()

    if not st.session_state["connected"]:
        st.markdown(
            '<div class="banner-warn">⚠️ <strong>AI provider not connected.</strong> '
            'Enter your API key and click <em>Test Connection</em> in the sidebar.</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    if st.button("⚡ Translate & Summarize", use_container_width=True, type="primary"):
        client: AIClient = st.session_state["client"]

        col_trans, col_sum = st.columns([1, 1], gap="medium")

        with col_trans:
            st.markdown('<div class="section-title">Translation</div>', unsafe_allow_html=True)
            with st.spinner("Translating…"):
                try:
                    translated_text = client.translate(extracted_text, source_lang)
                    st.text_area(
                        "English Translation",
                        value=translated_text,
                        height=380,
                        key="trans_image",
                    )
                except Exception as e:
                    title, reason, fix = parse_api_error(provider, e)
                    friendly_error(title, reason, fix)
                    st.stop()

        with col_sum:
            st.markdown('<div class="section-title">Summary</div>', unsafe_allow_html=True)
            with st.spinner("Generating summary…"):
                try:
                    summary = client.summarize(translated_text)
                    st.markdown(
                        f'<div class="card">{summary.replace(chr(10), "<br>")}</div>',
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    title, reason, fix = parse_api_error(provider, e)
                    friendly_error(title, reason, fix)
                    st.markdown(
                        '<div class="banner-info">ℹ️ The translation is still available on the left even though summarization failed.</div>',
                        unsafe_allow_html=True,
                    )
