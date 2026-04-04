terraform:
	docker-compose run terraform

scraper-install:
	cd scraper && pipenv install --dev --skip-lock

# Usage: make scrap MODE=ebay or make scrap MODE=serper
scrap-ebay:
	cd scraper && pipenv run python src/scraper.py ebay

scrap-serper:
	cd scraper && pipenv run python src/scraper.py serper