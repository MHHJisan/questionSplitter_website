def process_pdf(pdf_path, pdf_name):
    global processing_completed
    pdf_base_name = os.path.splitext(pdf_name)[0]
    folder_path = os.path.join(app.config['PROCESSED_FOLDER'], pdf_base_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    target_sentences = ["Paper 1 Multiple Choice ", "PAPER 1 Multiple Choice "]
    pages = convert_from_path(pdf_path=pdf_path, poppler_path='/usr/local/bin', dpi=300)

    target_found = False
    target_page_number = 0

    for page_number, page in enumerate(pages, start=1):
        text = pytesseract.image_to_string(page)
        logging.debug(f'Page {page_number} text: {text[:100]}')  # Log the first 100 characters of the page text
        if any(sentence in text for sentence in target_sentences):
            target_found = True
            target_page_number = page_number
            break

    if target_found:
        max_distance_left_pixels = 300
        count = 1  # This will be used to identify the question number

        for page_number, page in enumerate(pages[target_page_number - 1:], start=target_page_number):
            page_array = np.array(page)
            gray = cv2.cvtColor(page_array, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape

            text = pytesseract.image_to_string(page)
            boxes = pytesseract.image_to_boxes(page)
            lines = text.split('\n')
            line_y_coordinates = []

            for line in lines:
                if line.strip().startswith(str(count)):
                    for box in boxes.splitlines():
                        b = box.split()
                        char, x, y, w, h = b[0], int(b[1]), int(b[2]), int(b[3]), int(b[4])
                        if char.isdigit() and x <= max_distance_left_pixels:
                            if line.strip().startswith(str(count)):
                                line_y_coordinates.append((count, height - y))  # y-coordinate is inverted in images
                                count += 1
                                break

            line_y_coordinates.sort(key=lambda coord: coord[1], reverse=True)

            # Crop each question individually
            for i in range(len(line_y_coordinates)):
                start_line, start_y = line_y_coordinates[i]
                if i < len(line_y_coordinates) - 1:
                    end_y = line_y_coordinates[i + 1][1]
                else:
                    end_y = 50  # Crop until the bottom of the page

                # Ensure valid crop coordinates
                upper = min(start_y - 50, end_y)
                lower = max(start_y - 50, end_y)

                if lower > upper:
                    cropped_image = page.crop((0, upper, width, lower))
                    cropped_image_path = os.path.join(folder_path, f'{pdf_base_name}_q{start_line}.png')
                    cropped_image.save(cropped_image_path)
                    logging.debug(f'Saved cropped image: {cropped_image_path}')
        
        processing_completed = True
        logging.debug("Processing completed.")
    else:
        logging.debug("None of the target sentences found in the PDF.")
