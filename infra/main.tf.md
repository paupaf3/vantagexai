# Terraform main.tf Documentation for EC2 Scraper Deployment

This document explains each resource and configuration block in the `main.tf` file for deploying an EC2-based scraper with S3 access on AWS using Terraform.

---

## 1. AWS Provider

```
provider "aws" {
  region = "eu-central-1"
}
```

- **Purpose:** Configures Terraform to use AWS in the Frankfurt (eu-central-1) region.

---

## 2. S3 Bucket for Scraper Data

```
resource "aws_s3_bucket" "scraper_data" {
  bucket = "vantagexai-scraper-data-${random_id.suffix.hex}"
  tags = {
    Name        = "scraper-data-bucket"
    Environment = "dev"
  }
}
```

- **Purpose:** Creates a unique S3 bucket for storing scraped data.
- **Tags:** Used for identification and environment separation.

---

## 3. Random Suffix for Bucket Name

```
resource "random_id" "suffix" {
  byte_length = 4
}
```

- **Purpose:** Ensures the S3 bucket name is globally unique by appending a random hex string.

---

## 4. IAM Role for EC2 S3 Access

```
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
```

- **Purpose:** Allows EC2 instances to assume this role and gain permissions.
- **Policy Version:** "2012-10-17" is the required AWS policy language version.

---

## 5. Attach S3 Full Access Policy to Role

```
resource "aws_iam_role_policy_attachment" "ec2_scraper_s3" {
  role       = aws_iam_role.ec2_scraper_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}
```

- **Purpose:** Grants the EC2 role full access to S3 resources.

---

## 6. Instance Profile for EC2

```
resource "aws_iam_instance_profile" "ec2_scraper_profile" {
  name = "ec2_scraper_profile"
  role = aws_iam_role.ec2_scraper_role.name
}
```

- **Purpose:** Allows the EC2 instance to use the IAM role.

---

## 7. Security Group for EC2

```
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
```

- **Purpose:** Controls network access to the EC2 instance.
- **Ingress:** Allows SSH (22) and HTTP (80) from anywhere.
- **Egress:** Allows all outbound traffic.

---

## 8. Get Default VPC and Subnets

```
data "aws_vpc" "default" {
  default = true
}
data "aws_subnet_ids" "default" {
  vpc_id = data.aws_vpc.default.id
}
```

- **Purpose:** Fetches the default VPC and its subnets for EC2 placement.

---

## 9. EC2 Instance for Scraper

```
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
```

- **Purpose:** Provisions an Ubuntu EC2 instance for running the scraper.
- **AMI:** Ubuntu 22.04 LTS for the Frankfurt region.
- **Instance Type:** t3.micro (free tier eligible).
- **Network:** Uses the first subnet in the default VPC and the defined security group.
- **IAM:** Uses the instance profile for S3 access.
- **Tags:** For easy identification.

---

## Summary

This configuration provisions:

- An S3 bucket for data
- An EC2 instance with S3 access
- All required IAM and network resources

You can recreate the infrastructure by running `terraform init` and `terraform apply` in the `infra/` directory.
