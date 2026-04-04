# Custom Dockerfile for Terraform + AWS CLI
FROM hashicorp/terraform:latest

# Install AWS CLI dependencies and AWS CLI
RUN apk add --no-cache python3 py3-pip groff less && \
    pip3 install --no-cache-dir awscli

WORKDIR /workspace
ENTRYPOINT ["/bin/sh"]
