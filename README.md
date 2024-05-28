
# RSS Feed Generator

This project is a Python-based RSS feed generator that processes specified websites and generates RSS feeds in XML format. It is designed to handle multiple sites or groups of sites as configured in a JSON file.

## Features

- **Dynamic Script Loading**: Loads and runs Python scripts dynamically for each website or group of websites.
- **RSS Feed Generation**: Converts scraped data into RSS XML format.
- **Configurable**: Easily configurable via a JSON file to add or modify websites and corresponding scripts.

## Prerequisites

Before you run the project, you need to have Python installed on your machine. The project was developed with Python 3.9, but it should work with other Python 3 versions.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ALeX400/Multi-RSS.git
   cd Multi-RSS
   ```

2. Install required Python packages:
   ```bash
   pip install requests beautifulsoup4 lxml json5
   ```

## Configuration

Edit the `config.json` file to add or modify the groups or sites you want to scrape. Here is an example structure of the `config.json` file:

```json
{
    "Groups": {
        "Group_1": {
            "Urls": [
                "http://example.com/Page1.html",
                "http://example.com/Page2.html"
            ],
            "Scripts": [
                "pattern_page1.py",
                "pattern_page2.py"
            ],
            "FileName": null
        }
    },
    "Sites": {
        "Site_1": {
            "url": "http://example.com/Page1.html",
            "script": "pattern_page1.py",
            "FileName": null
        }
    }
}
```

## Usage

Run the main script from the command line:

```bash
python main.py
```

This will generate XML files in the `rss` directory based on your configuration.

## Output

The generated XML files will be stored in the `rss` directory. If `FileName` is set to `null` in the configuration, the name will default to the group or site name.

## Contributing

Contributions are welcome! Feel free to fork the repository and submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
