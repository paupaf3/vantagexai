scraper-install:
	cd scraper && pipenv install --dev --skip-lock

scrap:
	cd scraper && pipenv run python src/scraper.py