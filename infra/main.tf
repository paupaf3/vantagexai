# Configure the AWS provider
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

# Create an S3 bucket (unique name required)
resource "aws_s3_bucket" "scraper_data" {
  bucket = "vantagexai-scraper-data-${random_id.suffix.hex}"

  tags = {
    Name        = "scraper-data-bucket"
    Environment = "dev"
  }
}

# Random suffix to ensure bucket name uniqueness
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_server_side_encryption_configuration" "scraper_data" {
  bucket = aws_s3_bucket.scraper_data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "scraper_data" {
  bucket                  = aws_s3_bucket.scraper_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Get default VPC and subnets
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

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

resource "aws_iam_policy" "ecs_task_s3_access" {
  name = "vantagexai_ecs_task_s3_access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.scraper_data.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.scraper_data.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_s3_access_attach" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_s3_access.arn
}

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

data "archive_file" "lambda_trigger_scraper_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/trigger_scraper.py"
  output_path = "${path.module}/lambda/trigger_scraper.zip"
}

resource "aws_iam_role" "lambda_trigger_scraper_role" {
  name = "lambda_trigger_scraper_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_trigger_scraper_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_ecs_run_task" {
  name = "lambda_ecs_run_task_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = [
          aws_ecs_task_definition.scraper.arn,
          "${aws_ecs_task_definition.scraper.arn_without_revision}:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_task_execution_role.arn,
          aws_iam_role.ecs_task_role.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeTasks"
        ]
        Resource = ["arn:aws:ecs:*:${data.aws_caller_identity.current.account_id}:task/${aws_ecs_cluster.scraper.name}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_ecs_run_task_attach" {
  role       = aws_iam_role.lambda_trigger_scraper_role.name
  policy_arn = aws_iam_policy.lambda_ecs_run_task.arn
}

resource "aws_lambda_function" "trigger_scraper" {
  function_name    = "trigger-scraper-job"
  role             = aws_iam_role.lambda_trigger_scraper_role.arn
  runtime          = "python3.12"
  handler          = "trigger_scraper.lambda_handler"
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

# ---------------------------------------------------------------------------
# API Authorizer — token stored in SSM Parameter Store (SecureString).
# Before the first `terraform apply`, create the parameter manually:
#   aws ssm put-parameter \
#     --name "/vantagexai/api-token" \
#     --value "<your-secret-token>" \
#     --type SecureString \
#     --region eu-central-1
# ---------------------------------------------------------------------------

data "archive_file" "lambda_authorizer_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/authorizer.py"
  output_path = "${path.module}/lambda/authorizer.zip"
}

resource "aws_iam_role" "lambda_authorizer_role" {
  name = "lambda_authorizer_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "authorizer_basic_execution" {
  role       = aws_iam_role.lambda_authorizer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "authorizer_ssm_read" {
  name = "lambda_authorizer_ssm_read"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter"]
      Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/vantagexai/api-token"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "authorizer_ssm_attach" {
  role       = aws_iam_role.lambda_authorizer_role.name
  policy_arn = aws_iam_policy.authorizer_ssm_read.arn
}

resource "aws_lambda_function" "authorizer" {
  function_name    = "vantagexai-api-authorizer"
  role             = aws_iam_role.lambda_authorizer_role.arn
  runtime          = "python3.12"
  handler          = "authorizer.lambda_handler"
  filename         = data.archive_file.lambda_authorizer_zip.output_path
  source_code_hash = data.archive_file.lambda_authorizer_zip.output_base64sha256
  timeout          = 5

  environment {
    variables = {
      API_TOKEN_PARAM = "/vantagexai/api-token"
    }
  }
}

resource "aws_lambda_permission" "allow_apigw_invoke_authorizer" {
  statement_id  = "AllowExecutionFromAPIGatewayAuthorizer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.scraper_api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_api" "scraper_api" {
  name          = "scraper-trigger-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_authorizer" "token_auth" {
  api_id                            = aws_apigatewayv2_api.scraper_api.id
  authorizer_type                   = "REQUEST"
  authorizer_uri                    = aws_lambda_function.authorizer.invoke_arn
  identity_sources                  = ["$request.header.Authorization"]
  name                              = "token-authorizer"
  authorizer_payload_format_version = "2.0"
  enable_simple_responses           = true
  authorizer_result_ttl_in_seconds  = 300
}

resource "aws_apigatewayv2_integration" "scraper_lambda" {
  api_id                 = aws_apigatewayv2_api.scraper_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.trigger_scraper.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "trigger_scraper" {
  api_id             = aws_apigatewayv2_api.scraper_api.id
  route_key          = "POST /trigger-scraper"
  target             = "integrations/${aws_apigatewayv2_integration.scraper_lambda.id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.token_auth.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.scraper_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "allow_apigw_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger_scraper.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.scraper_api.execution_arn}/*/*"
}

data "aws_region" "current" {}
