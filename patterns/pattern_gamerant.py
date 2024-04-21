import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import logging

# Setare pentru logare
logging.basicConfig(filename='error.log', level=logging.ERROR, format='%(asctime)s:%(levelname)s:%(message)s')

# Header standard pentru requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def fetch_article_data(article_url):
    try:
        response = requests.get(article_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Cleanup the HTML
            for div in soup.find_all("div", class_=re.compile(r'(ad-zone|w-rich|display-card.*tag|tag.*display-card|ad-odd)')):
                div.decompose()
            for script_tag in soup.find_all("script"):
                script_tag.decompose()
            for tag in soup.find_all(style=re.compile(r'padding-bottom')):
                del tag['style']
            for element in soup.find_all(class_=re.compile(r'(emaki-custom-block.*emaki-custom-expandable|emaki-custom-expandable.*emaki-custom-block)')):
                element.decompose()

            content_block = soup.find('div', class_='content-block-regular')
            if content_block:
                description = content_block.get_text(strip=True)
                html_string = re.sub(r'\s+', ' ', str(content_block))
                clean_soup = BeautifulSoup(html_string, 'html.parser')
                prettified_html = clean_soup.prettify()
                return prettified_html.strip(), description
            else:
                return "Content block not found."
        else:
            logging.error(f"Failed to retrieve content. HTTP status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error retrieving content: {str(e)}")
        return None

def scrape_gamerant_articles(url):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            articles = soup.select('.sentinel-listing-page-list .display-card.article.small')
            if not articles:
                logging.error("Article container not found or empty.")
                return []
            
            articles_data = []
            for article in tqdm(articles[:5], desc='Processing articles'):
                title_element = article.select_one('.display-card-title a')
                if not title_element:
                    continue

                title = title_element.text.strip()
                link = 'https://gamerant.com' + title_element['href']
                content, description = fetch_article_data(link)

                articles_data.append({
                    "title": title,
                    "link": link,
                    "content": content,
                    "description": description
                })

            return articles_data
        else:
            logging.error(f"Failed to fetch page, status code: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error during scraping: {str(e)}")
        return []

def fetch_data(url):
    return scrape_gamerant_articles(url)
