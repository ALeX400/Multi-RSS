import os


def update_index():
    rss_dir = 'rss'
    files = [f for f in os.listdir(rss_dir) if f.endswith('.xml')]
    index_path = os.path.join(rss_dir, 'index.md')

    with open(index_path, 'w') as index_file:
        index_file.write('# List of XML files in this directory\n\n')
        for file in files:
            index_file.write(f'- [Link to {file}](./{file})\n')


if __name__ == "__main__":
    update_index()
