import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urlunparse

def remove_url_params(url):
    parsed_url = urlparse(url)
    clean_url = urlunparse(parsed_url._replace(query=""))
    return clean_url

def clean_urls_in_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Update all links (a tags)
    for a_tag in soup.find_all('a', href=True):
        a_tag['href'] = remove_url_params(a_tag['href'])
    
    # Update all image sources (img tags)
    for img_tag in soup.find_all('img', src=True):
        img_tag['src'] = remove_url_params(img_tag['src'])

    return str(soup)

def wrap_in_spoiler(content):
    return f"""
    <div class="ipsSpoiler_contents ipsClearfix">
        <div class="ipsSpoiler" data-ipsspoiler>
            <div class="ipsSpoiler_contents ipsClearfix">
                {content}
            </div>
        </div>
    </div>
    """

def format_system_requirements(soup):
    system_requirements_div = soup.find('div', class_='game_page_autocollapse sys_req')
    if not system_requirements_div:
        return "Cerințe de sistem indisponibile."

    os_mapping = {
        'win': 'Windows',
        'mac': 'MacOS',
        'linux': 'Linux'
    }

    os_contents = {}
    
    # =============
    # Format Tabs
    # =============
    if system_requirements_div.find('div', class_='sysreq_tabs'):
        tabs = system_requirements_div.find_all('div', class_='sysreq_tab')
        contents = system_requirements_div.find_all('div', class_='sysreq_content')
        for tab, content in zip(tabs, contents):
            os_type = tab.get('data-os', 'unknown').lower()
            os_name = os_mapping.get(os_type, os_type.capitalize())
            if os_name not in os_contents:
                os_contents[os_name] = ""
            
            full_req = content.find('div', class_='game_area_sys_req_full')
            if full_req:
                full_req_html = full_req.decode_contents()
                os_contents[os_name] += f"<div class='sys_req_full'>{full_req_html}</div>"
            
            note = content.find('div', class_='game_area_sys_req_note')
            if note:
                note_html = note.decode_contents()
                os_contents[os_name] += f"<div class='sys_req_note'>{note_html}</div>"
    # =============
    # Format Div without Tabs
    # =============
    else:
        contents = system_requirements_div.find_all('div', class_='game_area_sys_req')
        for content in contents:
            os_type = content.get('data-os', 'unknown').lower()
            os_name = os_mapping.get(os_type, os_type.capitalize())
            if os_name not in os_contents:
                os_contents[os_name] = ""
            
            full_req = content.find('div', class_='game_area_sys_req_full')
            if full_req:
                full_req_html = full_req.decode_contents()
                os_contents[os_name] += f"<div class='sys_req_full'>{full_req_html}</div>"
            
            note = content.find('div', class_='game_area_sys_req_note')
            if note:
                note_html = note.decode_contents()
                os_contents[os_name] += f"<div class='sys_req_note'>{note_html}</div>"
            
            left_col = content.find('div', class_='game_area_sys_req_leftCol')
            right_col = content.find('div', class_='game_area_sys_req_rightCol')
            
            if left_col:
                left_col_html = left_col.decode_contents()
                os_contents[os_name] += f"<div class='sys_req_left_col'>{left_col_html}</div>"
            
            if right_col:
                right_col_html = right_col.decode_contents()
                os_contents[os_name] += f"<div class='sys_req_right_col'>{right_col_html}</div>"

    if len(os_contents) == 1:
        os_name = next(iter(os_contents))
        os_content = os_contents[os_name]
        system_requirements_html = f"""
        <br><br><center><h2>System Requirements</h2></center>
        {wrap_in_spoiler(f"<center><h3>{os_name}</h3></center><div class='sys_req_container'>{os_content}</div>")}
        """
    else:
        system_requirements_html = "<br><br><center><h2>System Requirements</h2></center>"
        inner_content = ""
        for os_name, os_content in os_contents.items():
            inner_content += f"""
            <center><h3>{os_name}</h3></center>
            {wrap_in_spoiler(f"<div class='sys_req_container'>{os_content}</div>")}
            """
        system_requirements_html += wrap_in_spoiler(inner_content)

    return system_requirements_html

def extract_app_id(url):
    match = re.search(r'/app/(\d+)', url)
    return match.group(1) if match else None

