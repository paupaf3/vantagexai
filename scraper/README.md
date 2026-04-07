# VantageX.ai | Data Scraper 🕵️‍♂️

This is the data acquisition engine for VantageX.ai. It uses official APIs for product data collection and can run locally or as an ECS Fargate task on AWS.

## 🚀 Features

- **API-First:** Uses eBay's official Browse API for fast, reliable, and compliant data collection.
- **OAuth 2.0 Auth:** Securely authenticates with eBay using your developer credentials.
- **Multi-Item Search:** Pass one or more product queries on the command line.
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

To run the eBay scraper locally, pass the mode and one or more items:

```bash
python src/scraper.py ebay "rtx 5080" "macbook m3"
# or
pipenv run python src/scraper.py serper "rtx 5080" "macbook m3"
```

Output will be saved as JSON files in `../data/scraper/` (relative to the script).

### AWS Deployment

The current deployed path is:

1. API Gateway receives a `POST /trigger-scraper` request.
2. Lambda validates the payload and starts an ECS task.
3. The ECS task runs as a Fargate task.
4. The scraper uploads output to S3.

Example payload:

```json
{
  "mode": "ebay",
  "items": ["rtx 5080", "macbook m3"]
}
```

## ⚙️ Project Structure

- `src/scraper.py`: Main scraper script for eBay and Serper.
- `src/items.py`: Optional query presets for local experimentation.
- `requirements.txt` or `Pipfile`: Dependency management.
- `data/scraper/`: Local JSON output folder.

## 🛡️ Ethical Data Collection

- Uses official APIs where possible for compliance and reliability.
- No scraping of protected or private data.
- Targeted for educational use and personal dataset generation.
