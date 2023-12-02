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

# Function to process a batch of pages as images
def process_batch(start, end, batch_number):
    # Convert a range of pages to images
    images = convert_from_path(pdf_path, first_page=start, last_page=end, dpi=200)

    # Perform OCR on each image after preprocessing
    for i, image in enumerate(images):
        # Preprocess the image
        image = preprocess_image(image)

        # Perform OCR using pytesseract
        text = pytesseract.image_to_string(image)

        # Save the text in a file
        text_file_path = f'/content/batch_texts/batch_{batch_number}_page_{start + i}.txt'
        with open(text_file_path, 'w') as file:
            file.write(text)

        # Save the image
        image_file_path = f'/content/batch_images/batch_{batch_number}_page_{start + i}.png'
        image.save(image_file_path)

        # Display the image inline
        display(image)

    # Clear the images list to free up memory
    del images


def example():
    # Assuming Tesseract OCR is already installed
    # If not, install it using: !apt install tesseract-ocr

    # Define the path to your PDF file
    pdf_path = '/content/1936-1942 Chevrolet Parts Book.pdf'  # Replace with the path to your PDF

    # Create directories for saving output
    os.makedirs('/content/batch_texts', exist_ok=True)
    os.makedirs('/content/batch_images', exist_ok=True)

    # Define the size of each batch
    batch_size = 10  # Process 10 pages at a time, adjust based on your environment's capability

    # Calculate the number of batches needed
    total_pages = 20  # Total number of pages in your PDF
    batches = (total_pages + batch_size - 1) // batch_size

    # Process each batch
    for batch in range(batches):
        start_page = batch * batch_size + 1
        end_page = min(start_page + batch_size - 1, total_pages)
        process_batch(start_page, end_page, batch)


def read_file(file_path):
    if file_path.endswith(".txt"):
        with open(file_path, 'r') as f:
            return f.read()

    # Try to extract text from the PDF using pypdf
    text = read_pdf(file_path)
    if len(text) > 200:
        return text

    # Alternatively, OCR the PDF using pdf2image and pytesseract
    images = convert_from_path(file_path, first_page=1, dpi=200, poppler_path='/opt/homebrew/Cellar/poppler/23.12.0/bin')
    text = ""
    for image in images:
        # Preprocess the image
        image = preprocess_image(image)

        # Perform OCR using pytesseract
        text += pytesseract.image_to_string(image) + "\n\n"

    return text


def read_pdf(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text.strip()


if __name__ == "__main__":
    print(read_file(sys.argv[1]))