def generate_embed(app_id):
    return f"""
    <iframe frameborder="0" height="200" src="https://store.steampowered.com/widget/{app_id}/" width="850"></iframe>
    """

def remove_hrefs_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for a_tag in soup.find_all('a', href=True):
        a_tag.attrs.pop('href', None)
    return str(soup)

def fetch_article_data(article_url):
    try:
        response = requests.get(article_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract app ID for embedding
            app_id = extract_app_id(article_url)
            embed_html = generate_embed(app_id) if app_id else ""
            
            # Extract description
            game_description_div = soup.find('div', id='game_area_description', class_='game_area_description')
            description_html = str(game_description_div) if game_description_div else "Descriere indisponibilă."

            # Set Steam Embed
            description_html = (f"<br><br>" + embed_html + f"<br><br>") + description_html

            # Extract content descriptors
            content_descriptors_div = soup.find('div', id='game_area_content_descriptors', class_='game_area_description')
            content_descriptors_html = str(content_descriptors_div) if content_descriptors_div else "Descrierea conținutului pentru adulți indisponibilă."

            # Extract system requirements
            system_requirements_html = format_system_requirements(soup)
            if system_requirements_html:
                system_requirements_html += "<br><br>"

            # Extract developer information
            genres_and_manufacturer_div = soup.find('div', id='genresAndManufacturer', class_='details_block')
            genres_and_manufacturer_html = str(genres_and_manufacturer_div) if genres_and_manufacturer_div else "Informații despre dezvoltator indisponibile."
            genres_and_manufacturer_html = remove_hrefs_from_html(genres_and_manufacturer_html)  # Remove hrefs from developer information
            
            # Combine all sections based on embed_position
            full_description_html = (
                f"{genres_and_manufacturer_html}"
                f"{description_html}"
                f"{content_descriptors_html}"
                f"{system_requirements_html}"
            )

            # Define the CSS styles to be included in <head>...</head>
            styles = set_style()

            # Clean up the HTML content and remove URL params
            full_description_html = re.sub(r'\s+', ' ', full_description_html)
            full_description_html = clean_urls_in_html(full_description_html)
            clean_soup = BeautifulSoup(full_description_html, 'html.parser')
            prettified_html = clean_soup.prettify()
            prettified_html += f"<center>"
            prettified_html = prettified_html.replace('<div data-ipsspoiler="">', '<div data-ipsspoiler>')
            prettified_html = prettified_html.replace("&amp;", "&")
            prettified_html = prettified_html.replace("&lt;", "<").replace("&gt;", ">")

            # Insert the styles at the beginning of the HTML content
            final_html = styles + prettified_html

            return final_html.strip()
        else:
            return "Unable to fetch data"
    except Exception as e:
        return f"An error occurred: {str(e)}"

def set_style():
    return f"""
            <style>
            .sys_req_container {{
                display: flex;
                flex-wrap: wrap;
                margin-bottom: 10px;
            }}
            .sys_req_left_col, .sys_req_right_col {{
                flex: 1;
                padding: 10px;
                box-sizing: border-box;
            }}
            .sys_req_left_col {{
                border-right: 1px solid #ccc;
            }}
            .sys_req_right_col {{
                border-left: 1px solid #ccc;
            }}
            .ipsQuote_citation, .ipsSpoiler_header {{
                display: flex;
                justify-content: center;
            }}
            .ipsSpoiler_header [data-action='toggleSpoiler'] {{
                margin-top: 1px;
            }}
            [dir='ltr'] .ipsQuote, [dir='ltr'] .ipsSpoiler, [dir='ltr'] .ipsStyle_spoiler {{
                border-width: 0 4px 0 4px;
            }}
            </style>
    """

def scrape_steam_popularnew_articles(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            articles = soup.select('.search_result_row')
            if not articles:
                return []

            articles_data = []

            for article in articles[:5]:  # limiting to first 5 articles for demonstration
                title_element = article.find('span', class_='title')
                link_element = article['href']

                if not title_element or not link_element:
                    continue

                title = title_element.text.strip()
                link = remove_url_params(link_element)
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
        print(f"An error occurred while scraping articles: {str(e)}")
        return []

def fetch_data(url):
    return scrape_steam_popularnew_articles(url)
