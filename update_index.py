import os
from datetime import datetime
import urllib.parse

def update_index():
    rss_dir = 'rss'
    
    # Ensure the directory exists
    if not os.path.exists(rss_dir):
        print(f"Directory '{rss_dir}' does not exist.")
        return

    index_path = os.path.join(rss_dir, 'index.md')

    # Delete the existing index.md file if it exists
    if os.path.exists(index_path):
        os.remove(index_path)
        print(f"Existing '{index_path}' deleted.")

    # Traverse directory to find all XML files
    files = []
    for root, dirs, filenames in os.walk(rss_dir):
        for filename in filenames:
            if filename.endswith('.xml'):
                # Get the relative path to the file from rss_dir
                relative_path = os.path.relpath(os.path.join(root, filename), rss_dir)
                files.append(relative_path)

    with open(index_path, 'w') as index_file:
        # Write the header and description
        index_file.write('# XML Files Index\n')
        index_file.write('**This index was automatically generated to list all XML files in the `rss` directory and its subdirectories.**\n\n')
        index_file.write(f'**Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}**\n\n')
        
        # Write the table header
        index_file.write('| File Name | Link |\n')
        index_file.write('|-----------|------|\n')
        
        # Write each file as a row in the table
        for file in files:
            encoded_file = urllib.parse.quote(file)
            index_file.write(f'| {file} | [Link to {file}](./{encoded_file}) |\n')

    print(f"Index updated with {len(files)} files.")

if __name__ == "__main__":
    update_index()
