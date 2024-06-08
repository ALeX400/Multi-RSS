import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

unwanted_phrases = [
    "În lipsa unui acord scris, puteți prelua maxim 250 de caractere din acest articol dacă precizați sursa și dacă inserați vizibil linkul articolului.",
    "Pentru mai multe articole interesante rămâi cu noi pe"
]

unwanted_classes = [
    "addtoany_share_save_container",
    "code-block"
]

def fetch_article_data(article_url):
    try:
        with requests.get(article_url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted phrases in <p> tags
            for p in soup.find_all('p'):
                if any(phrase in p.text for phrase in unwanted_phrases):
                    p.decompose()

            # Remove <script> tags
            for script in soup.find_all('script'):
                script.decompose()

            # Remove <div> tags with unwanted classes
            for div in soup.find_all('div', class_=re.compile('|'.join(unwanted_classes))):
                div.decompose()

            content_block = soup.find('div', class_='entry-content')
            if content_block:
                return content_block.prettify().strip()
            else:
                return "Content block not found."
    except requests.RequestException as e:
        print(f"Failed to fetch article data from {article_url}: {e}")
        return None

def scrape_worldnews24_articles(url):
    try:
        with requests.get(url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            articles = soup.select('.magxpress-article-wrapper article')
            if not articles:
                print(f"No articles found at {url}")
                return []

            articles_data = []
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(fetch_article_data, article.select_one('.entry-header .entry-title a')['href']): article for article in articles[:5] if article.select_one('.entry-header .entry-title a')}
                for future in as_completed(futures):
                    article = futures[future]
                    try:
                        title_element = article.select_one('.entry-header .entry-title a')
                        title = title_element.text.strip()
                        link = title_element['href']
                        description = future.result()
                        if description:
                            articles_data.append({
                                "title": title,
                                "link": link,
                                "description": description
                            })
                    except Exception as e:
                        print(f"Error processing article from {url}: {e}")
            return articles_data
    except requests.RequestException as e:
        print(f"Failed to fetch articles from {url}: {e}")
        return []

def fetch_data(url):
    return scrape_worldnews24_articles(url)
