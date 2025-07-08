import streamlit as st
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import re
import requests
import io
import os
import tempfile
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Maximum retries for API calls
MAX_RETRIES = 3
INITIAL_WAIT_TIME = 1  # seconds
MAX_WAIT_TIME = 10    # seconds

class APIError(Exception):
    pass

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=INITIAL_WAIT_TIME, max=MAX_WAIT_TIME),
    retry=retry_if_exception_type(APIError)
)
def make_api_request(url, headers, payload):
    """
    Make API request with retry logic
    """
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response
    elif response.status_code == 503:
        raise APIError("Service temporarily unavailable")
    else:
        raise APIError(f"API error: {response.status_code}")

def test_api_connection(api_token):
    """
    Test the connection to the Hugging Face API
    """
    API_URL = "https://api-inference.huggingface.co/models/facebook/nllb-200-distilled-600M"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    try:
        payload = {
            "inputs": "ನಮಸ್ಕಾರ",
            "parameters": {"src_lang": "kan_Knda", "tgt_lang": "eng_Latn"}
        }
        response = make_api_request(API_URL, headers, payload)
        return True, "API connection successful!"
    except APIError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def clean_text(text):
    """Clean and normalize text"""
    text = ' '.join(text.split())
    return text.strip()

def is_kannada(text):
    """Check if text contains Kannada characters"""
    kannada_pattern = re.compile(r'[\u0C80-\u0CFF]')
    return bool(kannada_pattern.search(text))

def extract_text(image, lang='kan'):
    """Extract text from image using OCR"""
    try:
        text = pytesseract.image_to_string(image, lang=lang)
        return text if text.strip() else "No text detected"
    except Exception as e:
        return f"Error: {str(e)}"

def split_text(text, max_length=300):
    """Split text into manageable chunks"""
    sentences = text.split('.')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            current_chunk += sentence + '.'
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + '.'
            
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def translate_text_api_page_by_page(text, api_token):
    """Translate text from Kannada to English"""
    API_URL = "https://api-inference.huggingface.co/models/facebook/nllb-200-distilled-600M"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        text = clean_text(text)
        if not is_kannada(text):
            return text

        chunks = split_text(text)
        translated_chunks = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks, 1):
            try:
                st.progress(i / total_chunks, text=f"Translating chunk {i}/{total_chunks}")
                
                payload = {
                    "inputs": chunk,
                    "parameters": {
                        "src_lang": "kan_Knda",
                        "tgt_lang": "eng_Latn",
                        "max_length": 512,
                        "temperature": 0.7,
                        "repetition_penalty": 1.5
                    }
                }
                
                response = make_api_request(API_URL, headers, payload)
                result = response.json()
                
                if isinstance(result, list) and len(result) > 0:
                    translated_chunks.append(result[0]['translation_text'])
                
            except APIError as e:
                st.warning(f"Error translating chunk {i}: {str(e)}. Retrying...")
                time.sleep(2)
                try:
                    response = make_api_request(API_URL, headers, payload)
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        translated_chunks.append(result[0]['translation_text'])
                except Exception as retry_error:
                    st.error(f"Failed to translate chunk {i} after retry: {str(retry_error)}")
                    translated_chunks.append(f"[Translation failed for this section]")
            
            except Exception as e:
                st.error(f"Unexpected error translating chunk {i}: {str(e)}")
                translated_chunks.append("[Translation error]")

        return ' '.join(translated_chunks)

    except Exception as e:
        st.error(f"Translation error: {str(e)}")
        return "Translation failed. Please try again."

def summarize_text(text, api_token):
    """Generate a summary of the translated text"""
    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        text = clean_text(text)
        chunks = split_text(text, max_length=1000)
        
        summaries = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks, 1):
            st.progress(i / total_chunks, text=f"Summarizing chunk {i}/{total_chunks}")
            
            try:
                payload = {
                    "inputs": chunk,
                    "parameters": {
                        "max_length": 150,
                        "min_length": 50,
                        "do_sample": True,
                        "top_p": 0.95,
                        "temperature": 0.7,
                        "repetition_penalty": 1.2
                    }
                }
                
                response = make_api_request(API_URL, headers, payload)
                result = response.json()
                
                if isinstance(result, list) and len(result) > 0:
                    summaries.append(result[0]['summary_text'])
                
            except APIError as e:
                st.warning(f"Error summarizing chunk {i}: {str(e)}. Retrying...")
                try:
                    time.sleep(5)
                    response = make_api_request(API_URL, headers, payload)
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        summaries.append(result[0]['summary_text'])
                except Exception as retry_error:
                    st.error(f"Failed to summarize chunk {i} after retry")
                    sentences = chunk.split('.')[:3]
                    summaries.append('. '.join(sentences) + '.')
            
            except Exception as e:
                st.error(f"Unexpected error summarizing chunk {i}: {str(e)}")
                sentences = chunk.split('.')[:3]
                summaries.append('. '.join(sentences) + '.')
        
        return ' '.join(summaries)

    except Exception as e:
        st.error(f"Summarization error: {str(e)}")
        return "Summarization failed. Please try again."

