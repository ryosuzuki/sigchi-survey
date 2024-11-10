import json
import os
import requests
from datetime import datetime
from fpdf import FPDF
import tempfile

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def download_image(url, output_dir):
    try:
        response = requests.get(url, headers=HEADERS, stream=True)
        response.raise_for_status()
        file_ext = url.split('.')[-1].split('?')[0]
        if file_ext.lower() not in ['jpg', 'jpeg', 'png', 'gif']:
            file_ext = 'jpg'
        filename = os.path.join(output_dir, f"{hash(url)}.{file_ext}")
        with open(filename, 'wb') as file:
            file.write(response.content)
        return filename
    except Exception as e:
        print(f"Failed to download image {url}: {e}")
        return None

def wrap_text(text, max_width=190):
    wrapped = ''
    current_line = ''
    for word in text.split():
        if len(current_line + word) < max_width:
            current_line += word + ' '
        else:
            wrapped += current_line.strip() + '\n'
            current_line = word + ' '
    wrapped += current_line.strip()
    return wrapped

def generate_slides(json_data, output_dir="slides"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    temp_dir = tempfile.mkdtemp()

    for i, result in enumerate(json_data['results']):
        title = result['title']
        content = wrap_text(result['abstract'], max_width=90)  # Properly wrapped text
        figures = result['figure_urls'][:3]

        pdf.add_page()
        pdf.set_font("Helvetica", size=16)
        pdf.multi_cell(0, 10, title)
        pdf.set_font("Helvetica", size=12)
        try:
            pdf.multi_cell(0, 10, content)
        except FPDFException:
            pdf.multi_cell(0, 10, wrap_text(content[:500]))

        for url in figures:
            image_path = download_image(url, temp_dir)
            if image_path:
                pdf.image(image_path, x=10, w=100)

    pdf_output = os.path.join(output_dir, f"slides_{timestamp}.pdf")
    pdf.output(pdf_output)
    print(f"Slides saved as PDF: {pdf_output}")

if __name__ == "__main__":
    input_file = "combined_results.json"
    json_data = load_json(input_file)
    generate_slides(json_data)
