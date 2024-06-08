import requests
from bs4 import BeautifulSoup
import re
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

def clean_content(content, image_url):
    # Parse the content with BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')

    # Add the image at the beginning of the content
    if image_url:
        img_tag = soup.new_tag('img', src=image_url)
        br_tag = soup.new_tag('br')
        soup.insert(0, br_tag)
        soup.insert(0, img_tag)

    # Remove <a> tags but keep their content
    for a_tag in soup.find_all('a'):
        a_tag.replace_with(a_tag.text)

    # Remove <strong> tags but keep their content
    for strong_tag in soup.find_all('strong'):
        strong_tag.unwrap()

    # Remove unwanted <p> tags that contain specific phrases
    for p_tag in soup.find_all('p'):
        if 'appeared first on' in p_tag.text or 'The post' in p_tag.text:
            p_tag.decompose()

    # Remove inline styles from <span> tags
    for span in soup.find_all('span'):
        if 'style' in span.attrs:
            del span['style']

    return str(soup)

def fetch_article_data(item):
    try:
        title = item.find('title').text
        link = item.find('link').text
        description = item.find('{http://purl.org/rss/1.0/modules/content/}encoded').text

        # Get the image URL from the <enclosure> element
        enclosure = item.find('enclosure')
        image_url = enclosure.get('url') if enclosure is not None else None
        
        print(image_url)

        description = clean_content(description, image_url)

        return {
            "title": title,
            "link": link,
            "description": description
        }
    except Exception as e:
        print(f"Failed to fetch article data: {e}")
        return None

def scrape_prosport_articles(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item')

        if not items:
            print(f"No articles found at {url}")
            return []

        articles_data = []
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(fetch_article_data, item): item for item in items[:5]}
            for future in as_completed(futures):
                item = futures[future]
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
    except ET.ParseError as e:
        print(f"Failed to parse XML from {url}: {e}")
        return []

def fetch_data(url):
    return scrape_prosport_articles(url)
