# VantageX.ai

Stop searching, start finding. VantageX.ai is an AWS-powered shopping assistant that uses GenAI to find the perfect product at the perfect price.

## 🚧 Under Development

This project is currently in active development. Its primary goal is to provide hands-on experience with AWS fundamentals through a practical Data Scraping, Retrieval-Augmented Generation (RAG), and GenAI application.

## 🚀 The Vision

To move from "Search & Filter" to "Consult & Recommend." VantageX.ai helps users find products that meet complex, real-world needs through semantic reasoning.

## 🛠 Tech Stack

- **Frontend:** React/Next.js/Angular? via **AWS Amplify**
- **AI/LLM:** Claude 3.5 Sonnet? via **Amazon Bedrock**
- **Compute:** **AWS Lambda** (Serverless Python)
- **Database:** **Amazon DynamoDB** (NoSQL)
- **Storage:** **Amazon S3**
- **Auth:** **Amazon Cognito**

## 🌟 Key Features

- **Semantic Search:** Find products by description and "vibe," not just tags.
- **AI Advisor:** A conversational agent that asks clarifying questions.
- **Review Synthesis:** Instant summaries of pros/cons across multiple sources.

---

## 🕵️ Data Scraping Engine

VantageX.ai includes a flexible data scraper supporting both eBay and Serper.dev (Google Shopping) APIs. You can select the data source using Makefile targets or command-line arguments.

### Scraper Features

- **API-First:** Uses official APIs for eBay and Serper.dev for reliable, compliant data collection.
- **Multi-Source:** Choose between eBay or Serper.dev for product data.
- **Multi-Item Search:** Define product queries in `scraper/src/items.py`.
- **Rich Output:** Product name, price, currency, description, and URL.

### Installation

1. Install dependencies (from the `scraper/` directory):
   ```sh
   make scraper-install
   # or
   pip install -r requirements.txt
   # or
   pipenv install
   ```
2. Set up your API credentials in `scraper/.env`:
   ```env
   # For eBay
   EBAY_CLIENT_ID=your_client_id
   EBAY_CLIENT_SECRET=your_client_secret
   # For Serper.dev
   SERPER_API_KEY=your_serper_api_key
   ```

### Usage

You can run the scraper for either eBay or Serper.dev:

- **eBay:**
  ```sh
  make scrap-ebay
  # or
  cd scraper && pipenv run python src/scraper.py ebay
  ```
- **Serper.dev:**
  ```sh
  make scrap-serper
  # or
  cd scraper && pipenv run python src/scraper.py serper
  ```

Output JSON files will be saved in `data/scraper/` (relative to the project root).

#### Project Structure

- `scraper/src/scraper.py`: Main scraper script (supports both APIs)
- `scraper/src/items.py`: List of product queries
- `scraper/requirements.txt` or `scraper/Pipfile`: Dependencies
- `data/scraper/`: Output folder for scraped data

---

## 🏗️ Infrastructure Setup (Terraform + Docker)

This project uses Terraform (via Docker) to provision AWS infrastructure, such as the S3 bucket for scraped data. No local installation of Terraform or AWS CLI is required.

### Prerequisites

- Docker installed
- AWS credentials in `~/.aws/credentials` (with permissions to create S3 buckets)
- Access to the AWS Free Tier

### Steps to Create the S3 Bucket

1. Start a shell in the Terraform container:
   ```sh
   make terraform
   # or
   docker compose run terraform
   ```
2. Inside the container, initialize Terraform:
   ```sh
   terraform init
   ```
3. (Optional) Preview what will be created:
   ```sh
   terraform plan
   ```
4. Apply the configuration to create the bucket:

   ```sh
   terraform apply
   ```

   - Type `yes` when prompted.

5. Note the bucket name from the output.

### To Remove (Destroy) the S3 Bucket and All Resources

1. Start a shell in the Terraform container (if not already inside):
   ```sh
   make terraform
   # or
   docker compose run terraform
   ```
2. Inside the container, run:

   ```sh
   terraform destroy
   ```

   - Type `yes` when prompted.

This will delete the S3 bucket and any other resources managed by your Terraform configuration.
