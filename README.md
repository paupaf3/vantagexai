# VantageX.ai

Stop searching, start finding. VantageX.ai is an AWS-powered shopping assistant that uses GenAI to find the perfect product at the perfect price.

## 🚧 Under Development

This project is currently in active development. Its primary goal is to provide hands-on experience with AWS fundamentals through a practical Data Scraping, Retrieval-Augmented Generation (RAG), and GenAI application.

## 🚀 The Vision

To move from "Search & Filter" to "Consult & Recommend." VantageX.ai helps users find products that meet complex, real-world needs through semantic reasoning.

## 🛠 Tech Stack

- **Frontend:** React/Next.js/Angular? via **AWS Amplify**
- **AI/LLM:** Claude 3.5 Sonnet? via **Amazon Bedrock**
- **Scraper Compute:** **ECS Fargate** triggered by **AWS Lambda** and **API Gateway**
- **App Compute:** **AWS Lambda** (future serverless app logic)
- **Database:** **Amazon DynamoDB** (NoSQL)
- **Storage:** **Amazon S3**
- **Auth:** **Amazon Cognito**

## 🌟 Key Features

- **Semantic Search:** Find products by description and "vibe," not just tags.
- **AI Advisor:** A conversational agent that asks clarifying questions.
- **Review Synthesis:** Instant summaries of pros/cons across multiple sources.

---

## 🕵️ Data Scraping Engine

VantageX.ai includes a Dockerized data scraper that can run locally or as an ECS task. The current deployed path is **API Gateway -> Lambda -> ECS RunTask -> ECS Fargate task**.

### Scraper Features

- **API-First:** Uses official APIs for eBay and Serper.dev for reliable, compliant data collection.
- **Multi-Source:** Choose between eBay or Serper.dev for product data.
- **CLI-Driven Search:** Pass one or more product queries at runtime.
- **Rich Output:** Product name, price, currency, description, and URL.
- **Structured Logging:** All output goes through Python's `logging` module (timestamped, levelled).
- **Deduplication:** Duplicate product IDs within a single query are filtered before saving.
- **Resilient Requests:** All HTTP calls include a 15-second timeout and network error handling.

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

You can run the scraper locally for either eBay or Serper.dev:

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

Output JSON files will be saved in `data/scraper/` (relative to the project root) by default. Override the output path with the `SCRAPER_OUTPUT_DIR` environment variable (set automatically to `/tmp/scraper` when running in Docker/ECS).

### Deployed Trigger Flow

The deployed path uses an authenticated HTTP API to start scraper jobs on AWS:

1. Send a `POST` request with a `Bearer` token to the API Gateway endpoint.
2. A Lambda authorizer validates the token against a secret stored in **AWS SSM Parameter Store**.
3. On success, Lambda validates the payload and calls `ECS RunTask`.
4. ECS starts the scraper container as a Fargate task.
5. The scraper uploads results to S3.

The API accepts a payload like:

```sh
curl -X POST <api_url>/trigger-scraper \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"mode": "ebay", "items": ["rtx 5080", "macbook m3"]}'
```

> **Before deploying:** create the token in SSM (this keeps it out of the repo and Terraform state):
> ```sh
> aws ssm put-parameter \
>   --name "/vantagexai/api-token" \
>   --value "<your-secret-token>" \
>   --type SecureString \
>   --region eu-central-1
> ```

#### Project Structure

- `scraper/src/scraper.py`: Main scraper script (supports both APIs)
- `scraper/src/items.py`: Optional query presets for local experimentation
- `scraper/requirements.txt` or `scraper/Pipfile`: Dependencies
- `data/scraper/`: Output folder for scraped data

---

## 🏗️ Infrastructure Setup (Terraform + Docker)

This project uses Terraform (via Docker) to provision AWS infrastructure, including the S3 bucket, ECS cluster, Fargate task definition, Lambda trigger, and API Gateway. No local installation of Terraform or AWS CLI is required.

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
