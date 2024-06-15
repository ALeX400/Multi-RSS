import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import xml.etree.ElementTree as ET
import re

BASE_URL = "https://store.steampowered.com/feeds/news/app/"

def generate_embed(app_id):
    return f"""
    <iframe frameborder="0" height="200" src="https://store.steampowered.com/widget/{app_id}/" width="850"></iframe>
    """

def clean_article_content(content, app_ids):
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove href from <a> tags that do not contain images
    for a_tag in soup.find_all('a'):
        if not a_tag.find('img'):
            a_tag.unwrap()
    
    # Detect and transform plain text URLs into embeds if they match app_ids
    app_id_pattern = re.compile(r"https://store.steampowered.com/app/(\d+)(?:/[^/\s]*)?/")
    for text in soup.find_all(text=True):
        match = app_id_pattern.search(text)
        if match and int(match.group(1)) in app_ids:
            app_id = match.group(1)
            embed_html = generate_embed(app_id)
            new_content = text.replace(match.group(0), embed_html)
            new_soup = BeautifulSoup(new_content, 'html.parser')
            text.replace_with(new_soup)
    
    # Detect and transform YouTube video divs into iframe embeds
    for div in soup.find_all('div', class_='sharedFilePreviewYouTubeVideo'):
        youtube_id = div.get('data-youtube')
        if youtube_id:
            youtube_iframe = f"""
            <iframe allowfullscreen="1" frameborder="0" height="500" src="https://www.youtube.com/embed/{youtube_id}?fs=1&amp;modestbranding=1&amp;rel=0" width="850"></iframe>
            """
            new_soup = BeautifulSoup(youtube_iframe, 'html.parser')
            div.replace_with(new_soup)
            
     # Add custom styles
    custom_styles = """
    <style>
        [data-focus-scheme="dark"] {
            color-scheme: none;
        }
    </style>
    """
    
    # Insert custom styles at the beginning of the content
    soup.insert(0, BeautifulSoup(custom_styles, 'html.parser'))

    return str(soup)

def fetch_article_data(item, app_ids):
    try:
        title = item.find('title').text
        link = item.find('link').text.strip()
        pub_date = item.find('pubDate').text
        description = clean_article_content(item.find('description').text, app_ids)

        return {
            "title": title,
            "link": link,
            "description": description,
            "pubDate": pub_date
        }
    except Exception as e:
        print(f"Failed to fetch article data: {e}")
        return None

def fetch_data(app_id, app_ids):
    url = f"{BASE_URL}{app_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')

        items = soup.find_all('item')
        articles_data = []
        
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(fetch_article_data, item, app_ids): item for item in items}
            for future in as_completed(futures):
                try:
                    article_data = future.result()
                    if article_data:
                        articles_data.append(article_data)
                except Exception as e:
                    print(f"Error processing article from {url}: {e}")
        return articles_data
    except requests.RequestException as e:
        print(f"Failed to fetch articles from {url}: {e}")
        return []

def fetch_data_with_id(app_ids):
    all_articles = []
    
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_data, app_id, app_ids): app_id for app_id in app_ids}
        for future in as_completed(futures):
            try:
                articles = future.result()
                if articles:
                    all_articles.extend(articles)
            except Exception as e:
                print(f"Error fetching data for app ID: {futures[future]}: {e}")
    
    # Sort all articles by pubDate and get the 5 most recent ones
    all_articles_sorted = sorted(all_articles, key=lambda x: datetime.strptime(x['pubDate'], '%a, %d %b %Y %H:%M:%S %z'), reverse=True)
    return all_articles_sorted[:5]