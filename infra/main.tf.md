# Terraform main.tf Documentation

This document explains the current `main.tf` configuration for running scraper jobs on AWS using ECS Fargate.

The stack provisions:

- An S3 bucket for scraper output
- ECS cluster and Fargate task definition for the scraper container
- Lambda function that starts ECS tasks
- API Gateway HTTP endpoint to trigger Lambda

## 1. Provider, Variables, and Locals

```hcl
provider "aws" {
  region = "eu-central-1"
}

variable "image_tag" {
  description = "ECR image tag for the scraper container"
  default     = "latest"
}

data "aws_caller_identity" "current" {}

locals {
  scraper_image_uri = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/vantagex-scraper:${var.image_tag}"
}
```

- `provider "aws"`: Sets deployment region to Frankfurt.
- `variable "image_tag"`: Controls the ECR image tag at deploy time (default `latest`). Override with `-var="image_tag=v1.2.3"`.
- `data.aws_caller_identity.current`: Resolves the AWS account ID automatically — no hardcoded values.
- `locals.scraper_image_uri`: ECR image URI used by the Fargate task definition, built from live data sources.

## 2. S3 Bucket and Random Suffix

```hcl
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "scraper_data" {
  bucket = "vantagexai-scraper-data-${random_id.suffix.hex}"
  tags   = { Name = "scraper-data-bucket", Environment = "dev" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "scraper_data" { ... }
resource "aws_s3_bucket_public_access_block" "scraper_data" { ... }
```

- `random_id.suffix`: Creates a random hex suffix for global uniqueness.
- `aws_s3_bucket.scraper_data`: Stores scraper output files.
- `aws_s3_bucket_server_side_encryption_configuration`: Enforces AES-256 encryption at rest on all objects.
- `aws_s3_bucket_public_access_block`: Blocks all public access to the bucket (ACLs and policies).

## 3. Networking Data Sources

```hcl
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_region" "current" {}
```

- Reads default VPC and subnets for Fargate task placement.
- Reads current region for log config and policy ARNs.

## 4. ECS Task Security Group

```hcl
resource "aws_security_group" "ecs_task_sg" {
  name        = "vantagexai-ecs-task-sg"
  description = "Security group for ECS Fargate tasks"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

- Applied to the Fargate task.
- Egress-only is enough for this outbound scraper workload.

## 5. ECS Cluster, Logs, and IAM Roles

```hcl
resource "aws_ecs_cluster" "scraper" {
  name = "vantagexai-scraper-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "ecs_scraper" {
  name              = "/ecs/vantagexai-scraper"
  retention_in_days = 14
}
```

- ECS cluster receives tasks. Container Insights is enabled for cluster-level CloudWatch metrics (CPU, memory, task count).
- Log group stores container stdout/stderr for 14 days.

### Task Execution Role

```hcl
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "vantagexai_ecs_task_execution_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_base" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
```

- Needed for pulling image from ECR and writing logs to CloudWatch.

### Task Role for S3

```hcl
resource "aws_iam_role" "ecs_task_role" {
  name = "vantagexai_ecs_task_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}
```

The attached policy grants task-level access to the scraper bucket:

- `s3:ListBucket` on bucket ARN
- `s3:PutObject` and `s3:GetObject` on bucket objects

## 6. ECS Task Definition (Scraper Container)

```hcl
resource "aws_ecs_task_definition" "scraper" {
  family                   = "vantagexai-scraper"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "scraper"
      image     = local.scraper_image_uri
      essential = true
      command   = ["ebay", "placeholder-item"]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_scraper.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "scraper"
        }
      }
    }
  ])
}
```

- Defines an ECS Fargate task with one container named `scraper`.
- Lambda overrides command at runtime with requested mode/items.

## 7. Lambda Packaging and IAM

```hcl
data "archive_file" "lambda_trigger_scraper_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/trigger_scraper.py"
  output_path = "${path.module}/lambda/trigger_scraper.zip"
}
```

- Packages the Lambda source file.

Lambda role has:

- `AWSLambdaBasicExecutionRole` for logs
- Custom policy to:
  - `ecs:RunTask` on scraper task definition (all revisions)
  - `ecs:DescribeTasks` scoped to tasks within the scraper cluster only
  - `iam:PassRole` for ECS task execution/task roles

## 8. Lambda Function

```hcl
resource "aws_lambda_function" "trigger_scraper" {
  function_name                  = "trigger-scraper-job"
  role                           = aws_iam_role.lambda_trigger_scraper_role.arn
  runtime                        = "python3.12"
  handler                        = "trigger_scraper.lambda_handler"
  filename                       = data.archive_file.lambda_trigger_scraper_zip.output_path
  source_code_hash               = data.archive_file.lambda_trigger_scraper_zip.output_base64sha256
  timeout                        = 30
  reserved_concurrent_executions = 5

  environment {
    variables = {
      ECS_CLUSTER_ARN         = aws_ecs_cluster.scraper.arn
      ECS_TASK_DEFINITION_ARN = aws_ecs_task_definition.scraper.arn_without_revision
      ECS_CONTAINER_NAME      = "scraper"
      ECS_SUBNET_IDS          = jsonencode(data.aws_subnets.default.ids)
      ECS_SECURITY_GROUP_IDS  = jsonencode([aws_security_group.ecs_task_sg.id])
      ECS_ASSIGN_PUBLIC_IP    = "ENABLED"
      DEFAULT_S3_BUCKET       = aws_s3_bucket.scraper_data.bucket
    }
  }
}
```

- Starts ECS tasks dynamically using `ecs.run_task`.
- Uses env vars for cluster/task defaults and Fargate network placement.
- `reserved_concurrent_executions = 5`: Caps simultaneous Lambda invocations to prevent runaway ECS task launches.
- `ECS_TASK_DEFINITION_ARN` uses `arn_without_revision` so ECS always picks the latest active revision automatically.

## 9. API Authorizer (Token-Based)

The `POST /trigger-scraper` endpoint is protected by a Lambda REQUEST authorizer. The secret token is stored in **AWS SSM Parameter Store** as a `SecureString` — it never appears in code or Terraform state.

### One-time setup (before first `terraform apply`)

```sh
aws ssm put-parameter \
  --name "/vantagexai/api-token" \
  --value "<your-secret-token>" \
  --type SecureString \
  --region eu-central-1
