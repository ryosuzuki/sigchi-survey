import os
import json
import sys
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup

SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
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

def search_papers(papers, keyword):
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
    return matches

def search_semantic_scholar(title):
    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_API_URL,
            params={
                "query": title,
                "fields": "title,url,authors",
                "limit": 1
            }
        )
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            print(f"Error: {response.status_code} while fetching data for {title}")
    except Exception as e:
        print(f"Exception occurred: {e}")
    return []

def scrape_figures(semantic_scholar_url, max_retries=5, delay=5):
    for attempt in range(max_retries):
        try:
            response = requests.get(semantic_scholar_url, headers=HEADERS)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                figures = soup.find_all('img', {'class': 'figure__image'})
                figure_urls = [fig['src'] for fig in figures if 'src' in fig.attrs]
                return figure_urls
            elif response.status_code == 202:
                print(f"Page is not ready (Attempt {attempt + 1}/{max_retries}). Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Failed to retrieve page {semantic_scholar_url}. Status code: {response.status_code}")
                break
        except Exception as e:
            print(f"Exception occurred while scraping figures: {e}")
            break
    return []

def download_figures(figure_urls, output_dir="figures"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for idx, url in enumerate(figure_urls):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                filename = os.path.join(output_dir, f"figure_{idx + 1}.png")
                with open(filename, 'wb') as file:
                    file.write(response.content)
                print(f"Downloaded: {filename}")
            else:
                print(f"Failed to download image from {url}")
        except Exception as e:
            print(f"Error downloading figure from {url}: {e}")

def save_individual_json(paper, result, figures):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"semantic_scholar_{timestamp}.json"
    data_to_save = {
        "searched_paper": paper,
        "semantic_scholar_result": result,
        "figures": figures
    }
    with open(filename, 'w') as file:
        json.dump(data_to_save, file, indent=4)
    print(f"Saved results to {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_papers.py <keyword>")
        sys.exit(1)

    keyword = sys.argv[1]
    papers = load_data('data')
    results = search_papers(papers, keyword)

    if results:
        for paper in results:
            scholar_data = search_semantic_scholar(paper["title"])
            if scholar_data:
                scholar_url = scholar_data[0]["url"]
                figure_urls = scrape_figures(scholar_url)
                download_figures(figure_urls)
                save_individual_json(paper, scholar_data, figure_urls)
            else:
                print(f"No Semantic Scholar data found for: {paper['title']}")
            time.sleep(1)  # Pause to avoid rate limiting
        print(f"Found {len(results)} papers matching '{keyword}'. Semantic Scholar data saved.")
    else:
        print(f"No papers found for keyword '{keyword}'.")
