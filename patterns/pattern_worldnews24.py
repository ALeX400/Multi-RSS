import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

unwanted_phrases = [
    re.compile(r"În lipsa unui acord scris, puteți prelua maxim \d+ de caractere din acest articol dacă precizați sursa și dacă inserați vizibil linkul articolului."),
    "Pentru mai multe articole interesante rămâi cu noi pe",
    "VIDEO"
]

unwanted_classes = [
    "addtoany_share_save_container",
    "code-block"
]

def remove_unwanted_phrases(soup):
    for p in soup.find_all('p'):
        if any(phrase.search(p.text) if isinstance(phrase, re.Pattern) else phrase in p.text for phrase in unwanted_phrases):
            p.decompose()

def remove_unwanted_scripts(soup):
    for script in soup.find_all('script'):
        script.decompose()

def remove_unwanted_divs(soup):
    for div in soup.find_all('div', class_=re.compile('|'.join(unwanted_classes))):
        div.decompose()

def remove_video_block(soup):
    for figure in soup.find_all('figure', class_=re.compile('wp-block-embed is-type-video')):
        figure.decompose()

def fetch_article_data(article_url):
    try:
        with requests.get(article_url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            remove_unwanted_phrases(soup)
            remove_unwanted_scripts(soup)
            remove_unwanted_divs(soup)
            remove_video_block(soup)

            content_block = soup.find('div', class_='entry-content')
            image_block = soup.find('div', class_='entry-image')
            image_html = ""
            if image_block:
                img_tag = image_block.find('img')
                if img_tag:
                    image_html = str(img_tag)

            if content_block:
                final_content = f"{image_html}<br><br>{content_block.prettify().strip()}"
                return final_content
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
