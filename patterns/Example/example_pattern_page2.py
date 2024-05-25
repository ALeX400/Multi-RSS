# Continut pentru pattern_page2.py si pattern_page3.py
import requests
from bs4 import BeautifulSoup

def fetch_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('article')
        
        articles_data = []
        for article in articles:
            title = article.find('h1').text.strip()
            description = article.find('p').text.strip()
            link = article.find('a')['href']
            
            articles_data.append({
                "title": title,
                "link": link,
                "description": description
            })
        
        return articles_data
    else:
        return []