```

### How it works

```
Client → API Gateway → Authorizer Lambda → checks SSM token → allow/deny
                                                 ↓ (if allowed)
                                          Trigger Lambda → ECS RunTask
```

- `aws_lambda_function.authorizer`: Reads the token from SSM (cached in-memory for the container lifetime). Returns `{"isAuthorized": true/false}`.
- `aws_apigatewayv2_authorizer.token_auth`: REQUEST authorizer with `enable_simple_responses = true` and a 5-minute result cache (reduces SSM calls).
- IAM policy grants the authorizer Lambda `ssm:GetParameter` on the specific parameter path only.

### Calling the API

```sh
curl -X POST <api_url>/trigger-scraper \
  -H "Authorization: Bearer <your-secret-token>" \
  -H "Content-Type: application/json" \
  -d '{"mode": "ebay", "items": ["rtx 5080"]}'
```

Requests without a valid token receive `403 Forbidden`.

## 10. API Gateway HTTP API

```hcl
resource "aws_apigatewayv2_api" "scraper_api" { ... }
resource "aws_apigatewayv2_integration" "scraper_lambda" { ... }

resource "aws_apigatewayv2_route" "trigger_scraper" {
  route_key          = "POST /trigger-scraper"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.token_auth.id
  ...
}
```

- Exposes `POST /trigger-scraper` endpoint, protected by the token authorizer.

## 11. Runtime Request Flow

1. Client sends `POST /trigger-scraper` with `Authorization: Bearer <token>` header.
2. API Gateway invokes the authorizer Lambda to validate the token.
3. On success, API Gateway invokes the trigger Lambda.
4. Lambda validates `mode` and `items`, then calls ECS `RunTask` with a command override.
5. ECS schedules the scraper container as a Fargate task.
6. Container runs the scraper and uploads output to S3.

## 12. Example API Payload

```sh
curl -X POST <scraper_trigger_api_url>/trigger-scraper \
  -H "Authorization: Bearer <your-secret-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "ebay",
    "items": ["rtx 5080", "macbook m3"]
  }'
```

Optional field: `s3_bucket` — overrides the default S3 bucket for that job.

## Notes

- The ECR image URI is built automatically from the live AWS account ID — no hardcoded values needed.
- To deploy a specific image version: `terraform apply -var="image_tag=v1.2.3"`.
- The SSM parameter must exist before `terraform apply` — Terraform does not create it (by design, to keep secrets out of state).
