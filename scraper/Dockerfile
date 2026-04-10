FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Write scraped files to /tmp inside the container; override with SCRAPER_OUTPUT_DIR if needed
ENV SCRAPER_OUTPUT_DIR=/tmp/scraper

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source directory over
COPY src/ /app/src/

# Establish the entrypoint instruction.
# Usage Example: docker run --env-file .env scraper_image ebay "laptop" "phone" --s3-bucket my-bucket
ENTRYPOINT ["python", "src/scraper.py"]