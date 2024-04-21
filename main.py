import importlib.util
import os
import json
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom
from tqdm import tqdm

def load_and_run_script(script_name, url):
    script_path = os.path.join(os.path.dirname(__file__), 'patterns', script_name)
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    if spec.loader is None:
        raise FileNotFoundError(f"Script {script_name} could not be loaded. Check if the file exists.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fetch_data(url)

def generate_xml(feed_items, file_name):
    root = Element('rss', version='2.0')
    channel = SubElement(root, 'channel')
    for item in feed_items:
        item_element = SubElement(channel, 'item')
        title = SubElement(item_element, 'title')
        title.text = item.get('title', 'No title')
        link = SubElement(item_element, 'link')
        link.text = item.get('link', '#')
        description = SubElement(item_element, 'description')
        description.text = item.get('description', 'No description')

    xml_str = xml.dom.minidom.parseString(tostring(root)).toprettyxml(indent="   ")
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(xml_str)

def main():
    with open('config.json', 'r') as file:
        config = json.load(file)

    output_dir = 'rss'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    patterns_dir = os.path.join(os.path.dirname(__file__), 'patterns')
    if not os.path.exists(patterns_dir):
        os.makedirs(patterns_dir)
        raise Exception("Patterns directory created. Please add pattern scripts and retry.")

    # Process groups with tqdm
    groups = config.get('Groups', {})
    for group_name, group_info in tqdm(groups.items(), desc='Processing groups', total=len(groups)):
        group_feed = []
        for url, script in zip(group_info['Urls'], group_info['Scripts']):
            articles_data = load_and_run_script(script, url)
            group_feed.extend(articles_data)
        file_name = os.path.join(output_dir, group_info.get('FileName') or f'{group_name}.xml')
        generate_xml(group_feed, file_name)

    # Process individual sites with tqdm
    sites = config.get('Sites', {})
    for site_name, site_info in tqdm(sites.items(), desc='Processing individual sites', total=len(sites)):
        articles_data = load_and_run_script(site_info['script'], site_info['url'])
        if articles_data:
            file_name = os.path.join(output_dir, site_info.get('FileName') or f'{site_name}.xml')
            generate_xml(articles_data, file_name)

if __name__ == "__main__":
    main()
