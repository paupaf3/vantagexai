# S3 bucket outputs
output "bucket_name" {
  description = "The name of the S3 bucket."
  value       = aws_s3_bucket.scraper_data.bucket
}
