import os
from datetime import datetime

def update_index():
    rss_dir = 'rss'
    files = [f for f in os.listdir(rss_dir) if f.endswith('.xml')]
    index_path = os.path.join(rss_dir, 'index.md')

    with open(index_path, 'w') as index_file:
        # Write the custom header with SVG
        index_file.write('''
<svg width="800" height="200">
  <rect width="800" height="200" fill="#f3f4f6"/>
  <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="24" fill="#333">XML Files Index</text>
</svg>

This index was automatically generated to list all XML files in the `rss` directory.

_Last updated: {datetime_now}_

'''.format(datetime_now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # Write the table header with SVG decorations
        index_file.write('''
<table>
  <thead>
    <tr>
      <th>File Name</th>
      <th>Link</th>
    </tr>
  </thead>
  <tbody>
''')

        # Write each file as a row in the table
        for file in files:
            index_file.write(f'''
    <tr>
      <td>{file}</td>
      <td><a href="./{file}">Link to {file}</a></td>
    </tr>
''')

        # Close the table
        index_file.write('''
  </tbody>
</table>
''')

if __name__ == "__main__":
    update_index()
