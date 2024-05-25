import os
from datetime import datetime

def update_index():
    rss_dir = 'rss'
    files = [f for f in os.listdir(rss_dir) if f.endswith('.xml')]
    index_path = os.path.join(rss_dir, 'index.md')

    with open(index_path, 'w') as index_file:
        # Write the header and description
        index_file.write('# XML Files Index\n')
        index_file.write('This index was automatically generated to list all XML files in the `rss` directory.\n\n')
        index_file.write(f'_Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}_\n\n')
        
        # Write the table header
        index_file.write('| File Name | Link |\n')
        index_file.write('|-----------|------|\n')
        
        # Write each file as a row in the table
        for file in files:
            index_file.write(f'| {file} | [Link to {file}](./{file}) |\n')

if __name__ == "__main__":
    update_index()
