import requests
from bs4 import BeautifulSoup
import re

# Standard headers for requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def fetch_article_data(article_url):
    """
    Fetches the content of an article given its URL.

    Args:
        article_url (str): URL of the article to fetch.

    Returns:
        str: HTML content of the article, or an error message.
    """
    try:
        response = requests.get(article_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup.prettify().strip()
        else:
            print(f"Failed to retrieve content from {article_url}. HTTP status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error retrieving content from {article_url}: {str(e)}")
        return None

def scrape_articles(url):
    """
    Scrapes articles from a given URL and fetches their content.

    Args:
        url (str): URL of the page to scrape articles from.

    Returns:
        list: A list of dictionaries containing article titles, links, and descriptions.
    """
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Adjust the selector according to the website's structure
            articles = soup.select('.article-selector')
            if not articles:
                print(f"No articles found at {url}.")
                return []
            
            articles_data = []
            for index, article in enumerate(articles[:5]):
                print(f'Processing article {index + 1}/{len(articles[:5])}')
                title_element = article.select_one('.title-selector')
                if not title_element:
                    continue

                title = title_element.text.strip()
                link = 'https://example.com' + title_element['href']
                description = fetch_article_data(link)

                articles_data.append({
                    "title": title,
                    "link": link,
                    "description": description
                })

            return articles_data
        else:
            print(f"Failed to retrieve articles from {url}. HTTP status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error scraping articles from {url}: {str(e)}")
        return []

def fetch_data(url):
    """
    Fetches data from the given URL by scraping articles.

    Args:
        url (str): URL to scrape data from.

    Returns:
        list: A list of scraped articles.
    """
    return scrape_articles(url)

# Example usage
if __name__ == "__main__":
    url = 'https://example.com/articles'
    articles = fetch_data(url)
    for article in articles:
        print(f"Title: {article['title']}\nLink: {article['link']}\nDescription: {article['description']}\n")
