# PDF Processing Flask App

This Flask application allows you to upload PDF files, extract specific pages, crop certain sections, and save them as images. It provides real-time updates using Flask-SocketIO.

## Features

- Upload a PDF file and extract specific pages based on a target page number.
- Automatically crop the footer and split the page into individual questions.
- Processed images are saved in a folder based on the subject name.
- Real-time feedback using a progress modal on the front-end.
- List processed files in the `processed` directory.

## Prerequisites

Make sure you have the following installed:

- Python 3.x
- [Poppler](https://poppler.freedesktop.org/) (for PDF conversion)
- [Tesseract](https://github.com/tesseract-ocr/tesseract) (for OCR)

### macOS Setup (for Poppler and Tesseract)

Install both Poppler and Tesseract using Homebrew:

    brew install poppler
    brew install tesseract

Installation
Clone the repository:

    git clone https://github.com/yourusername/pdf-processing-app.git
    cd pdf-processing-app

Install the required dependencies:

    pip install -r requirements.txt

Set environment variables for Poppler and Tesseract (optional if installed via Homebrew):

    export POPPLER_PATH="/usr/local/bin"
    export TESSERACT_PATH="/usr/local/bin"

    Alternatively, you can set the paths directly in your app.py:

        poppler_path = '/usr/local/bin'
        pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

Running the Application
To run the application locally, use the following command:

    python app.py

By default, the app will run at http://127.0.0.1:5000/.

Usage
Open the app in your browser at http://127.0.0.1:5000/.
Upload a PDF file and specify the target page number and subject.
The application will process the PDF, split the questions, and save the cropped images in the processed folder.
Real-time updates will be provided via a modal.

Troubleshooting
If you encounter issues such as "Unable to get page count," ensure Poppler is installed correctly and available in your PATH.

You can manually check Poppler installation by running:

    which pdfinfo

If Tesseract is not recognized, ensure its path is set properly or install it via Homebrew:

    brew install tesseract

License
This project is licensed under the MIT License.

```

```
