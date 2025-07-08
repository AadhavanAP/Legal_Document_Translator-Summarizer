📄 Legal Document Translator & Summarizer
An intelligent Streamlit application designed to translate and summarize legal documents from Kannada to English. This tool leverages Optical Character Recognition (OCR) to extract text from images and PDFs, followed by advanced AI models from the Hugging Face Hub for seamless translation and summarization.

## ✨ Key Features

Multi-Format Upload: Supports both image (.jpg, .png, .jpeg) and multi-page .pdf files.

Advanced OCR: Uses Tesseract to accurately extract Kannada text from documents.

High-Quality Translation: Integrates with the facebook/nllb-200-distilled-600M model for reliable Kannada to English translation.

Intelligent Summarization: Employs the facebook/bart-large-cnn model to generate concise summaries of the translated text.

Interactive UI: A user-friendly interface built with Streamlit, providing real-time progress updates.

Robust API Handling: Features automatic retries with exponential backoff for resilient communication with external APIs.

Page-by-Page Processing: For PDFs, each page is processed and displayed individually, maintaining the document's structure.

🚀 How It Works
API Setup: The user starts by entering their Hugging Face API token. The app includes a built-in connection test.

Document Upload: Upload a Kannada legal document as a PDF or an image file.

Text Extraction:

For PDFs, the file is converted into a series of images, one for each page.

pytesseract then performs OCR on each image to extract the Kannada text.

Translation: The extracted text is broken into manageable chunks and sent to the Hugging Face Inference API for translation to English.

Summarization: The translated English text is then sent to a summarization model to create a compact and coherent summary.

Display Results: The extracted text, full translation, and the final summary are all displayed in a clean, side-by-side layout.

🛠️ Setup and Installation
Follow these steps to run the project locally.

Prerequisites
Python 3.8 or higher

Tesseract OCR Engine

Windows: Download and install from Tesseract at UB Mannheim. Make sure to add the installation directory to your system's PATH.

macOS: brew install tesseract

Linux: sudo apt-get install tesseract-ocr libtesseract-dev

Poppler (for PDF processing)

Windows: Download the latest version from this blog. Add the bin/ directory to your system's PATH.

macOS: brew install poppler

Linux: sudo apt-get install poppler-utils

Installation Steps
Clone the Repository

Bash

git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
Create a Virtual Environment
It's recommended to use a virtual environment to manage dependencies.

Bash

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies
Create a requirements.txt file with the following content:

Plaintext

streamlit
pytesseract
Pillow
pdf2image
requests
tenacity
Then, run the installation command:

Bash

pip install -r requirements.txt
Get a Hugging Face API Token

Go to Hugging Face and create an account.

Navigate to your Profile -> Settings -> Access Tokens.

Create a new token with the "read" role.

▶️ How to Run the App
Execute the Streamlit command from your terminal:

Bash

streamlit run app.py
(Assuming your Python script is named app.py)

Open your web browser and go to http://localhost:8501.

Paste your Hugging Face API token in the "API Setup" section and start translating your documents!

💻 Technology Stack
Application Framework: Streamlit

OCR Engine: Tesseract (pytesseract wrapper)

PDF Processing: pdf2image

Image Handling: Pillow

API Communication: requests, tenacity

AI Models (via Hugging Face API):

Translation: facebook/nllb-200-distilled-600M

Summarization: facebook/bart-large-cnn

🤝 Contributing
Contributions are welcome! If you'd like to improve the application or add new features, please follow these steps:

Fork the repository.

Create a new branch (git checkout -b feature/YourAmazingFeature).

Make your changes and commit them (git commit -m 'Add some amazing feature').

Push to the branch (git push origin feature/YourAmazingFeature).

Open a Pull Request.

📄 License
This project is licensed under the MIT License. See the LICENSE file for more details.