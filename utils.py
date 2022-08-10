from urllib2 import urlopen
from selenium import webdriver
import csv
import time
import sys

reload(sys)
sys.setdefaultencoding('utf-8')


class BaseScraper:
    GECKODRIVER_EXECUTABLE_PATH = 'selenium/geckodriver'

    def get_webdriver_options(self):
        options = webdriver.FirefoxOptions()
        options.headless = True
        return options

    def run(self):
        self.run_scraper()

    def fetch_page_html(self, url):
        html = urlopen(url)
        return str(html.read())
    
    def read_file(self, filename):
        with open(filename, 'r') as f:
            content = f.read()
        return content

    def write_to_file(self, content, filename):
        with open(filename, 'w') as f:
            f.write(content)

    def write_items_to_csv_file(
        self,
        items,
        fieldnames,
        csv_filename,
    ):
        with open(csv_filename, 'a') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                writer.writerow(item)

    def fetch_scrolled_page_html(self, url):
        driver = webdriver.Firefox(
            executable_path=self.GECKODRIVER_EXECUTABLE_PATH,
            options=self.get_webdriver_options(),
        )
        driver.get(url)
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.SCROLL_PAUSE_TIME)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            print('new_height: ', new_height)
        page_source = driver.page_source
        driver.close()
        return page_source
