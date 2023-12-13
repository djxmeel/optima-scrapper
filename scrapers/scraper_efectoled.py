import json
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from utils.util import Util


# EFECTOLED SCRAPER
class ScraperEfectoLed:
    DRIVER = None
    logger = None
    BEGIN_SCRAPE_FROM = 0

    PRODUCT_LINKS_CATEGORIES_JSON_PATH = 'data/efectoled/LINKS/PRODUCT_LINKS_CATEGORIES.json'

    SPECS_SUBCATEGORIES = ()

    PRODUCTS_INFO_PATH = 'data/efectoled/PROD/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH = 'data/efectoled/PROD/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH = 'data/efectoled/PROD/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH = 'data/efectoled/PROD/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH = 'data/efectoled/PROD/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH = 'data/efectoled/PROD/NEW/PRODUCT_PDF'

    PRODUCTS_INFO_PATH_TEST = 'data/efectoled/TEST/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH_TEST = 'data/efectoled/TEST/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH_TEST = 'data/efectoled/TEST/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH_TEST = 'data/efectoled/TEST/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH_TEST = 'data/efectoled/TEST/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH_TEST = 'data/efectoled/TEST/NEW/PRODUCT_PDF'

    PRODUCTS_LINKS_PATH = 'data/efectoled/LINKS/PRODUCTS_LINKS_EFECTOLED.json'
    NEW_PRODUCTS_LINKS_PATH = 'data/efectoled/LINKS/NEW_PRODUCTS_LINKS_EFECTOLED.json'

    CATEGORIES_LINKS = (
        'https://www.efectoled.com/es/6-comprar-bombillas-lamparas-led',
        'https://www.efectoled.com/es/7-comprar-tubos-pantallas-y-lineal-led',
        'https://www.efectoled.com/es/content/328-iluminacion-interior',
        'https://www.efectoled.com/es/11-comprar-downlight-led',
        'https://www.efectoled.com/es/8-comprar-paneles-led',
        'https://www.efectoled.com/es/10-comprar-tiras-y-neon-led',
        'https://www.efectoled.com/es/content/324-iluminacion-exterior',
        'https://www.efectoled.com/es/content/311-home-deco',
        'https://www.efectoled.com/es/11051-comprar-espacios',
        'https://www.efectoled.com/es/11047-comprar-estilos',
        'https://www.efectoled.com/es/11047-comprar-estilos',
    )

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
            time.sleep(5)
            ScraperEfectoLed.scrape_item(driver, url)
            return

        name_xpath = "//h3[@itemprop='name']"
        keys_values_xpath = "//div[@class='product-field product-field-type-S']"

        # Diccionario que almacena todos los datos de un artículo
        item = {'url': driver.current_url, 'list_price': 0, 'imgs': [], 'icons': [], 'website_description': '', 'videos': []}

        cls.logger.info(f'BEGINNING EXTRACTION OF: {driver.current_url}')

        # Extracción de los campos
        keys_values = driver.find_elements(By.XPATH, keys_values_xpath)

        for key_value in keys_values:
            key = key_value.find_element(By.TAG_NAME, "strong")
            try:
                value = key_value.find_element(By.TAG_NAME, "div")
            except NoSuchElementException:
                cls.logger.warning(f'Field {key.text} has no value.')
                item[key.text] = ''
                continue

            item[key.text] = value.text

        # Extracción y formateo del SKU
        if 'Código de orden' in item.keys():
            item['Sku'] = f'{item["Código de orden"]}'
            del item['Código de orden']
        else:
            item['Sku'] = f'{Util.get_sku_from_link(driver, driver.current_url, "ES")}'

        # Extracción de imágenes
        try:
            # Find the image elements and extract their data
            image_elements = driver.find_elements(By.XPATH, "//a[@rel='vm-additional-images']")

            for index, image_element in enumerate(image_elements):
                src = image_element.get_attribute('href')
                item['imgs'].append({'src': src, 'img64': Util.src_to_base64(src)})
        except NoSuchElementException:
            cls.logger.warning('PRODUCT HAS NO IMGS')

        # Extracción de video
        try:
            video_element = driver.find_element(By.XPATH, "//div[@uk-lightbox='']/a")
            item['videos'].append(video_element.get_attribute('href'))
        except NoSuchElementException:
            pass

        # Extracción de la descripción del producto CON outerHTML
        try:
            # Check if an <h4> exists to determine whether a description exists
            driver.find_element(By.XPATH, "//div[@class='product-description']/h4")
            # Removing "Contáctenos" button before saving
            item['website_description'] = driver.find_element(By.XPATH, "//div[@class='product-description']").get_attribute('outerHTML').replace('<div><a class="uk-button uk-button-default" href="https://v-tac.es/contáctenos">Contáctenos</a></div>', '')

        except NoSuchElementException:
            pass

        # Extracción del título
        item['name'] = f'[{item["Sku"]}] {driver.find_element(By.XPATH, name_xpath).text}'

        # Uso de los campos de ODOO para el volumen y el peso si están disponibles
        if 'Volumen del artículo' in item.keys():
            item['volume'] = float(item['Volumen del artículo'].replace(',', '.'))
            del item['Volumen del artículo']
        if 'Peso del artículo' in item.keys():
            item['weight'] = float(item['Peso del artículo'].replace(',', '.').split(' ')[0].replace('kg', ''))
            del item['Peso del artículo']

        cls.logger.info(f'EXTRACTED ITEM WITH NAME: {item["name"].encode("utf-8")}')

        return item

    @classmethod
    def extract_all_links(cls, driver, categories, update=False):
        extracted = set()
        for cat in categories:
            try:
                driver.get(cat)
            except TimeoutException:
                cls.logger.error("ERROR navegando a la página. Reintentando...")
                ScraperEfectoLed.extract_all_links(driver, categories, update)
                return

            inner_categories_links = [cat.get_attribute("href") for cat in driver.find_elements(By.XPATH,
                                                                                                "/html/body/div[1]/div/section[3]/div/main/div/div[2]/div[2]/div/section//h4//a")]

            for inner_cat in inner_categories_links:
                driver.get(f'{inner_cat}?limit=9999')
                links = driver.find_elements(By.XPATH, "//div[@id='bd_results']//img/parent::a")
                time.sleep(Util.PRODUCT_LINK_EXTRACTION_DELAY)

                before = len(extracted)

                for link in links:
                    extracted.add(link.get_attribute('href'))

                cls.logger.info(f'ADDED: {len(extracted) - before} TOTAL: {len(extracted)} URL: {driver.current_url}')

        if update:
            links_path = ScraperEfectoLed.PRODUCTS_LINKS_PATH

            if os.path.exists(links_path):
                with open(links_path, 'r') as file:
                    old_links = set(json.load(file))
                    new_links = extracted - old_links
                    return extracted, new_links

        return extracted, None

    @classmethod
    def count_pdfs_of_link(cls, link):
        time.sleep(Util.PDF_DOWNLOAD_DELAY)

        if ScraperEfectoLed.DRIVER.current_url != link:
            ScraperEfectoLed.DRIVER.get(link)

        attachments_xpath = '//div[@class="downloads"]//a'
        pdf_elements = []

        try:
            # Get the <a> elements
            pdf_elements = ScraperEfectoLed.DRIVER.find_elements(By.XPATH, attachments_xpath)
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

        attachments_xpath = '//div[@class="downloads"]//a'

        # Get the <a> elements
        pdf_elements = driver.find_elements(By.XPATH, attachments_xpath)

        cls.logger.info(f'Found {len(pdf_elements)} attachments in SKU {sku}')

        for pdf_element in pdf_elements:
            url = pdf_element.get_attribute('href')
            response = requests.get(url)

            nested_dir = f'{ScraperEfectoLed.PRODUCTS_PDF_PATH}/{sku}'
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
