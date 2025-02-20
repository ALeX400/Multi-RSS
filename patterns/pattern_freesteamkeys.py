import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

REMOVE_SELECTORS = [
    'div.cat-links', 'div.post-meta-info'
]

def extract_article_header(soup):
    title_element = soup.find('h1', class_='entry-title')
    title = title_element.text.strip() if title_element else "No Title"

    img_element = soup.select_one('.post-thumbnail img')
    img_url = img_element['src'] if img_element else ""

    giveaway_button = soup.select_one('.item-url.custom_link_button')
    giveaway_onclick = giveaway_button['onclick'] if giveaway_button else ""

    return f"""
    <div class="custom-header">
        <div class="custom-header-content">
            <div class="custom-title">{title}</div>
            <div class="custom-thumbnail">
                <img src="{img_url}" alt="{title}">
            </div>
        </div>
        <div class="custom-header-button">
            <button class="custom-button" onclick="{giveaway_onclick}">Open Giveaway</button>
        </div>
    </div>
    """

#def clean_article_content(soup):
#    for selector in REMOVE_SELECTORS:
#        for elem in soup.select(selector):
#            elem.decompose()

#    for picture in soup.find_all('picture'):
#        img_tag = picture.find('img')
#        if img_tag:
#            picture.replace_with(img_tag)

#    for a_tag in soup.find_all('a'):
#        if not a_tag.find('img') and not a_tag.find('iframe'):
#            a_tag.unwrap()

#    return str(soup)

def clean_article_content(soup):
    for selector in REMOVE_SELECTORS:
        for elem in soup.select(selector):
            elem.decompose()

    for picture in soup.find_all('picture'):
        img_tag = picture.find('img')
        if img_tag:
            picture.replace_with(img_tag)

    for a_tag in soup.find_all('a'):
        href = a_tag.get('href', '')

        if not href.startswith("https://store.steampowered.com"):
            if not a_tag.find('img') and not a_tag.find('iframe'):
                a_tag.unwrap()

    return str(soup)


def fetch_article_content(article_url):
    try:
        response = requests.get(article_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        article_header = extract_article_header(soup)

        article_content = soup.find('div', class_='zf_description')

        article_content = clean_article_content(article_content) if article_content else "No content found."

        styles = """<link href="http://localhost/Styles-Rss/freesteamkeys.css" rel="stylesheet">"""
        final_content = f"{styles}{article_header}{article_content}"
        return final_content.strip()
    except requests.RequestException as e:
        print(f"Failed to fetch article content from {article_url}: {e}")
        return None

def fetch_article_data(item):
    try:
        title = item.find('title').text.strip()
        link = item.find('link').text.strip()
        pub_date = item.find('pubDate').text.strip()
        description = fetch_article_content(link)

        return {
            "title": title,
            "link": link,
            "description": description,
            "pubDate": pub_date
        }
    except Exception as e:
        print(f"Failed to fetch article data: {e}")
        return None

def fetch_data(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')

        items = soup.find_all('item')[:5]
        articles_data = []
        
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(fetch_article_data, item): item for item in items}
            for future in as_completed(futures):
                article_data = future.result()
                if article_data:
                    articles_data.append(article_data)

        return articles_data
    except requests.RequestException as e:
        print(f"Failed to fetch articles from {url}: {e}")
        return []
