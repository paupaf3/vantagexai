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

# IAM Role for EC2 to access S3
resource "aws_iam_role" "ec2_scraper_role" {
  name = "ec2_scraper_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# IAM Policy Attachment for S3 access
resource "aws_iam_role_policy_attachment" "ec2_scraper_s3" {
  role       = aws_iam_role.ec2_scraper_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Instance Profile for EC2
resource "aws_iam_instance_profile" "ec2_scraper_profile" {
  name = "ec2_scraper_profile"
  role = aws_iam_role.ec2_scraper_role.name
}

# Security Group for EC2
resource "aws_security_group" "scraper_sg" {
  name        = "scraper_sg"
  description = "Allow SSH and HTTP access"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Get default VPC and subnet
data "aws_vpc" "default" {
  default = true
}
data "aws_subnet_ids" "default" {
  vpc_id = data.aws_vpc.default.id
}

# EC2 Instance for Scraper
resource "aws_instance" "scraper" {
  ami                    = "ami-0c55b159cbfafe1f0" # Ubuntu 22.04 LTS in eu-central-1
  instance_type          = "t3.micro"
  subnet_id              = data.aws_subnet_ids.default.ids[0]
  vpc_security_group_ids = [aws_security_group.scraper_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_scraper_profile.name
  tags = {
    Name = "scraper-ec2"
  }
}
