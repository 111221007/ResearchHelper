import requests
from bs4 import BeautifulSoup
import time
import urllib.parse


def scrape_ieee(query, max_pages=50):
    """
    Scrape IEEE Xplore search results pages for given query.
    """
    base_url = "https://ieeexplore.ieee.org/search/searchresult.jsp"
    papers = []
    for page in range(1, max_pages + 1):
        # Construct query URL with pagination
        params = {
            "newsearch": "true",
            "queryText": query,
            "pageNumber": page
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        # Each result item has class "List-results-items"
        for item in soup.select(".List-results-items .List-results-item"):
            title_tag = item.select_one(".result-item-title a")
            title = title_tag.get_text(strip=True)
            link = "https://ieeexplore.ieee.org" + title_tag["href"]
            # Access details page to find PDF link
            detail = requests.get(link)
            dsoup = BeautifulSoup(detail.text, "html.parser")
            pdf_tag = dsoup.select_one("a.icon-pdf")
            pdf_link = pdf_tag["href"] if pdf_tag else None
            venue = dsoup.select_one(".Stats-document-venue").get_text(strip=True) if dsoup.select_one(
                ".Stats-document-venue") else ""
            year = dsoup.select_one(".u-pb-1 span:nth-of-type(2)").get_text(strip=True) if dsoup.select_one(
                ".u-pb-1 span:nth-of-type(2)") else ""
            papers.append({
                "title": title,
                "venue": venue,
                "year": year,
                "pdf_link": pdf_link
            })
            time.sleep(1)  # polite delay
        time.sleep(2)
    return papers


def scrape_arxiv(query, max_pages=50):
    """
    Scrape arXiv search results for given query without API.
    """
    base_url = "https://arxiv.org/search/"
    papers = []
    for page in range(max_pages):
        params = {
            "query": query,
            "searchtype": "all",
            "abstracts": "show",
            "order": "-announced_date_first",
            "size": 50,
            "start": page * 50
        }
        r = requests.get(base_url, params=params)
        soup = BeautifulSoup(r.text, "html.parser")
        for result in soup.select(".arxiv-result"):
            title = result.select_one(".title").get_text(strip=True)
            authors = result.select_one(".authors").get_text(strip=True).replace("Authors:", "").strip()
            year_elem = result.select_one(".submitted-date")
            if year_elem:
                year = year_elem.get_text(strip=True).split(";")[0].replace("Submitted ", "")
            else:
                year = "Unknown"
            pdf_tag = result.select_one("p.list-title a[title='Download PDF']")
            pdf_link = pdf_tag["href"] if pdf_tag else None
            papers.append({
                "title": title,
                "authors": authors,
                "year": year,
                "pdf_link": f"https://arxiv.org{pdf_link}" if pdf_link else None
            })
        time.sleep(2)
    return papers


def main():
    query = "serverless computing benchmarking"
    ieee_papers = scrape_ieee(query, max_pages=2)
    arxiv_papers = scrape_arxiv(query, max_pages=2)

    # Combine and dedupe by title
    all_papers = ieee_papers + arxiv_papers
    unique = {p["title"]: p for p in all_papers}

    # Display results
    for idx, paper in enumerate(unique.values(), 1):
        print(f"{idx}. {paper['title']} ({paper.get('year', '')})")
        print(f"   Venue: {paper.get('venue', 'arXiv')}")
        print(f"   PDF: {paper['pdf_link']}\n")


if __name__ == "__main__":
    main()
