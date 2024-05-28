import requests
from bs4 import BeautifulSoup, Comment
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def proxy_image_urls(soup):
    for img in soup.find_all('img'):
        img['src'] = f"https://image-proxy-beta.vercel.app/proxy?url={img['src']}"
    return soup

def remove_empty_elements(soup):
    for element in soup.find_all():
        if not element.get_text(strip=True) and not element.find_all():
            element.decompose()
    return soup

def fetch_article_data(article_url):
    try:
        response = requests.get(article_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements as specified
            unwanted_selectors = [
                "h1.post-title.entry-title",
                "div.author.vcard",
                "span.post-byline",
                "span.post-byline.updated",
                'ins.adsbygoogle',
                'script'
            ]
            for selector in unwanted_selectors:
                for element in soup.select(selector):
                    element.decompose()

            # Remove meta tags
            for meta in soup.find_all('meta'):
                meta.decompose()

            # Remove specific elements based on regex
            for element in soup.find_all(True, {"id": re.compile(r'^post-ratings-\d+')}):
                element.decompose()
            for element in soup.find_all(True, {"class": re.compile(r'post-ratings-text')}):
                element.decompose()

            # Remove "(No Ratings Yet)" text
            for text in soup.find_all(string=re.compile(r'\(No Ratings Yet\)')):
                text.extract()

            # Remove from "How to install ETS2 mods or ATS Mods" up to and including "Credits"
            install_instructions_start = soup.find('strong', text=re.compile(r'^\s*How to install ETS2 mods or ATS Mods\s*$', re.IGNORECASE))
            if install_instructions_start:
                for previous in list(install_instructions_start.previous_siblings):
                    if previous.name == 'strong' and re.match(r'^Credits$', previous.get_text(strip=True), re.IGNORECASE):
                        previous.extract()
                        break
                    previous.extract()
                install_instructions_start.insert_before(soup.new_string('<hr>'))

            credits_block = soup.find('strong', text=re.compile(r'^Credits$', re.IGNORECASE))
            if credits_block:
                credits_block.extract()

            # Proxy image URLs
            soup = proxy_image_urls(soup)

            # Remove empty elements
            soup = remove_empty_elements(soup)

            # Remove comments
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            for comment in comments:
                comment.extract()

            # Find download button outside the article
            download_button_html = ''
            download_button_div = soup.find('div', class_='download-button')
            if download_button_div:
                download_button = download_button_div.find('a', class_='dmod')
                if download_button:
                    download_button['style'] = 'background-color: green; color: white; padding: 10px; text-align: center; display: inline-block; text-decoration: none;'
                    download_button_html = str(download_button)

            content_block = soup.find('article')
            if content_block:
                html_string = re.sub(r'\s+', ' ', str(content_block))
                clean_soup = BeautifulSoup(html_string, 'html.parser')
                prettified_html = clean_soup.prettify()

                prettified_html += '<hr><br><br><br>'

                if download_button_html:
                    prettified_html += f'<center>{download_button_html}<center>'

                prettified_html = prettified_html.replace("&amp;", "&")
                prettified_html = prettified_html.replace("&lt;", "<").replace("&gt;", ">")

                return prettified_html.strip()
            else:
                return "Content block not found."
        else:
            return "Unable to fetch data"
    except Exception as e:
        return f"An error occurred: {str(e)}"

def scrape_ets2world_articles(url):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            articles = soup.select('.post-list.group .post-row article')
            if not articles:
                return []

            articles_data = []

            for article in articles[:5]:
                title_element = article.select_one('.post-title a')
                if not title_element:
                    continue

                title = title_element.text.strip()
                link = title_element['href']
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
    return scrape_ets2world_articles(url)
