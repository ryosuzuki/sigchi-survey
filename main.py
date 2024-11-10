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
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("start-maximized")
    options.add_argument("--disable-dev-shm-usage")

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

def save_combined_json(filename, papers_with_images):
    data_to_save = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": papers_with_images
    }

    with open(filename, 'w') as file:
        json.dump(data_to_save, file, indent=4)
    print(f"Saved combined results to {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <keyword>")
        sys.exit(1)

    keyword = sys.argv[1]
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

        # Combine all results into a single JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"combined_results_{timestamp}.json"
        save_combined_json(output_filename, combined_results)

        print(f"Found {len(results)} papers matching '{keyword}'. Combined data saved.")
    else:
        print(f"No papers found for keyword '{keyword}'.")
