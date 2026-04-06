# S3 bucket outputs
output "bucket_name" {
  description = "The name of the S3 bucket."
  value       = aws_s3_bucket.scraper_data.bucket
}

# EC2 Instance Outputs
output "scraper_instance_id" {
  description = "The ID of the EC2 instance running the scraper."
  value       = aws_instance.scraper.id
}

output "scraper_instance_public_ip" {
  description = "The public IP of the EC2 instance running the scraper."
  value       = aws_instance.scraper.public_ip
}
