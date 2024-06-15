import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def load_styles():
    try:
        with open('assets/adevarul.ro.min.css', 'r') as file:
            styles = file.read()
        return f"<style>{styles}</style>"
    except Exception as e:
        print(f"Failed to load styles: {e}")
        return ""

def clean_article_content(soup):
    # Remove specific elements
    for selector in ['.info.svelte-hvtg27', '.date.metaFont.svelte-hvtg27', '.read-more-item', 'footer', 'nav', 'script', 'div[class^="google-adposition"]']:
        for elem in soup.select(selector):
            elem.decompose()
    
    # Replace <picture> elements with <img> tags
    for picture in soup.find_all('picture'):
        img_tag = picture.find('img')
        if img_tag:
            picture.replace_with(img_tag)

    # Remove href from <a> tags that do not contain images or iframes
    for a_tag in soup.find_all('a'):
        if not a_tag.find('img') and not a_tag.find('iframe'):
            a_tag.unwrap()

    # Process and clean titles
    for title_div in soup.select('header[class^="svelte-hvtg27"]'):
        h1_tag = title_div.find('h1')
        if h1_tag:
            h1_tag_text = h1_tag.get_text().replace('VIDEO', '').replace('Video', '').strip()
            h1_tag.string = h1_tag_text
            title_div.replace_with(h1_tag)
    
    return str(soup)

def fetch_article_content(article_url):
    try:
        response = requests.get(article_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract article content
        article_content = soup.find('article')
        if article_content:
            cleaned_content = clean_article_content(article_content)
            # Add custom styles
            #style = load_styles()
            style = """<link href="https://alex400.github.io/Multi-RSS/assets/adevarul.ro.css" rel="stylesheet">"""
            
            cleaned_content = f"{style}{cleaned_content}<center>"
            return cleaned_content.strip()
        else:
            return "Article content not found."
    except requests.RequestException as e:
        print(f"Failed to fetch article content from {article_url}: {e}")
        return None

def fetch_article_data(item):
    try:
        title = item.find('title').text.replace('VIDEO', '').replace('Video', '').strip()
        link = item.find('link').text.strip()
        pub_date = item.find('pubDate').text
    
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

        items = soup.find_all('item')
        articles_data = []
        
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(fetch_article_data, item): item for item in items[:5]}
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
