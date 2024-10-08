from flask import Flask, request, render_template, send_from_directory, redirect, url_for
from flask_socketio import SocketIO
import os
from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np
import logging
from flask_socketio import emit


logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
socketio = SocketIO(app)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Set the path to the Poppler binaries
poppler_path = os.getenv('POPPLER_PATH', default='/usr/local/bin/')

# Set the path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_CMD', default='/usr/local/bin/tesseract')

# Ensure the upload and processed folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    message = request.args.get('message')
    return render_template('index.html', message=message)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index', message="No file part"))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index', message="No selected file"))
    
    target_page_number = request.form.get('target_page_number', type=int)
    subject = request.form.get('subject')

    if target_page_number is None:
        return redirect(url_for('index', message="Target page number is required"))
    if not subject:
        return redirect(url_for('index', message="Subject is required"))

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        socketio.start_background_task(process_pdf, file_path, filename, target_page_number, subject)
        return redirect(url_for('index', message="File uploaded and processing started."))

def process_pdf(pdf_path, pdf_name, target_page_number, subject):
    try:
        pdf_base_name = os.path.splitext(pdf_name)[0]

        # Create a folder based on the subject inside the processed folder
        subject_folder = os.path.join(app.config['PROCESSED_FOLDER'], subject)
        os.makedirs(subject_folder, exist_ok=True)

        folder_path = os.path.join(subject_folder, pdf_base_name)
        os.makedirs(folder_path, exist_ok=True)

        target_sentences = ["Paper 1 Multiple Choice ", "PAPER 1 Multiple Choice ", "Paper 1 AS Level Multiple Choice ", " "]
        pages = convert_from_path(pdf_path=pdf_path, poppler_path=poppler_path, dpi=300)

        target_found = False

        for page_number, page in enumerate(pages, start=1):
            text = pytesseract.image_to_string(page)
            logging.debug(f'Page {page_number} text: {text[:100]}')  # Log the first 100 characters of the page text
            if any(sentence in text for sentence in target_sentences):
                target_found = True
                break

        if target_found:
            count = 1
            question = 1

            for page in pages[target_page_number - 1:]:
                page_array = np.array(page)
                gray = cv2.cvtColor(page_array, cv2.COLOR_BGR2GRAY)
                height, width = gray.shape

                # Crop the footer by 10px
                cropped_page = page.crop((0, 0, width, height - 10))

                text = pytesseract.image_to_string(cropped_page)
                boxes = pytesseract.image_to_boxes(cropped_page)
                lines = text.split('\n')
                line_y_coordinates = []

                for line in lines:
                    if line.strip().startswith(str(count)):
                        first_digit_found = False
                        second_digit_found = False
                        for box in boxes.splitlines():
                            b = box.split()
                            char, x, y, w, h = b[0], int(b[1]), int(b[2]), int(b[3]), int(b[4])
                            if char.isdigit() and x <= 300:
                                if not first_digit_found and char == str(count)[0]:
                                    first_digit_found = True
                                elif first_digit_found and len(str(count)) > 1 and char == str(count)[1]:
                                    second_digit_found = True

                                if (first_digit_found and len(str(count)) == 1) or (first_digit_found and second_digit_found):
                                    line_y_coordinates.append((count, y))
                                    count += 1
                                    break

                line_y_coordinates.sort(key=lambda coord: coord[1], reverse=True)

                for i in range(len(line_y_coordinates) - 1):
                    start_line, start_y = line_y_coordinates[i]
                    end_line, end_y = line_y_coordinates[i + 1]
                    upper = min(height - start_y, height - end_y) - 50
                    lower = max(height - start_y, height - end_y) - 50
                    if lower > upper:
                        cropped_image = cropped_page.crop((0, upper, width, lower))
                        cropped_image_path = os.path.join(folder_path, f'{pdf_base_name}_q{question}.png')
                        cropped_image.save(cropped_image_path)
                        logging.debug(f'Saved cropped image: {cropped_image_path}')
                        question += 1

                if line_y_coordinates:
                    last_line, last_y = line_y_coordinates[-1]
                    upper = height - last_y - 70
                    lower = height - 70
                    if lower > upper:
                        cropped_image = cropped_page.crop((0, upper, width, lower-150))
                        cropped_image_path = os.path.join(folder_path, f'{pdf_base_name}_q{question}.png')
                        cropped_image.save(cropped_image_path)
                        logging.debug(f'Saved cropped image: {cropped_image_path}')
                        question += 1

        else:
            logging.debug("None of the target sentences found in the PDF.")
        
        # Emit the 'processing_done' event after processing is done
        socketio.emit('processing_done')

    except Exception as e:
        logging.error(f"Error during processing: {e}")
        socketio.emit('processing_done')  # Still emit to ensure frontend knows processing is finished

@app.route('/processed')
def list_processed_files():
    processed_files = {}
    for dirpath, dirnames, filenames in os.walk(app.config['PROCESSED_FOLDER']):
        logging.debug(f'Directory {dirpath} with files: {filenames}')  # Log directory and files
        if filenames:
            folder_name = os.path.basename(dirpath)  # The last folder name in the path
            rel_dirpath = os.path.relpath(dirpath, app.config['PROCESSED_FOLDER'])
            processed_files[folder_name] = [os.path.join(rel_dirpath, filename) for filename in filenames]
    
    return render_template('index.html', processed_files=processed_files)

# Route to serve files from the processed folder
@app.route('/processed/<path:filename>')
def serve_processed_file(filename):
    directory = os.path.join(app.config['PROCESSED_FOLDER'], os.path.dirname(filename))
    return send_from_directory(directory, os.path.basename(filename), as_attachment=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
