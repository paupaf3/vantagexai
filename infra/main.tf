# Configure the AWS provider
provider "aws" {
  region = "eu-central-1"
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
