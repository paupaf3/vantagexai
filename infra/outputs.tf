# S3 bucket outputs
output "bucket_name" {
  description = "The name of the S3 bucket."
  value       = aws_s3_bucket.scraper_data.bucket
}

output "scraper_ecs_cluster_arn" {
  description = "ECS cluster ARN used for scraper tasks."
  value       = aws_ecs_cluster.scraper.arn
}

output "scraper_task_definition_arn" {
  description = "ECS task definition ARN used by the trigger Lambda."
  value       = aws_ecs_task_definition.scraper.arn
}

output "trigger_scraper_lambda_name" {
  description = "Lambda function that triggers scraper jobs as ECS tasks."
  value       = aws_lambda_function.trigger_scraper.function_name
}

output "scraper_trigger_api_url" {
  description = "HTTP API Gateway invoke URL for triggering scraper jobs."
  value       = aws_apigatewayv2_api.scraper_api.api_endpoint
}

output "api_token_ssm_setup" {
  description = "Run this command once before deploying to store your API token in SSM."
  value       = "aws ssm put-parameter --name '/vantagexai/api-token' --value '<your-secret-token>' --type SecureString --region ${data.aws_region.current.name}"
}
