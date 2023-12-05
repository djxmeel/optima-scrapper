import json
import math
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
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

    PRODUCTS_INFO_PATH = 'data/vtac_uk/PROD/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH = 'data/vtac_uk/PROD/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH = 'data/vtac_uk/PROD/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH = 'data/vtac_uk/PROD/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH = 'data/vtac_uk/PROD/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH = 'data/vtac_uk/PROD/NEW/PRODUCT_PDF'

    PRODUCTS_INFO_PATH_TEST = 'data/vtac_uk/TEST/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH_TEST = 'data/vtac_uk/TEST/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH_TEST = 'data/vtac_uk/TEST/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH_TEST = 'data/vtac_uk/TEST/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH_TEST = 'data/vtac_uk/TEST/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH_TEST = 'data/vtac_uk/TEST/NEW/PRODUCT_PDF'

    PRODUCTS_LINKS_PATH = 'data/vtac_uk/LINKS/PRODUCTS_LINKS_UK.json'
    NEW_PRODUCTS_LINKS_PATH = 'data/vtac_uk/LINKS/NEW_PRODUCTS_LINKS_UK.json'

    PRODUCTS_FIELDS_JSON_PATH = 'data/vtac_uk/FIELDS/PRODUCTS_FIELDS.json'
    PRODUCTS_FIELDS_EXCEL_PATH = 'data/vtac_uk/FIELDS/DISTINCT_FIELDS_EXCEL.xlsx'

    PRODUCTS_EXAMPLE_FIELDS_JSON_PATH = 'data/vtac_uk/FIELDS/PRODUCTS_FIELDS_EXAMPLES.json'
    PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH = 'data/vtac_uk/FIELDS/DISTINCT_FIELDS_EXAMPLES_EXCEL.xlsx'

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

    OOS_MESSAGE = Util.load_json(Util.OOS_MESSAGES_PATH)[BRAND_NAME]

    @classmethod
    def instantiate_driver(cls):
        cls.DRIVER = webdriver.Firefox()

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
                'imgs': [], 'icons': [],
                'website_description': '',
                'videos': [],
                'Stock europeo': '0 unidades (Disponible en un plazo de 5 a 9 días hábiles)',
                'invoice_policy': 'delivery',
                'detailed_type': 'product',
                'show_availability': True,
                'allow_out_of_stock_order': True,
                'available_threshold': 100000,
                'out_of_stock_message': cls.OOS_MESSAGE}

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
        except NoSuchElementException:
            pass

        # Extracción del SKU
        try:
            item['default_code'] = f'{Util.get_sku_from_link_uk(driver)}'
        except NoSuchElementException:
            cls.logger.warning(f'SKIPPING: SKU NOT FOUND {item["url"]}')
            return None

        internal_ref = Util.get_internal_ref_from_sku(item['default_code'])

        if not internal_ref:
            return None

        # Extracción del titulo
        item['name'] = Util.translate_from_to_spanish('en',
                                                      driver.find_element(By.XPATH,
                                                                          '//main/div[3]/div/div/section[1]/div/div/div[2]/div[1]/div').text).upper()

        # Formateo del titulo
        item['name'] = f'[{internal_ref}] {item["name"]}'

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

        # Extracción de iconos
        icons = driver.find_elements(By.XPATH,
                                     '//main/div[3]/div/div/section[1]/div/div/div[1]/div[2]//*[name()="svg"]')

        for icon in icons:
            item['icons'].append(Util.svg_to_base64(icon.get_attribute('outerHTML'), ScraperVtacUk.logger))

        if not icons:
            cls.logger.warning('PRODUCT HAS NO ICONS')

        # Reemplazo de campos para ODOO
        if 'Peso bruto (kg)' in item:
            item['weight'] = float(item['Peso bruto (kg)'].replace(',', '.'))
            del item['Peso bruto (kg)']

        # Hardcoded fields
        item['product_brand_id'] = cls.BRAND_NAME

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
            product_count = int(driver.find_element(By.XPATH, '//aside/h5').text.split(' ')[0])

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
                    return extracted, new_links

        return extracted, None

    @classmethod
    def count_pdfs_of_link(cls, link):
        time.sleep(Util.PDF_DOWNLOAD_DELAY)

        if ScraperVtacUk.DRIVER.current_url != link:
            ScraperVtacUk.DRIVER.get(link)

        pdf_download_tab_xpath = '//div[@id = \'tab-label-product.downloads\']'

        pdf_elements = []

        try:
            # Specs tab certificates
            pdf_elements += ScraperVtacUk.DRIVER.find_elements(By.XPATH, "//span[text() = 'Check the certificate']/parent::a")
        except NoSuchElementException:
            pass

        try:
            # Downloads tab
            ScraperVtacUk.DRIVER.find_element(By.XPATH, pdf_download_tab_xpath).click()
        except NoSuchElementException:
            pass

        try:
            pdf_elements += ScraperVtacUk.DRIVER.find_elements(By.XPATH, "//div[@class='attachment-item']/a")
        except NoSuchElementException:
            pass

        return len(pdf_elements)

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

        try:
            # Specs tab certificates
            pdf_elements += driver.find_elements(By.XPATH, "//span[text() = 'Check the certificate']/parent::a")
        except NoSuchElementException:
            pass

        try:
            # Downloads tab
            driver.find_element(By.XPATH, pdf_download_tab_xpath).click()
        except NoSuchElementException:
            pass

        try:
            pdf_elements += driver.find_elements(By.XPATH, "//div[@class='attachment-item']/a")
        except NoSuchElementException:
            pass

        cls.logger.info(f'Found {len(pdf_elements)} PDFs in SKU {sku}')

        for pdf_element in pdf_elements:
            url = pdf_element.get_attribute('href')
            response = requests.get(url)

            nested_dir = f'{ScraperVtacUk.PRODUCTS_PDF_PATH}/{sku}'
            os.makedirs(nested_dir, exist_ok=True)

            # Get the original file name if possible
            content_disposition = response.headers.get('content-disposition')
            if content_disposition:
                filename = content_disposition.split('filename=')[-1].strip('"')
            else:
                # Fallback to extracting the filename from URL if no content-disposition header
                filename = os.path.basename(url)

            filename = filename.replace('%20', '_')

            with open(f'{nested_dir}/{filename}', 'wb') as file:
                file.write(response.content)

        return len(pdf_elements)
