# VantageX.ai | Data Scraper 🕵️‍♂️

This is the data acquisition engine for VantageX.ai. It now uses the official eBay Browse API for robust, reliable, and ethical data collection, and is ready for extension to other APIs or scraping methods.

## 🚀 Features

- **API-First:** Uses eBay's official Browse API for fast, reliable, and compliant data collection.
- **OAuth 2.0 Auth:** Securely authenticates with eBay using your developer credentials.
- **Multi-Item Search:** Define a list of products to search in `src/items.py`.
- **Rich Output:** Captures product name, price, currency, description, and URL.

## 📥 Installation

1. Install dependencies (Pipenv or requirements.txt):

   ```bash
   pip install -r requirements.txt
   # or
   pipenv install
   ```

2. Set up your eBay API credentials:
   - Create a `.env` file in the `scraper/` directory with:
     ```env
     EBAY_CLIENT_ID=your_client_id
     EBAY_CLIENT_SECRET=your_client_secret
     ```

## 🏃‍♂️ Usage

To run the eBay scraper for all items in `src/items.py`:

```bash
python src/scraper.py
# or
pipenv run python src/scraper.py
```

Output will be saved as JSON files in `../data/scraper/` (relative to the script).

## ⚙️ Project Structure

- `src/scraper.py`: Main eBay API scraper script.
- `src/items.py`: List of product queries to search.
- `requirements.txt` or `Pipfile`: Dependency management.
- `data/scraper/`: Local JSON output folder.

## 🛡️ Ethical Data Collection

- Uses official APIs where possible for compliance and reliability.
- No scraping of protected or private data.
- Targeted for educational use and personal dataset generation.
