from robocorp.tasks import task
from robocorp import browser
from RPA.Robocorp.WorkItems import WorkItems
from RPA.Excel.Files import Files as Excel
import re
import requests
import logging
import os
from datetime import datetime

OUTPUT_DIR = 'output'
page = browser.page()
workitems = WorkItems()
workitems.get_input_work_item()
search_phrase = workitems.get_work_item_variable("search_phrase")
excel = Excel()

@task
def main():
  """Runs the Main Task"""
  open_website()
  fill_search(search_phrase)
  setting_newest()
  scrape_articles()
  download_excel()

def open_website():
  """Navigate to URL"""
  page.set_default_navigation_timeout(50000)
  page.goto('https://www.latimes.com')


def fill_search(search_phrase):
  """Fills the Seach Field With Input"""
  page.click('svg[data-element="magnify-icon"]')
  page.fill('input[data-element="search-form-input"]', search_phrase)
  page.press('input[data-element="search-form-input"]', 'Enter')

def setting_newest():
  """Sets the order by newest content"""
  page.select_option('select.select-input', '1')

def download_image(url, base_name):
    """Downloads the Images"""
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

def scrape_articles():
  """Iterates all the articles and get information from it"""
  articles = []
  articles_elements = page.query_selector_all('.promo-wrapper')
  monetary_regex = r"\$\d+(\.\d{1,2})?|\d+(\.\d{1,2})?\s*dollars?|\d+(\.\d{1,2})?\s*USD"

  for article in articles_elements:
    try:
        title_element =  article.query_selector('.promo-title')
        date_element =  article.query_selector('.promo-timestamp')
        description_element =  article.query_selector('.promo-description')
        img_element =  article.query_selector('img.image')

        title =  title_element.inner_text() if title_element else 'No Title Available'
        date =  date_element.inner_text() if date_element else 'No Date Available'
        if 'ago' in date:
            date = datetime.now().strftime('%B %d, %Y')
        description =  description_element.inner_text() if description_element else 'No Description Available'
        img_url =  img_element.get_attribute('src') if img_element else 'No Url Available'

        img_name = download_image(img_url, search_phrase) if img_url != 'No Url Available' else 'No Image Available'
        img_name = os.path.basename(img_name) if img_name else 'No Image Available'

        monetary_presence = bool(re.search(monetary_regex, title)) or bool (re.search(monetary_regex, description))

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
  return articles

def download_excel():
  """Download the list to a excel file and saves in the output folder"""
  articles = scrape_articles()

  if not articles:
    logging.info('No data to save')
  else:
    output_path = os.path.join(OUTPUT_DIR, 'news_data.xlsx')
    excel.create_workbook(output_path)
    excel.append_rows_to_worksheet(articles, header=True)
    excel.save_workbook()
    logging.info('Data Saved')
