import importlib.util
import os
import json5
from lxml import etree
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


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
    """
    Clean the XML string by removing <script>, <spoiler> elements and comments.
    """
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

    # Convert bytes to string and replace indentation with tabs
    xml_str = xml_bytes.decode('UTF-8')
    xml_str = xml_str.replace('  ', '\t')

    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(xml_str)


def process_site(site_name, site_info):
    print(f"Processing site: '{site_name}'")
    try:
        articles_data = load_and_run_script(site_info['script'], site_info['url'])
        if articles_data:
            file_name = os.path.join('rss', site_info.get('FileName') or f'{site_name}.xml')
            generate_xml(articles_data, file_name)
            return site_name, True
        else:
            print(f"No data found for site '{site_name}'")
            return site_name, False
    except Exception as e:
        print(f"Failed to process site {site_name}: {e}")
        return site_name, False


def print_progress_bar(iteration, total, length=50):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = '#' * filled_length + '-' * (length - filled_length)
    print(f'\rProgress: |{bar}| {percent}% Complete', end='\r')
    if iteration == total:
        print()


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
            print(f"Finished processing group {group_name}")
            current_task += 1
            print_progress_bar(current_task, total_tasks)

    success_count = 0
    with ThreadPoolExecutor() as executor:
        future_to_site = {executor.submit(process_site, site_name, site_info): (site_name, site_info) for site_name, site_info in sites.items()}
        for future in as_completed(future_to_site):
            site_name, _ = future_to_site[future]
            try:
                site_name, success = future.result()
                if success:
                    success_count += 1
            except Exception as e:
                print(f"Failed to process site {site_name}: {e}")
            current_task += 1
            print_progress_bar(current_task, total_tasks)

    print(f"Finished {success_count}/{len(sites)} successfully.")


if __name__ == "__main__":
    main()
