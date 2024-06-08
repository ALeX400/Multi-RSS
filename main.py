import importlib.util
import os
import json5
from lxml import etree
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

def load_and_run_script(script_name, url):
    script_path = os.path.join(os.path.dirname(__file__), 'patterns', script_name)
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    if spec.loader is None:
        raise FileNotFoundError(f"Script {script_name} could not be loaded. Check if the file exists.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = module.fetch_data(url)
    return data

def clean_xml(xml_str):
    xml_str = re.sub(r'<!--.*?-->', '', xml_str, flags=re.DOTALL)
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_str, parser)
    for element in root.xpath(".//script"):
        element.getparent().remove(element)
    for element in root.xpath(".//spoiler"):
        element.getparent().remove(element)
    return etree.tostring(root, pretty_print=True, encoding='UTF-8')

def generate_xml(feed_items, file_name):
    root = etree.Element('rss', version="2.0", nsmap={'atom': "http://www.w3.org/2005/Atom", 'content': "http://purl.org/rss/1.0/modules/content/"})
    channel = etree.SubElement(root, 'channel')
    for item in feed_items:
        item_element = etree.SubElement(channel, 'item')
        title = etree.SubElement(item_element, 'title')
        title.text = item.get('title', 'No title')
        link = etree.SubElement(item_element, 'link')
        link.text = item.get('link', '#')
        description = etree.SubElement(item_element, 'description')
        description.text = etree.CDATA(item.get('description', 'No description'))
    xml_bytes = etree.tostring(root, pretty_print=True, encoding='UTF-8')
    with open(file_name, 'wb') as file:
        file.write(xml_bytes)

def print_progress_bar(iteration, total, length=50):
    if iteration == 2:
        print()
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = '#' * filled_length + '-' * (length - filled_length)
    print(f'\rProgress: |{bar}| {percent}% Complete')
    #if iteration == total:
        #print()

def process_site(site_name, site_info):
    print(f"Processing site: '{site_name}'")
    try:
        base_url = site_info['url']
        categories = site_info.get('category', [])
        script = site_info['script']
        all_articles_data = []
        if categories:
            site_dir = os.path.join('rss', site_name)
            if not os.path.exists(site_dir):
                os.makedirs(site_dir)
            total_categories = len(categories)
            current_category = 0
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(load_and_run_script, script, os.path.join(base_url, category)): category for category in categories}
                for future in as_completed(futures):
                    category = futures[future]
                    try:
                        articles_data = future.result()
                        if articles_data:
                            category_dir = os.path.join(site_dir, category)
                            if not os.path.exists(category_dir):
                                os.makedirs(category_dir)
                            category_file_name = os.path.join(category_dir, f"{category}.xml")
                            generate_xml(articles_data, category_file_name)
                            all_articles_data.extend(articles_data)
                    except Exception as e:
                        print(f"Failed to process category {category} for site {site_name}: {e}")
                    #current_category += 1
            #if current_category > 0:
                #print_progress_bar(total_categories, total_categories)
            #print()  # Finalize category progress bar output
        else:
            articles_data = load_and_run_script(script, base_url)
            if articles_data:
                file_name = os.path.join('rss', f"{site_name}.xml")
                generate_xml(articles_data, file_name)
                all_articles_data.extend(articles_data)
        if all_articles_data:
            return site_name, True
        else:
            print(f"No data found for site '{site_name}'")
            return site_name, False
    except Exception as e:
        print(f"Failed to process site {site_name}: {e}")
        return site_name, False

def replace_dynamic_parameters(url):
    current_year = datetime.now().year
    url = url.replace("{year}", str(current_year))
    return url

def main():
    with open('config.json', 'r', encoding='utf-8') as file:
        config = json5.load(file)
    output_dir = 'rss'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    patterns_dir = os.path.join(os.path.dirname(__file__), 'patterns')
    if not os.path.exists(patterns_dir):
        os.makedirs(patterns_dir)
        raise Exception("Patterns directory created. Please add pattern scripts and retry.")
    groups = config.get('Groups', {})
    sites = config.get('Sites', {})
    total_tasks = len(groups) + len(sites)
    current_task = 0
    if groups:
        for group_index, (group_name, group_info) in enumerate(groups.items()):
            print(f'Processing group {group_index + 1}/{len(groups)}: {group_name}')
            group_feed = []
            with ThreadPoolExecutor() as executor:
                future_to_url = {executor.submit(load_and_run_script, script, url): (url, script) for url, script in zip(group_info['Urls'], group_info['Scripts'])}
                for future in as_completed(future_to_url):
                    url, script = future_to_url[future]
                    try:
                        articles_data = future.result()
                        group_feed.extend(articles_data)
                    except Exception as e:
                        print(f"Failed to process {url} with script {script}: {e}")
                        continue
            file_name = os.path.join(output_dir, group_info.get('FileName') or f'{group_name}.xml')
            generate_xml(group_feed, file_name)
            print(f"Finished processing group {group_name}\n")
            current_task += 1
            #print_progress_bar(current_task, total_tasks)
    success_count = 0
    with ThreadPoolExecutor() as executor:
        future_to_site = {executor.submit(process_site, site_name, site_info): (site_name, site_info) for site_name, site_info in sites.items()}
        for future in as_completed(future_to_site):
            site_name, site_info = future_to_site[future]
            try:
                site_name, success = future.result()
                if success:
                    success_count += 1
            except Exception as e:
                print(f"Failed to process site {site_name}: {e}")
            current_task += 1
            print_progress_bar(current_task, total_tasks)
    #print()  # Finalize site progress bar output
    print(f"\nFinished {success_count}/{len(sites)} successfully.")

if __name__ == "__main__":
    main()
