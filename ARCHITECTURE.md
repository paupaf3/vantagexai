# Architecture Overview: VantageX.ai

The project follows a **Fully Serverless** architecture to minimize costs and maximize scalability while learning AWS best practices.

## System Flow

1.  **User Entry:** User interacts with the **Amplify** frontend.
2.  **API Layer:** Requests are routed through **Amazon API Gateway** to **AWS Lambda**.
3.  **Intelligence Layer:** \* Lambda invokes **Amazon Bedrock** to process natural language.
    - Bedrock performs a **Vector Search** (Embeddings) to find products with the highest "utility" for the user's specific need.
4.  **Data Layer:** Product specs and price history are retrieved from **DynamoDB**.
5.  **Delivery:** The AI synthesizes a "Recommendation Report" explaining _why_ the product is the smartest financial choice.

## Infrastructure Diagram Goal

_Planned: [Insert Excalidraw Export here]_
