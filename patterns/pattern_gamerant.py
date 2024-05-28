import requests
from bs4 import BeautifulSoup
import re
import json
import os
import sys

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}


def get_site_name_by_script():
    with open('config.json', 'r') as file:
        config = json.load(file)
    
    sites = config.get('Sites', {})
    for site_name, site_info in sites.items():
        if site_info.get('script') == os.path.basename(__file__):
            return site_name
    return None

site_name = get_site_name_by_script()

def fetch_article_data(article_url):
    try:
        response = requests.get(article_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

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
                html_string = re.sub(r'\s+', ' ', str(content_block))
                clean_soup = BeautifulSoup(html_string, 'html.parser')
                prettified_html = clean_soup.prettify()
                return prettified_html.strip()
            else:
                return "Content block not found."
        else:
            return None
    except Exception as e:
        return None

def scrape_gamerant_articles(url):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            articles = soup.select('.sentinel-listing-page-list .display-card.article.small')
            if not articles:
                return []

            articles_data = []

            for article in articles[:5]:
                title_element = article.select_one('.display-card-title a')
                if not title_element:
                    continue

                title = title_element.text.strip()
                link = 'https://gamerant.com' + title_element['href']
                description = fetch_article_data(link)

                articles_data.append({
                    "title": title,
                    "link": link,
                    "description": description
                })
            return articles_data
        else:
            return []
    except Exception as e:
        return []


def fetch_data(url):
    return scrape_gamerant_articles(url)
