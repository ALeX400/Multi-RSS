import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def clean_article_content(soup):
    # Remove specific elements
    for div_class in ['author', 'news-section-media', 'likes']:
        for div in soup.find_all('div', class_=div_class):
            div.decompose()
    
    # Remove href from <a> tags within <div class="section-header">
    for section_header in soup.find_all('div', class_='section-header'):
        for a_tag in section_header.find_all('a', href=True):
            a_tag.attrs.pop('href', None)
            a_tag['style'] = 'text-decoration: none;'

    # Add custom CSS
    custom_css = '''
    <style>
        .blog .news-section-block.sectionstyle-hero .content {
            background-color: inherit;
            padding: 2rem;
        }
        div.blog .section {
            padding: 16px;
            margin-bottom: 1rem;
            max-width: 800px;
            margin: auto;
        }
        .blog-hero {
            background-color: inherit;
            padding: calc(8rem + 100px) 0 8rem 0;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            min-height: 50vh;
        }
        .change-blog-container {
            background-color: inherit;
            width: 100%;
        }
        h1,h2,h3,h4,h5 {
            font-family: inherit;
            font-weight: inherit;
            color: inherit;
        }
        .body-info h1,.body-info h2,.body-info h3,.body-info h4,.body-info h5 {
            font-family: "Bebas Neue", sans-serif;
            font-weight: 500;
            color: #e4dad1;
        }
        .sectionstyle-hero {
            min-height: 0;
        }
    </style>
    '''

    # Prepare final content
    final_content = custom_css
    final_content += str(soup)

    return final_content

def fetch_article_data(article_url):
    try:
        response = requests.get(article_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract <div class="blog-hero">
        blog_hero = soup.find('div', class_='blog-hero')
        if blog_hero:
            blog_hero_image = blog_hero.find('div', class_='blog-hero-image')
            if blog_hero_image:
                blog_hero_image.decompose()
            blog_hero_content = str(blog_hero)
            blog_hero.decompose()
        else:
            blog_hero_content = ''
        
        # Extract and clean content
        content_block = soup.find('div', class_='blog')
        if content_block:
            cleaned_content = clean_article_content(content_block)
            final_content = '<link href="https://rust.facepunch.com/styles.min.css" rel="stylesheet">'
            final_content += blog_hero_content
            final_content += cleaned_content
            final_content += '<center>'
            
            # Use prettify() for better readability
            soup = BeautifulSoup(final_content, 'html.parser')
            soup = soup.prettify().strip()
            content = str(soup)
            content += '<center>'
            return content
        else:
            return "Content block not found."
    except requests.RequestException as e:
        print(f"Failed to fetch article data from {article_url}: {e}")
        return None

def scrape_rust_facepunch_articles(url):
    try:
        rss_url = url.replace('news/', 'rss/news/')
        response = requests.get(rss_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        
        items = soup.find_all('item')
        if not items:
            print(f"No articles found at {rss_url}")
            return []

        articles_data = []
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(fetch_article_data, item.find('link').text): item
                for item in items[:5]
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    title = item.find('title').text
                    link = item.find('link').text
                    pub_date = item.find('pubDate').text if item.find('pubDate') else ''
                    description = future.result()
                    if description:
                        articles_data.append({
                            "title": title,
                            "link": link,
                            "description": description,
                            "pubDate": pub_date
                        })
                except Exception as e:
                    print(f"Error processing article from {rss_url}: {e}")
        return articles_data
    except requests.RequestException as e:
        print(f"Failed to fetch articles from {rss_url}: {e}")
        return []

def fetch_data(url):
    return scrape_rust_facepunch_articles(url)
