from datetime import datetime
from bs4 import BeautifulSoup
from utils import BaseScraper
from os.path import exists
import time


class Scraper(BaseScraper):

    CACHE_ITEM_PAGES_TO_FILE = True
    CACHE_INDEX_PAGE_TO_FILE = True
    USE_CACHED_ITEM_PAGES = True
    USE_CACHED_INDEX_PAGE = True
    HANDLE_INFINITE_SCROLL = True
    SCROLL_PAUSE_TIME = 3.0
    PAGE_FETCHING_TIMEOUT = 0.2

    INDEX_PAGE_FILENAME = 'pages/index_page_fully_scrolled.html'
    ITEM_DETAILED_PAGE_FILENAME = 'pages/detailed_pages/%s.html'
    CSV_RESULT_FILENAME = 'csv/%s_parsed_items.csv'
    GECKODRIVER_EXECUTABLE_PATH = 'selenium/geckodriver'
    INDEX_PAGE_URL = 'https://www.meinauftrag.rib.de/public/publications'

    def collect_items(self, index_page_html):

        def _remove_spaces(text):
            text = text.replace('\\r', '')
            text = text.replace('\\n', '')            
            return text

        def get_item_id(item_index_left_div):
            span = item_index_left_div.find('span', {'class': 'info-actions'})
            href = span.find('a')['href']
            item_id = href.split('/')[-1]
            return int(item_id.strip())            

        def get_index_name(item_index_left_div):
            div = item_index_left_div.find('div')
            strong = div.find('strong')
            return strong.text.strip()            

        def get_index_description(item_index_left_div):
            div = item_index_left_div.find('div', {'class': 'text-muted'})
            text = _remove_spaces(div.text)
            text = text.split('Show further assignments by')[0]
            return text.strip()

        def get_index_publication_date(item_index_div):
            item_index_right_div = item_index_div.find('div', {'class': 'item-right'})
            month_div = item_index_right_div.find('div', {'class': 'month'}).text
            splitted_raw_month = month_div.split(' ')
            year = splitted_raw_month[-1]
            months_mapper = {
                'January': '01',
                'February': '02',
                'March': '03',
                'April': '04',
                'May': '05',
                'June': '06',
                'July': '07',
                'August': '08',
                'September': '09',
                'October': '10',
                'November': '11',
                'December': '12',
            }            
            month_name = splitted_raw_month[0]
            month = months_mapper[month_name]            
            day = item_index_right_div.find('div', {'class': 'date'}).text
            return '{0}. {1}. {2}'.format(day, month, year)


        def get_brief_description(item_tender_details):
            div = item_tender_details.find('div', {'class': 'col-md-12'})
            assert div.find('legend').text == 'Brief Description'
            tds = div.find_all('td')
            assert len(tds) == 1
            description = _remove_spaces(tds[0].text.strip())
            return description

        def _get_index_cols(item_index_cols):
            index_cols = {
                'index_application_period': '',
                'expiration_time': '',
                'index_application_deadline': '',
                'index_execution_timeframe': '',
                'index_place_of_execution': '',
            }
            for col in item_index_cols:
                div = col.find_all('div')
                field_name = div[0].text.strip()
                value = _remove_spaces(div[-1].text).strip()
                if field_name == 'Application Period':
                    index_cols['index_application_period'] = value
                elif field_name == 'Application deadline':
                    index_cols['index_application_deadline'] = value
                elif field_name == 'Execution Timeframe':
                    index_cols['index_execution_timeframe'] = value
                elif field_name == 'Place of Execution':
                    index_cols['index_place_of_execution'] = value
                elif field_name == 'Expiration time':
                    index_cols['expiration_time'] = value  
                else:
                    raise Exception('Unhandled field {0}!'.format(field_name))
            return index_cols

        def _get_item_detail_cols(item_tender_details):
            item_tender_details_sections = item_tender_details.find_all('div', {'class': 'col-md-6'})
            item_detail_cols = {
                'awarded': {
                    'number': '',
                    'name': '',
                    'place_of_execution': '',
                    'execution_timeframe': '',
                    'application_period': '',
                    'opening_date': '',
                    'period': '',
                    'bidders_request': '',
                    'regulation': '',
                    'tender_procedures': '',
                    'subdivision_into_lots': '',
                    'side_offers_allowed': '',
                    'several_main_offers_allowed': '',
                    'cpv_codes': '',
                    'delivery_form': '',
                    'application_deadline': '',
                    'issue_date': '',
                },
                'action': {
                    'number': '',
                    'name': '',
                },
                'contracting_authority': {
                    'name': '',
                    'address': '',
                    'email': '',
                },
                'brief_descripiton': '',
            }
            for section in item_tender_details_sections:
                _section_name = section.find('legend').text.strip()
                if _section_name == 'Awarded':
                    section_key = 'awarded'
                elif _section_name == 'Contracting Authority':
                    section_key = 'contracting_authority'
                elif _section_name == 'Action':
                    section_key = 'action'
                elif _section_name == 'Brief description':
                    section_key = 'brief_description'
                else:
                    if _section_name not in [
                        # will be handeled separately in get_brief_description()
                        'Place of Execution',
                    ]:
                        raise Exception('Unhandled section: {0}!'.format(_section_name))
                trs = section.find_all('tr')
                for tr in trs:
                    tds = tr.find_all('td')
                    _field_name = tds[0].text.strip()
                    value = tds[-1].text.strip()
                    if _field_name == 'Name':
                        key = 'name'
                    elif _field_name == 'Number':
                        key = 'number'
                    elif _field_name == 'Address':
                        key = 'address'
                    elif _field_name == 'Email':
                        key = 'email'
                    elif _field_name == 'Place of Execution':
                        key = 'place_of_execution'
                    elif _field_name == 'Execution Timeframe':
                        key = 'execution_timeframe'
                    elif _field_name == 'Application Period':
                        key = 'application_period'
                    elif _field_name == 'Expiration time':
                        key = 'expiration_time'
                    elif _field_name == 'Opening Date':
                        key = 'opening_date'
                    elif _field_name == 'Award period':
                        key = 'period'
                    elif _field_name == 'Bidders requests':
                        key = 'bidders_request'
                    elif _field_name == 'Regulation':
                        key = 'regulation'
                    elif _field_name == 'Tender Procedures':
                        key = 'tender_procedures'
                    elif _field_name == 'Subdivision into lots':
                        key = 'subdivision_into_lots'
                    elif _field_name == 'Side-offers allowed':
                        key = 'side_offers_allowed'
                    elif _field_name == 'Several main offers allowed':
                        key = 'several_main_offers_allowed'
                    elif _field_name == 'CPV Codes':
                        key = 'cpv_codes'
                    elif _field_name == 'Delivery form':
                        key = 'delivery_form'
                    elif _field_name == 'Application deadline':                  
                        key = 'application_deadline'
                    elif _field_name == 'Issue date':
                        key = 'issue_date'
                    else:
                        if _field_name not in [
                            # optional in some sections
                            'Place of Execution',
                        ]:
                            raise Exception('Unhandled field: {0}!'.format(_field_name))
                    item_detail_cols[section_key][key] = value
            return item_detail_cols

        items = []
        index_soup = BeautifulSoup(index_page_html, "lxml")
        elements_to_parse = index_soup.find_all('ul', {'class': 'stream'})[0].find_all('li')

        for index, element_to_parse in enumerate(elements_to_parse):
            try:
                print()
                print('{0} of {1}'.format(index+1, len(elements_to_parse)))
                item_index_div = element_to_parse.find('div', {'class': 'item'})
                item_index_left_div = item_index_div.find('div', {'class': 'item-left'})
                item_index_cols = item_index_left_div.find_all('div', {'class': 'col-6'})

                index_cols = _get_index_cols(item_index_cols)

                item_id = get_item_id(item_index_left_div)
                index_name=get_index_name(item_index_left_div)
                print(item_id)
                print(index_name)
                item_detailed_page_html = self.get_detailed_item_page_html(item_id=item_id)
                item_detailed_soup = BeautifulSoup(item_detailed_page_html, "lxml")
                item_tender_details = item_detailed_soup.find('div', {'class': 'tender-details'})
                if item_tender_details:
                    item_detail_cols = _get_item_detail_cols(item_tender_details)
                else:
                    print('!!!!!!!!!!')
                    continue


                item = {
                    # Index page fields
                    'item_id': item_id,
                    'index_name': get_index_name(item_index_left_div),
                    'index_description': get_index_description(item_index_left_div),
                    'index_publication_date': get_index_publication_date(item_index_div),
                    # # Columns section
                    'index_application_period': index_cols['index_application_period'],
                    'expiration_time': index_cols['expiration_time'],
                    'index_application_deadline': index_cols['index_application_deadline'],
                    'index_execution_timeframe': index_cols['index_execution_timeframe'],
                    'index_place_of_execution': index_cols['index_place_of_execution'],
                    # Detail page fields
                    # # Awarded section
                    'awarded_number': item_detail_cols['awarded']['number'],
                    'awarded_name': item_detail_cols['awarded']['name'],
                    'awarded_place_of_execution': item_detail_cols['awarded']['place_of_execution'],
                    'awarded_execution_timeframe': item_detail_cols['awarded']['execution_timeframe'],
                    'awarded_application_period': item_detail_cols['awarded']['application_period'],
                    'awarded_opening_date': item_detail_cols['awarded']['opening_date'],
                    'awarded_period': item_detail_cols['awarded']['period'],
                    'awarded_bidders_request': item_detail_cols['awarded']['bidders_request'],
                    # # Action section
                    'action_number': item_detail_cols['action']['number'],
                    'action_name': item_detail_cols['action']['name'],
                    # # Contracting Authority section
                    'contracting_authority_name': item_detail_cols['contracting_authority']['name'],
                    'contracting_authority_address': item_detail_cols['contracting_authority']['address'],
                    'contracting_authority_email': item_detail_cols['contracting_authority']['email'],
                    # Brief description section
                    'brief_description': get_brief_description(item_tender_details),
                }

                items.append(item)
            except Exception as e:
                print(e)
        return items

    def get_detailed_item_page_html(self, item_id):
        item_detailed_page_filename = self.ITEM_DETAILED_PAGE_FILENAME % item_id
        if self.USE_CACHED_ITEM_PAGES and exists(item_detailed_page_filename):
            item_detailed_page_html = self.read_file(item_detailed_page_filename)
        else:
            item_detail_url = '{0}/{1}/'.format(self.INDEX_PAGE_URL, item_id)
            item_detailed_page_html = self.fetch_page_html(item_detail_url)
            time.sleep(self.PAGE_FETCHING_TIMEOUT)
            if self.CACHE_ITEM_PAGES_TO_FILE:
                self.write_to_file(
                    content=item_detailed_page_html,
                    filename=item_detailed_page_filename
                )
        return item_detailed_page_html

    def get_index_page_html(self):
        if self.USE_CACHED_INDEX_PAGE and exists('{0}'.format(self.INDEX_PAGE_FILENAME)):
            index_page_html = self.read_file(filename=self.INDEX_PAGE_FILENAME)
            print('items were extracted from file')
        else:
            if self.HANDLE_INFINITE_SCROLL:
                index_page_html = self.fetch_scrolled_page_html(url=self.INDEX_PAGE_URL)
                print('items were extracted from browser page with scroll simulation')
                if self.CACHE_INDEX_PAGE_TO_FILE:
                    self.write_to_file(content=index_page_html, filename=self.INDEX_PAGE_FILENAME)
                    print('fetched items had been written to file')
            else:
                index_page_html = self.fetch_page_html(self.INDEX_PAGE_URL)
                print('items were extracted from browser page without scroll simulation')
        return index_page_html 

    def run_scraper(self):
        index_page_html = self.get_index_page_html()
        items = self.collect_items(index_page_html=index_page_html)
        dt = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        self.write_items_to_csv_file(
            items=items,
            # fieldnames=Item.get_fielnames(),
            csv_filename=self.CSV_RESULT_FILENAME % dt,
            fieldnames=['item_id',
                        'index_name',
                        'index_description',
                        'index_publication_date',
                        'index_application_period',
                        'expiration_time',
                        'index_application_deadline',
                        'index_execution_timeframe',
                        'index_place_of_execution',
                        'awarded_number',
                        'awarded_name',
                        'awarded_place_of_execution',
                        'awarded_execution_timeframe',
                        'awarded_application_period',
                        'awarded_opening_date',
                        'awarded_period',
                        'awarded_bidders_request',
                        'action_number',
                        'action_name',
                        'contracting_authority_name',
                        'contracting_authority_address',
                        'contracting_authority_email',
                        'brief_description']

        )


if __name__ == '__main__':
    scraper = Scraper()
    scraper.run()