def convert_pdf_to_images(pdf_file):
    """Convert PDF file to list of images"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_file.read())
            temp_file_path = temp_file.name
        
        images = convert_from_path(temp_file_path, dpi=300)
        os.unlink(temp_file_path)
        return images
    except Exception as e:
        return f"Error converting PDF: {str(e)}"

def main():
    st.set_page_config(
        page_title="Legal Document Translator And Summarizer",
        page_icon="📄",
        layout="wide"
    )

    if 'api_token' not in st.session_state:
        st.session_state['api_token'] = None
    
    st.title("Legal Document Translator And Summarizer")
    
    # API Setup Section
    with st.expander("📡 API Setup (Click to expand)", expanded=not st.session_state['api_token']):
        st.markdown("""
        ### How to get your Hugging Face API token:
        1. Go to [Hugging Face](https://huggingface.co/join) and create an account
        2. Click your profile picture → Settings
        3. Go to Access Tokens in the left sidebar
        4. Click "New token" and create a token with "read" role
        5. Copy and paste the token below
        """)
        
        api_token = st.text_input(
            "Enter your Hugging Face API token",
            type="password",
            value=st.session_state['api_token'] if st.session_state['api_token'] else ""
        )
        
        if st.button("Test Connection"):
            if api_token:
                with st.spinner("Testing API connection..."):
                    success, message = test_api_connection(api_token)
                    if success:
                        st.success(message)
                        st.session_state['api_token'] = api_token
                    else:
                        st.error(message)
            else:
                st.warning("Please enter an API token first")

    # File Upload Section
    st.subheader("Upload Document")
    uploaded_file = st.file_uploader(
        "Choose an image or PDF file",
        type=["jpg", "jpeg", "png", "pdf"],
        help="Supported formats: JPG, JPEG, PNG, PDF"
    )
    
    if uploaded_file is not None:
        file_type = uploaded_file.type
        
        # Handle PDF files
        if file_type == "application/pdf":
            with st.spinner("Converting PDF to images..."):
                pdf_images = convert_pdf_to_images(uploaded_file)
                
            if isinstance(pdf_images, str):
                st.error(pdf_images)
            else:
                st.subheader("Extracted Text from PDF")
                all_text = ""
                
                col1, col2 = st.columns(2)
                
                for i, image in enumerate(pdf_images):
                    with col1:
                        st.image(image, caption=f"Page {i+1}", use_column_width=True)
                    with col2:
                        extracted_text = extract_text(image)
                        st.text_area(f"Extracted Text (Page {i+1})", value=extracted_text, height=150)
                        all_text += extracted_text + "\n"
                
                if all_text.strip() and "Error" not in all_text:
                    if st.session_state['api_token']:
                        if st.button("Translate and Summarize"):
                            st.subheader("Translated Text (Kannada to English)")
                            
                            progress_container = st.empty()
                            translated_pages = []
                            
                            for i, image in enumerate(pdf_images):
                                page_text = extract_text(image)
                                if page_text.strip() and "Error" not in page_text:
                                    progress_container.text(f"Translating Page {i+1}...")
                                    translated_page = translate_text_api_page_by_page(
                                        page_text,
                                        st.session_state['api_token']
                                    )
                                    translated_pages.append(f"--- Page {i+1} Translation ---\n{translated_page}")
                                    st.text_area(f"Page {i+1} Translation", value=translated_page, height=150)
                            
                            progress_container.empty()
                            
                            if translated_pages:
                                full_translation = "\n\n".join(translated_pages)
                                with st.spinner("Generating Summary..."):
                                    summary = summarize_text(full_translation, st.session_state['api_token'])
                                    st.subheader("Document Summary")
                                    st.write(summary)
                    else:
                        st.warning("Please set up your API token in the API Setup section above")
        
        # Handle Image files
        else:
            image = Image.open(uploaded_file)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(image, caption="Uploaded Image", use_column_width=True)
            
            with col2:
                with st.spinner("Extracting text..."):
                    extracted_text = extract_text(image)
                st.subheader("Extracted Kannada Text")
                st.text_area("", value=extracted_text, height=200)
            
            if extracted_text.strip() and "Error" not in extracted_text:
                if st.session_state['api_token']:
                    if st.button("Translate and Summarize"):
                        with st.spinner("Translating..."):
                            translated_text = translate_text_api_page_by_page(
                                extracted_text,
                                st.session_state['api_token']
                            )
                        st.subheader("Translated Text")
                        st.text_area("Translation", value=translated_text, height=200)
                        
                        with st.spinner("Generating Summary..."):
                            summary = summarize_text(translated_text, st.session_state['api_token'])
                        st.subheader("Summary")
                        st.write(summary)
                else:
                    st.warning("Please set up your API token in the API Setup section above")

    # Add footer with instructions
    st.markdown("---")
    st.markdown("""
    ### Instructions:
    1. First, set up your Hugging Face API token in the API Setup section
    2. Upload either a PDF document or an image containing Kannada text
    3. The system will extract the text from your document
    4. Click "Translate and Summarize" to get the English translation and a summary
    """)

if __name__ == "__main__":
    main()
