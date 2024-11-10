import os
import json
import sys

def load_data(directory):
    papers = []
    for filename in os.listdir(directory):
        if filename.endswith("_program.json"):
            with open(os.path.join(directory, filename), 'r') as file:
                data = json.load(file)
                if "contents" in data:
                    for paper in data["contents"]:
                        # Add venue and year from the conference metadata
                        paper["venue"] = data["conference"]["shortName"] if "conference" in data else "Unknown"
                        paper["year"] = data["conference"]["year"] if "conference" in data else "Unknown"
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

def save_to_json(results, output_file):
    with open(output_file, 'w') as file:
        json.dump(results, file, indent=4)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_papers.py <keyword>")
        sys.exit(1)

    keyword = sys.argv[1]
    papers = load_data('data')
    results = search_papers(papers, keyword)

    if results:
        save_to_json(results, 'search_results.json')
        print(f"Found {len(results)} papers matching '{keyword}'. Results saved to search_results.json.")
    else:
        print(f"No papers found for keyword '{keyword}'.")
