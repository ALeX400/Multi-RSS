import os
import json
from datetime import datetime

def update_index():
    rss_dir = 'rss'
    
    # Ensure the directory exists
    if not os.path.exists(rss_dir):
        print(f"Directory '{rss_dir}' does not exist.")
        return

    cache_path = 'file_cache.json'  # This will save file_cache.json in the root directory

    # Traverse directory to find all XML files
    files = []
    for root, dirs, filenames in os.walk(rss_dir):
        for filename in filenames:
            if filename.endswith('.xml'):
                # Get the relative path to the file from rss_dir
                relative_path = os.path.relpath(os.path.join(root, filename), rss_dir)
                files.append(relative_path)

    # Create the JSON object
    file_cache = {
        "last_updated": datetime.now().strftime("%d.%m.%Y %I:%M %p"),
        "files": files
    }

    # Write the JSON object to file
    with open(cache_path, 'w') as cache_file:
        json.dump(file_cache, cache_file, indent=4)

    print(f"File cache updated with {len(files)} files.")

if __name__ == "__main__":
    update_index()
