import sys
import os

import cv2
import numpy as np
from pdf2image import convert_from_path # first: brew install poppler. For heroku: https://stackoverflow.com/questions/54739063/install-poppler-onto-heroku-server-django
import pytesseract  # first: brew install tesseract; brew install tesseract-lang; ln /opt/homebrew/Cellar/tesseract/5.3.3/bin/tesseract /usr/local/bin/tesseract
from PIL import Image
from pypdf import PdfReader


# Function to preprocess an image with OpenCV
def preprocess_image(image):
    image_cv = np.array(image)

    # Check for GPU availability for OpenCV
    use_gpu = cv2.cuda.getCudaEnabledDeviceCount() > 0

    if use_gpu:
        # Upload image to GPU
        image_gpu = cv2.cuda_GpuMat(image_cv)
        # Convert to grayscale
        gray_gpu = cv2.cuda.cvtColor(image_gpu, cv2.COLOR_BGR2GRAY)
        # Download image from GPU to CPU
        image_cv = gray_gpu.download()
    else:
        # Convert to grayscale
        image_cv = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    return Image.fromarray(image_cv)


def read_file(file_path, poppler_path=None):
    if file_path.endswith(".txt"):
        with open(file_path, 'r') as f:
            return f.read()

    # Try to extract text from the PDF using pypdf
    text = read_pdf_with_pypdf(file_path)
    if len(text) > 200:
        return text

    if poppler_path:
        # Alternatively, OCR the PDF using pdf2image and pytesseract
        images = convert_from_path(file_path, first_page=1, dpi=200, poppler_path=poppler_path)
        text = ""
        for image in images:
            # Preprocess the image
            image = preprocess_image(image)

            # Perform OCR using pytesseract
            text += pytesseract.image_to_string(image) + "\n\n"

    return text


def read_pdf_with_pypdf(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text.strip()


if __name__ == "__main__":
    poppler_path = '/opt/homebrew/Cellar/poppler/23.12.0/bin'
    print(read_file(sys.argv[1]), poppler_path=poppler_path)