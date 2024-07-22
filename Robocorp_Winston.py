import os
import re
import requests
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
import pandas as pd
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Diretório de saída
OUTPUT_DIR = 'output'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

class ImageDownloader:
    @staticmethod
    def download_image(url, base_name):
        counter = 1
        while True:
            file_name = os.path.join(OUTPUT_DIR, f"{base_name}_{counter}.jpg")
            if not os.path.exists(file_name):
                break
            counter += 1

        img_download = requests.get(url)
        if img_download.status_code == 200:
            with open(file_name, 'wb') as f:
                f.write(img_download.content)
            return file_name
        else:
            logging.error('Error in downloading image')
            return None

class ArticleScraper:
    @staticmethod
    def contain_monetary(text):
        monetary_regex = r"\$\d+(\.\d{1,2})?|\d+(\.\d{1,2})?\s*dollars?|\d+(\.\d{1,2})?\s*USD"
        return bool(re.search(monetary_regex, text))

    async def scrape_articles(self, search_phrase):
        articles = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto('https://www.latimes.com/', timeout=60000)
            await page.click('xpath=//html/body/ps-header/header/div[2]/button', timeout=30000)
            await page.fill('input[data-element="search-form-input"]', search_phrase)
            await page.press('input[data-element="search-form-input"]', 'Enter')

            try:
                await page.select_option('xpath=//html/body/div[2]/ps-search-results-module/form/div[2]/ps-search-filters/div/main/div[1]/div[2]/div/label/select', value='1', timeout=20000)
            except Exception as e:
                logging.error(f'Error finding the dropdown: {e}')

            await page.wait_for_timeout(3000)
            articles_elements = await page.query_selector_all('.promo-wrapper')

            for article in articles_elements:
                try:
                    title_element = await article.query_selector('.promo-title')
                    date_element = await article.query_selector('.promo-timestamp')
                    description_element = await article.query_selector('.promo-description')
                    img_element = await article.query_selector('img.image')

                    title = await title_element.inner_text() if title_element else 'No Title Available'
                    date = await date_element.inner_text() if date_element else 'No Date Available'
                    if 'ago' in date:
                        date = datetime.now().strftime('%B %d, %Y')
                    description = await description_element.inner_text() if description_element else 'No Description Available'
                    img_url = await img_element.get_attribute('src') if img_element else 'No Url Available'

                    img_name = ImageDownloader.download_image(img_url, search_phrase)
                    img_name = os.path.basename(img_name) if img_name else 'No Image Available'

                    monetary_presence = self.contain_monetary(title) or self.contain_monetary(description)

                    articles.append({
                        'title': title,
                        'date': date,
                        'description': description,
                        'picture_filename': img_name,
                        'count_phrases': title.count(search_phrase) + description.count(search_phrase),
                        'contains_monetary': monetary_presence
                    })
                except Exception as e:
                    logging.error(f'Error extracting content info: {e}')

            await browser.close()

        return articles

async def main():
    search_phrase = input('Type your search topic: ')
    scraper = ArticleScraper()
    articles = await scraper.scrape_articles(search_phrase)

    df = pd.DataFrame(articles)
    if df.empty:
        logging.info("No data to save.")
    else:
        output_path = os.path.join(OUTPUT_DIR, 'news_data.xlsx')
        df.to_excel(output_path, index=False)
        logging.info('Data saved')

if __name__ == "__main__":
    asyncio.run(main())
