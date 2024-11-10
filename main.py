import os
import json
import sys
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import re

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def load_data(directory):
    papers = []
    for filename in os.listdir(directory):
        if filename.endswith("_program.json"):
            with open(os.path.join(directory, filename), 'r') as file:
                data = json.load(file)
                if "contents" in data:
                    for paper in data["contents"]:
                        paper["venue"] = data["conference"].get("shortName", "Unknown")
                        paper["year"] = data["conference"].get("year", "Unknown")
                        papers.append(paper)
    return papers

def search_papers(papers, keyword, max_results=3):
    keyword = keyword.lower()
    matches = []
    for paper in papers:
        if any(keyword in (paper.get(key, '') or '').lower() for key in ['title', 'abstract']):
            matches.append({
                "id": paper.get("id"),
                "title": paper.get("title"),
                "abstract": paper.get("abstract"),
                "authors": paper.get("authors"),
                "sessionIds": paper.get("sessionIds", []),
                "venue": paper.get("venue"),
                "year": paper.get("year")
            })
        if len(matches) >= max_results:
            break
    return matches

def search_images_selenium(query, max_results=3, delay=5):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}&t=h_&iax=images&ia=images"
        driver.get(search_url)
        time.sleep(delay)  # Wait for the page to load

        image_elements = driver.find_elements(By.CSS_SELECTOR, "img.tile--img__img")
        image_urls = [img.get_attribute("src") for img in image_elements[:max_results] if img.get_attribute("src")]

        print(f"Found {len(image_urls)} images.")
        return image_urls
    except Exception as e:
        print(f"Error during image search with Selenium: {e}")
        return []
    finally:
        driver.quit()

def save_combined_json(directory, papers_with_images):
    data_to_save = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": papers_with_images
    }

    file_path = os.path.join(directory, "results.json")
    with open(file_path, 'w') as file:
        json.dump(data_to_save, file, indent=4)
    print(f"Saved combined results to {file_path}")
    return file_path

def load_json(file_path):
    """Load JSON data from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_slides_html(data, output_file):
    """Generate an HTML file with slides from JSON data using Reveal.js."""

    html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Presentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js/dist/theme/black.css">
</head>
<body>
    <div class="reveal">
        <div class="slides">
    """
    for paper in data.get("results", []):
        title = paper.get('title', 'No Title')
        abstract = paper.get('abstract', 'No abstract available')
        figure_urls = paper.get('figure_urls', [])
        html_content += f"<section><h2>{title}</h2><p>{abstract}</p></section>"
        for url in figure_urls:
            html_content += f"<section><img src='{url}' alt='Figure'></section>"

    html_content += """
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js/dist/reveal.js"></script>
    <script>Reveal.initialize();</script>
</body>
</html>
    """

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Slides saved to {output_file}")

def sanitize_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '-').lower()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <keyword>")
        sys.exit(1)

    keyword = sys.argv[1]
    sanitized_keyword = sanitize_filename(keyword)
    output_directory = os.path.join("results", sanitized_keyword)

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    papers = load_data('data')
    results = search_papers(papers, keyword)

    combined_results = []
    if results:
        for paper in results:
            print(f"Searching images for: {paper['title']}")
            figure_urls = search_images_selenium(paper["title"])
            paper["figure_urls"] = figure_urls
            combined_results.append(paper)
            time.sleep(1)  # Avoid rate limiting

        json_path = save_combined_json(output_directory, combined_results)
        html_path = os.path.join(output_directory, "slides.html")
        json_data = load_json(json_path)
        generate_slides_html(json_data, html_path)
    else:
        print(f"No papers found for keyword '{keyword}'.")
