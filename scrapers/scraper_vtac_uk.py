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

    DRIVER = None
    logger = None
    BEGIN_SCRAPE_FROM = 0

    SPECS_SUBCATEGORIES = ["product-attributes", "product-packaging", "product-features"]

    CATEGORIES_LINKS = [
        'https://www.vtacexports.com/default/digital-accessories.html',
        'https://www.vtacexports.com/default/led-lighting.html',
        'https://www.vtacexports.com/default/decorative-lighting.html',
        'https://www.vtacexports.com/default/smart-products.html',
        'https://www.vtacexports.com/default/electrical.html'
    ]

    PRODUCTS_INFO_PATH = 'data/vtac_uk/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH = 'data/vtac_uk/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH = 'data/vtac_uk/PRODUCT_PDF'

    PRODUCTS_LINKS_PATH = 'data/vtac_uk/LINKS/PRODUCTS_LINKS_UK.json'
    NEW_PRODUCTS_LINKS_PATH = 'data/vtac_uk/LINKS/NEW_PRODUCTS_LINKS_UK.json'

    PRODUCTS_FIELDS_JSON_PATH = 'data/vtac_uk/FIELDS/PRODUCTS_FIELDS.json'
    PRODUCTS_FIELDS_EXCEL_PATH = 'data/vtac_uk/FIELDS/DISTINCT_FIELDS_EXCEL.xlsx'

    PRODUCTS_EXAMPLE_FIELDS_JSON_PATH = 'data/vtac_uk/FIELDS/PRODUCTS_FIELDS_EXAMPLES.json'
    PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH = 'data/vtac_uk/FIELDS/DISTINCT_FIELDS_EXAMPLES_EXCEL.xlsx'

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
        item = {'url': driver.current_url, 'list_price': 0, 'imgs': [], 'icons': [], 'website_description': '', 'videos': []}

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
            item['website_description'] = f'{Util.translate_from_to_spanish("en",outer_html)}\n'
        except NoSuchElementException:
            pass

        # Extracción del SKU
        try:
            item['Sku'] = f'{Util.get_sku_from_link_uk(driver)}'
        except NoSuchElementException:
            cls.logger.warning('SKU NO ENCONTRADO')

        try:
            item['default_code'] = Util.get_internal_ref_from_sku(item['Sku'])
        except:
            return None

        # Extracción del precio
        try:
            item['list_price'] = driver.find_element(By.XPATH,
                                                     f'/html/body/div[3]/main/div[4]/div/div/section[1]/div/div/div[2]/div[3]/div/div/div[2]/div[1]/span').text
            if len(item['list_price']) > 1:
                item['list_price'] = float(item['list_price'].replace('£', '').replace(',', ''))
        except NoSuchElementException:
            cls.logger.warning('PRECIO NO ENCONTRADO')

        # Extracción del titulo
        item['name'] = Util.translate_from_to_spanish('en',
                                                      driver.find_element(By.XPATH,
                                                                          '/html/body/div[3]/main/div[4]/div/div/section[1]/div/div/div[2]/div[1]/div').text)

        # Formateo del titulo
        item['name'] = f'[{item["default_code"]}] {item["name"]}'

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
        try:
            icons = driver.find_elements(By.XPATH,
                                         '/html/body/div[3]/main/div[4]/div/div/section[1]/div/div/div[1]/div[2]//*[name()="svg"]')

            for icon in icons:
                item['icons'].append(Util.svg_to_base64(icon.get_attribute('outerHTML'), ScraperVtacUk.logger))
        except NoSuchElementException:
            cls.logger.warning('PRODUCT HAS NO ICONS')

        # Reemplazo de campos para ODOO
        if 'Peso bruto (kg)' in item:
            item['weight'] = float(item['Peso bruto (kg)'].replace(',', '.'))
            del item['Peso bruto (kg)']

        cls.logger.info(f'EXTRACTED ITEM WITH NAME: {item["name"]}')

        return item

    @classmethod
    def extract_all_links(cls, driver, categories, update=False):
        extracted = set()

        for cat in categories:
            try:
                driver.get(cat)
            except TimeoutException:
                cls.logger.error("ERROR navegando a la página. Reintentando...")
                ScraperVtacUk.extract_all_links(driver, categories)
                return

            # Número total de productos por categoría
            product_count = int(
                driver.find_element(By.XPATH, '//*[@id="maincontent"]/div[4]/div[1]/h5').text.split(' ')[0])

            # Número de páginas (Total / 16)
            page_count = math.ceil(product_count / 16)

            for page in range(1, page_count + 1):
                driver.get(f'{cat}?p={page}')

                time.sleep(Util.PRODUCT_LINK_EXTRACTION_DELAY)

                links = driver.find_elements(By.XPATH,
                                             '/html/body/div[3]/main/div[4]/div[2]/section/div[2]/div//form/a')

                before = len(extracted)

                for link in links:
                    extracted.add(link.get_attribute('href'))

                cls.logger.info(f'ADDED: {len(extracted) - before} TOTAL: {len(extracted)} URL: {driver.current_url}')

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
