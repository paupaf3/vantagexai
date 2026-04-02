# VantageX.ai Project Roadmap

## Phase 1: Data & Ingestion (The Foundation) 🏗️

- [ ] Initialize AWS Environment (IAM, CLI).
- [ ] Create **S3 Bucket** for product "data drops."
- [ ] Setup **DynamoDB** table using Single-Table Design.
- [ ] Create Web Scraping logic to create static dataset (avoid running in AWS due to cost, and use static data obtained from local execution)
- [ ] Create a **Lambda Python** script to parse JSON product data into the database.

## Phase 2: The Intelligence Engine (AI Core) 🧠

- [ ] Enable **Amazon Bedrock** model access.
- [ ] Implement Semantic Search (Text-to-Embeddings).
- [ ] Build a "Value Score" logic in Lambda to compare product features vs. price.

## Phase 3: The Interface (Frontend) 💻

- [ ] Deploy a React skeleton to **AWS Amplify**.
- [ ] Connect the UI to the backend via API Gateway.
- [ ] Implement **Amazon Cognito** for personalized user "Watchlists."

## Phase 4: Conversational Shopping 🤖

- [ ] Implement **Bedrock Agents** for a multi-turn chat experience.
- [ ] Add "Price Drop" notification logic using **Amazon SNS**.

## Out of Scope (V1)

- Real-time web scraping (Use static datasets scrapped with same logic, but executed locally).
- Multi-region deployment.
- Mobile native application.
