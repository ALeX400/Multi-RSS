import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import random

user_agents = [
    # Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    # Firefox
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
    # Edge
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.100.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.100.0',
    # Opera
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.90',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.90',
]

def get_random_headers():
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'
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

def remove_links_containing_text(soup, texts):
    if isinstance(texts, str):
        texts = [texts]
    texts = [text.lower() for text in texts]
    for a in soup.find_all('a'):
        if a.text.strip().lower() in texts:
            a.decompose()

def remove_unwanted_phrases(soup):
    for p in soup.find_all('p'):
        if any(phrase.search(p.text) if isinstance(phrase, re.Pattern) else phrase in p.text for phrase in unwanted_phrases):
            p.decompose()

def remove_unwanted_scripts(soup):
    for script in soup.find_all('script'):
        script.decompose()

def remove_unwanted_elements(soup):
    for class_name in unwanted_classes:
        for element in soup.find_all('div', class_=class_name):
            element.decompose()
    for element in soup.select('.entry-meta, .cat-links, span#tbmarker'):
        element.decompose()
    for footer in soup.find_all('footer'):
        footer.decompose()
    for ins in soup.find_all('ins'):
        ins.decompose()

def fix_iframe_src(iframe):
    if 'src' in iframe.attrs and iframe['src'] == 'about:blank':
        if 'data-litespeed-src' in iframe.attrs:
            iframe['src'] = iframe['data-litespeed-src']
            del iframe['data-litespeed-src']

def replace_figures_with_iframes(soup):
    for figure in soup.find_all('figure'):
        iframes = figure.find_all('iframe')
        if iframes:
            for iframe in iframes:
                fix_iframe_src(iframe)
                figure.replace_with(iframe)
        else:
            blockquotes = figure.find_all('blockquote', class_='twitter-tweet')
            if blockquotes:
                for blockquote in blockquotes:
                    figure.replace_with(blockquote)
                script_html = '<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
                script_soup = BeautifulSoup(script_html, 'html.parser')
                for blockquote in blockquotes:
                    blockquote.insert_after(script_soup)

def remove_links(soup, ignore_elements):
    ignore_elements_set = set(ignore_elements)
    
    def should_ignore(tag):
        return tag.name in ignore_elements_set or any(parent.name in ignore_elements_set for parent in tag.parents)
    
    for tag in soup.find_all(True):
        if should_ignore(tag):
            continue
        else:
            for attribute in ['href', 'src', 'data-litespeed-src', 'url']:
                if attribute in tag.attrs:
                    del tag.attrs[attribute]

def fetch_article_content(article_url):
    try:
        response = requests.get(article_url, headers=get_random_headers())
        response.raise_for_status()
    except requests.exceptions.SSLError as e:
        print(f"SSL error {e} for {article_url}")
        return None
    except requests.RequestException as e:
        print(f"Failed to fetch article content from {article_url}: {e}")
        return None
    
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        article_element = soup.find('article', id=re.compile(r'post-\d+'))
        if not article_element:
            return "Article content not found."

        remove_unwanted_scripts(article_element)
        remove_unwanted_phrases(article_element)
        remove_unwanted_elements(article_element)
        replace_figures_with_iframes(article_element)
        remove_links(article_element, ['iframe', 'img', 'script', 'blockquote'])
        remove_links_containing_text(soup, ['SURSA', 'VIDEO'])

        # Extract image
        image_block = article_element.find('div', class_='entry-image')
        image_html = ""
        if image_block:
            img_tag = image_block.find('img')
            if img_tag:
                image_html = str(img_tag)

        final_content = f"{image_html}<br><br>{article_element.prettify().strip()}"
        final_content = final_content.replace('async=""', 'async')
        final_content = final_content.replace('— ', '&mdash;')
                
        return final_content
    except Exception as e:
        print(f"Error processing article content from {article_url}: {e}")
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

def extract_base_and_category(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    category = "/".join(path_parts) + '/'
    return base_url, category

def fetch_data(url):
    try:
        base_url, category = extract_base_and_category(url)
        # Format the URL to access the RSS feed
        rss_url = f"{base_url}category/{category}feed/"
        response = requests.get(rss_url, headers=get_random_headers())
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
                    print(f"Error processing article from {rss_url}: {e}")
        return articles_data
    except requests.RequestException as e:
        print(f"Failed to fetch articles from {rss_url}: {e}")
        return []