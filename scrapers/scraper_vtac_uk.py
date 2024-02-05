import json
import math
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, \
    ElementNotInteractableException
from selenium.common.exceptions import TimeoutException
from utils.util import Util


# VTAC UK SCRAPER
class ScraperVtacUk:
    COUNTRY = 'uk'
    WEBSITE_NAME = 'V-TAC UK'
    BRAND_NAME = 'V-TAC'

    DRIVER = None
    logger = None
    BEGIN_SCRAPE_FROM = 0

    PRODUCT_LINKS_CATEGORIES_JSON_PATH = 'data/vtac_uk/LINKS/PRODUCT_LINKS_CATEGORIES.json'

    SPECS_SUBCATEGORIES = ["product-attributes", "product-packaging", "product-features"]

    PRODUCTS_INFO_PATH = 'data/vtac_uk/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH = 'data/vtac_uk/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH = 'data/vtac_uk/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH = 'data/vtac_uk/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH = 'data/vtac_uk/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH = 'data/vtac_uk/NEW/PRODUCT_PDF'

    PRODUCTS_LINKS_PATH = 'data/vtac_uk/LINKS/PRODUCTS_LINKS_UK.json'
    NEW_PRODUCTS_LINKS_PATH = 'data/vtac_uk/LINKS/NEW_PRODUCTS_LINKS_UK.json'

    CATEGORIES_LINKS = [
        'https://www.vtacexports.com/default/led-lighting.html',
        'https://www.vtacexports.com/default/decorative-lighting.html',
        'https://www.vtacexports.com/default/smart-products.html',
        'https://www.vtacexports.com/default/digital-accessories.html',
        'https://www.vtacexports.com/default/electrical.html',
        'https://www.vtacexports.com/default/energy.html',
        'https://www.vtacexports.com/default/new-arrivals.html',
        'https://www.vtacexports.com/default/back-in-stock.html',
        'https://www.vtacexports.com/default/top-products.html'
    ]

    @classmethod
    def instantiate_driver(cls):
        cls.DRIVER = webdriver.Firefox()
        cls.DRIVER.maximize_window()

    @classmethod
    def scrape_item(cls, driver, url, subcategories=None):
        try:
            # Se conecta el driver instanciado a la URL
            driver.get(url)
        except TimeoutException:
            cls.logger.error(f'ERROR extrayendo los datos de {url}. Reintentando...')

            time.sleep(30)
            ScraperVtacUk.scrape_item(driver, url, subcategories)
            return

        subcategories_li_elements = []

        # Agree to cookies
        try:
            cookie_btn = driver.find_element(By.XPATH, "//button[@data-trigger-settings='agree']")
            if cookie_btn.is_displayed():
                cookie_btn.click()
        except NoSuchElementException:
            pass

        for subcat_id in subcategories:
            try:
                subcategories_li_elements += driver.find_elements(By.XPATH, f'//div[@id = "{subcat_id}"]//ul/li')
            except NoSuchElementException:
                continue

        # Diccionario que almacena todos los datos de un artículo
        item = {'url': driver.current_url, 'list_price': 0,
                'imgs': [],
                'website_description': '',
                'videos': [],
                'product_brand_id': cls.BRAND_NAME}

        cls.logger.info(f'BEGINNING EXTRACTION OF: {driver.current_url}')

        # Para cada subcategoria, extraemos sus campos
        for subcat_li in subcategories_li_elements:
            try:
                # <li> que contienen el campo y valor (<span1> campo <span2> valor)
                key_value_spans = subcat_li.find_elements(By.TAG_NAME, 'span')

                # Si el elemento <li> no contiene <span>. <li> es un Feature
                if len(key_value_spans) < 1:
                    raise NoSuchElementException

                # Si el span2 no es un texto plano, se ignora (ejemplo : botón)
                try:
                    if len(key_value_spans) > 1:
                        key_value_spans[1].find_element(By.TAG_NAME, 'a')
                        continue
                except NoSuchElementException:
                    pass

                key = Util.translate_from_to_spanish('en', key_value_spans[0].text)
                value = Util.translate_from_to_spanish('en', key_value_spans[1].text)

                # Guardado de campos y valor en la estructura de datos
                item[str(key).capitalize()] = value
            except NoSuchElementException:
                pass

        # Extracción de la descripción (Features)
        try:
            # Se hace click() sobre el botón de Features para acceder al texto
            driver.find_element(By.ID, 'tab-label-features').click()
            outer_html = driver.find_element(By.XPATH, "//div[@id='product-features']//ul").get_attribute('outerHTML')
            item['website_description'] = f'{Util.translate_from_to_spanish("en", outer_html)}\n'
        except (NoSuchElementException, ElementClickInterceptedException):
            pass

        # Extracción del SKU
        try:
            item['default_code'] = f'{Util.get_sku_from_link_uk(driver)}'
        except NoSuchElementException:
            cls.logger.warning(f'SKIPPING: SKU NOT FOUND {item["url"]}')
            return None

        internal_ref = Util.get_internal_ref_from_sku(item['default_code'])

        if not internal_ref:
            cls.logger.warning(f'SKIPPING: SKU NOT CONVERTED TO INTERNAL REF {item["url"]}')
            return None

        # Extracción del titulo
        item['name'] = Util.translate_from_to_spanish('en',
                                                      driver.find_element(By.XPATH,
                                                                          '//main/div[3]/div/div/section[1]/div/div/div[2]/div[1]/div').text)

        # Formateo del titulo
        item['name'] = f'[{internal_ref}] {item["name"]}'.upper()

        # Extracción de imágenes
        try:
            # Find the image elements and extract their data
            image_div_elements = driver.find_elements(By.XPATH, "//div[@id='main-carousel']/div/div/div")

            for image_div_element in image_div_elements:
                # Check if data-type attr exists. If so, image-element is a VIDEO
                if image_div_element.get_attribute('data-type') is not None:
                    item['videos'].append(image_div_element.get_attribute('data-video-url'))
                else:
                    # If div element does not have attr data-type, it contains an img
                    src = image_div_element.find_element(By.TAG_NAME, 'img').get_attribute('src')
                    item['imgs'].append({'src': src, 'img64': Util.src_to_base64(src)})
        except NoSuchElementException:
            cls.logger.warning('PRODUCT HAS NO IMGS')

        # Reemplazo de campos para ODOO
        if 'Peso bruto (kg)' in item:

            # Temporal fix for 16 getting translated in letters for some reason
            if item['Peso bruto (kg)'] == 'dieciséis':
                item['Peso bruto (kg)'] = '16'

            item['weight'] = float(item['Peso bruto (kg)'].replace(',', '.'))
            del item['Peso bruto (kg)']

        # Scrape UK stock data
        try:
            stockdata_dict = {}

            stock_uls = driver.find_elements(By.XPATH, "//div[@class='columns']/div/div/section[1]/div/div/div[2]/div[4]//ul")

            local_lis = stock_uls[0].find_elements(By.TAG_NAME, 'div')
            global_lis = stock_uls[1].find_elements(By.TAG_NAME, 'div')

            item['almacen2_custom'] = int(str(local_lis[0].text).split(':')[1].replace('pcs', '').replace('-','0').strip())
            item['- Almacén 2'] = f"{item['almacen2_custom']} unidades"

            stockdata_dict['localtransit'] = local_lis[1].text
            stockdata_dict['globaltransit'] = global_lis[1].text
            item['transit'] = 0

            # Sum local and global transit
            for key, value in stockdata_dict.items():
                stockdata_dict[key] = int(str(value).split(':')[1].replace('pcs', '').replace('-','0').strip())

                item['transit'] += stockdata_dict[key]
        except (IndexError, ValueError):
            cls.logger.warning('NO UK STOCK INFO FOUND FOR SKU ' + item['default_code'])

        cls.logger.info(f'EXTRACTED ITEM WITH NAME: {item["name"]}')

        return item

    @classmethod
    def extract_all_links(cls, driver, categories, update=False):
        extracted = []
        # Product links and categories {'link': 'category string'}
        product_links_categories = {}

        for cat in categories:
            try:
                driver.get(cat)
            except TimeoutException:
                cls.logger.error("ERROR navegando a la página. Reintentando...")
                ScraperVtacUk.extract_all_links(driver, categories)
                return

            # Número total de productos por categoría
            product_count = int(driver.find_element(By.XPATH, '//aside//h5').text.split(' ')[0])

            # Número de páginas (Total / 16)
            page_count = math.ceil(product_count / 16)

            for page in range(1, page_count + 1):
                driver.get(f'{cat}?p={page}')

                time.sleep(Util.PRODUCT_LINK_EXTRACTION_DELAY)

                links = driver.find_elements(By.XPATH, "//main//div[@class='column main']/section//form/a")
                links.extend(driver.find_elements(By.XPATH, "//main//div[@class='column main']/section/div/div/div/a"))

                if len(links) < 1:
                    links = driver.find_elements(By.XPATH, '//main//form/a')

                before = len(extracted)

                current_categs = [c.text for c in driver.find_elements(By.XPATH, '/html/body/div[3]/section[1]/div/div/div[1]/div/div/nav/ol//a')[1:]]
                category_string = ''

                for categ in current_categs:
                    category_string += f'{categ} / '

                category_string = category_string[:-3]

                for link in links:
                    href = link.get_attribute('href')
                    extracted.append(href)
                    if href in product_links_categories:
                        product_links_categories[href].append(category_string)
                    else:
                        product_links_categories[href] = [category_string]

                cls.logger.info(f'ADDED: {len(extracted) - before} TOTAL: {len(extracted)} URL: {driver.current_url}')

        Util.dump_to_json(product_links_categories, cls.PRODUCT_LINKS_CATEGORIES_JSON_PATH)

        cls.logger.info(f'EXTRACTED {len(extracted)} LINKS')

        extracted = set(extracted)

        cls.logger.info(f'EXTRACTED {len(extracted)} UNIQUE LINKS')

        if update:
            links_path = ScraperVtacUk.PRODUCTS_LINKS_PATH

            if os.path.exists(links_path):
                with open(links_path, 'r') as file:
                    old_links = set(json.load(file))
                    new_links = extracted - old_links
                    cls.logger.info(f'FOUND {len(new_links)} NEW LINKS')
                    return extracted, new_links

        return extracted, None

    @classmethod
    def count_pdfs_of_link(cls, link):
        time.sleep(Util.PDF_DOWNLOAD_DELAY)

        if ScraperVtacUk.DRIVER.current_url != link:
            ScraperVtacUk.DRIVER.get(link)

        pdf_download_tab_xpath = '//div[@id = \'tab-label-product.downloads\']'

        pdf_elements = []

        offset = 0
        pdfs_to_skip_count = 0

        # Accept cookies
        try:
            ScraperVtacUk.DRIVER.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[2]/button[2]').click()
        except (NoSuchElementException, ElementNotInteractableException):
            pass

        try:
            # Specs tab certificates
            pdf_elements += ScraperVtacUk.DRIVER.find_elements(By.XPATH, "//span[text() = 'Check the certificate']/parent::a")
            offset = len(pdf_elements)
        except NoSuchElementException:
            pass

        try:
            # Downloads tab
            ScraperVtacUk.DRIVER.find_element(By.XPATH, pdf_download_tab_xpath).click()
        except NoSuchElementException:
            pass
        except ElementClickInterceptedException:
            ActionChains(ScraperVtacUk.DRIVER).scroll_by_amount(0, 500).perform()
            time.sleep(0.2)
            ScraperVtacUk.DRIVER.find_element(By.XPATH, pdf_download_tab_xpath).click()

        try:
            pdf_elements += ScraperVtacUk.DRIVER.find_elements(By.XPATH, "//div[@class='attachment-item']/a")
        except NoSuchElementException:
            pass

        for pdf_element in pdf_elements[offset:]:
            spans = pdf_element.find_elements(By.TAG_NAME, "span")
            if len(spans) >= 2:
                name = spans[1].text
                if '(Fiche)' in name or 'Label UK' in name or 'Right Click' in name:
                    pdfs_to_skip_count += 1

        return len(pdf_elements) - pdfs_to_skip_count

    @classmethod
    def download_pdfs_of_sku(cls, driver, sku):
        """
        Downloads PDF from a given URL.

        Parameters:
        driver: Selenium WebDriver instance.
        url (str): URL to download the PDF from.
        sku (str): SKU of the product.

        """
        time.sleep(Util.PDF_DOWNLOAD_DELAY)

        pdf_download_tab_xpath = '//div[@id = \'tab-label-product.downloads\']'

        pdf_elements = []

        # Specs tab certificates
        pdf_elements += driver.find_elements(By.XPATH, "//span[text() = 'Check the certificate']/parent::a")

        # Accept cookies
        try:
            driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[2]/button[2]').click()
        except (NoSuchElementException, ElementNotInteractableException):
            pass

        try:
            time.sleep(0.2)
            # Downloads tab
            driver.find_element(By.XPATH, pdf_download_tab_xpath).click()
        except NoSuchElementException:
            pass
        except ElementClickInterceptedException:
            ActionChains(driver).scroll_by_amount(0, 500).perform()
            time.sleep(0.2)
            driver.find_element(By.XPATH, pdf_download_tab_xpath).click()

        pdf_elements += driver.find_elements(By.XPATH, "//div[@class='attachment-item']/a")

        cls.logger.info(f'Found {len(pdf_elements)} PDFs in SKU {sku}')

        for pdf_element in pdf_elements:
            attachment_display_names = pdf_element.find_elements(By.TAG_NAME, "span")

            if len(attachment_display_names) >= 2:
                attachment_name = attachment_display_names[1].text
            else:
                attachment_name = ""

            if '(Fiche)' in attachment_name or 'Label UK' in attachment_name or 'Right Click' in attachment_name:
                cls.logger.info(f'SKIPPING UNWANTED PDF: {attachment_name} of SKU {sku}')
                continue

            url = pdf_element.get_attribute('href')
            response = requests.get(url)

            # Get the original file name if possible to extract the extension
            content_disposition = response.headers.get('content-disposition')
            if content_disposition:
                filename = content_disposition.split('filename=')[-1].strip('"')
            else:
                # Fallback to extracting the filename from URL if no content-disposition header
                filename = os.path.basename(url)

            if not attachment_name:
                attachment_name = filename.split('.')[0]

            file_extension = filename.split('.')[-1]

            if file_extension != 'pdf' and file_extension != 'png':
                continue

            nested_dir = f'{ScraperVtacUk.PRODUCTS_PDF_PATH}/{sku}'
            os.makedirs(nested_dir, exist_ok=True)

            attachment_name = Util.attachment_naming_replacements(attachment_name, 'uk')

            with open(f'{nested_dir}/{attachment_name}.{file_extension}', 'wb') as file:
                file.write(response.content)

        return len(pdf_elements)

    @classmethod
    def download_specsheet_of_sku(cls, driver, sku, skip_existing=False):
        nested_dir = f'data/vtac_uk/SPEC_SHEETS/{sku}'

        try:

            if not os.path.exists(nested_dir):
                os.makedirs(nested_dir, exist_ok=False)
            elif skip_existing:
                print(f'SKIPPING: Spec sheet of SKU {sku} already exists')
                return

            spec_sheet_path = '/html/body/div[3]/main/div[3]/div/div/section[1]/div/div/div[2]/div[3]/div/div[1]/div[2]/div[2]/div/div[2]/div/a'

            specsheet_anchor = driver.find_element(By.XPATH, spec_sheet_path)
            print(f'Found the specsheet of SKU {sku}')

            name = f'{sku}.pdf'

            response = requests.get(specsheet_anchor.get_attribute('href'))

            with open(f'{nested_dir}/{name}', 'wb') as file:
                file.write(response.content)
        except NoSuchElementException:
            os.remove(nested_dir)
            print(f'SKIPPING: Could not download spec_sheet of SKU -> {sku}')
