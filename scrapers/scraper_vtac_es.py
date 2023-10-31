import json
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from utils.util import Util


# VTAC ES SCRAPER
class ScraperVtacSpain:
    COUNTRY = 'es'

    DRIVER = None
    logger = None
    BEGIN_SCRAPE_FROM = 0

    PRODUCT_LINKS_CATEGORIES_JSON_PATH = 'data/vtac_spain/LINKS/PRODUCT_LINKS_CATEGORIES.json'

    SPECS_SUBCATEGORIES = ()

    PRODUCTS_INFO_PATH = 'data/vtac_spain/PROD/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH = 'data/vtac_spain/PROD/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH = 'data/vtac_spain/PROD/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH = 'data/vtac_spain/PROD/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH = 'data/vtac_spain/PROD/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH = 'data/vtac_spain/PROD/NEW/PRODUCT_PDF'

    PRODUCTS_INFO_PATH_TEST= 'data/vtac_spain/TEST/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH_TEST = 'data/vtac_spain/TEST/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH_TEST = 'data/vtac_spain/TEST/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH_TEST = 'data/vtac_spain/TEST/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH_TEST = 'data/vtac_spain/TEST/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH_TEST = 'data/vtac_spain/TEST/NEW/PRODUCT_PDF'

    PRODUCTS_LINKS_PATH = 'data/vtac_spain/LINKS/PRODUCTS_LINKS_ES.json'
    NEW_PRODUCTS_LINKS_PATH = 'data/vtac_spain/LINKS/NEW_PRODUCTS_LINKS_ES.json'

    PRODUCTS_FIELDS_JSON_PATH = 'data/vtac_spain/FIELDS/PRODUCTS_FIELDS.json'
    PRODUCTS_FIELDS_EXCEL_PATH = 'data/vtac_spain/FIELDS/DISTINCT_FIELDS_EXCEL.xlsx'

    PRODUCTS_EXAMPLE_FIELDS_JSON_PATH = 'data/vtac_spain/FIELDS/PRODUCTS_FIELDS_EXAMPLES.json'
    PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH = 'data/vtac_spain/FIELDS/DISTINCT_FIELDS_EXAMPLES_EXCEL.xlsx'

    CATEGORIES_LINKS = (
        'https://v-tac.es/sistemas-solares.html',
        'https://v-tac.es/iluminaci%C3%B3n.html',
        'https://v-tac.es/smart-digital.html',
        'https://v-tac.es/el%C3%A9ctrico.html',
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
            ScraperVtacSpain.scrape_item(driver, url)
            return

        name_xpath = "//h3[@itemprop='name']"
        keys_values_xpath = "//div[@class='product-field product-field-type-S']"
        graph_dimensions_xpath = "//img[@alt = 'Dimensions']"

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
                continue

            item[str(key.text).capitalize()] = value.text

        # Extracción y formateo del SKU
        if 'Código de orden' in item.keys():
            item['default_code'] = f'{item["Código de orden"]}'
            del item['Código de orden']
        else:
            item['default_code'] = f'{Util.get_sku_from_link(driver, driver.current_url, "ES")}'

        # Extracción de las dimensiones gráficas
        try:
            graph_dimensions_src = driver.find_element(By.XPATH, graph_dimensions_xpath).get_attribute('src')
            item['imgs'].append({
                'src': graph_dimensions_src,
                'img64': Util.src_to_base64(graph_dimensions_src)
            })
        except NoSuchElementException:
            pass

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

        internal_ref = Util.get_internal_ref_from_sku(item['default_code'])

        # If internal_ref is None, it's SKU contains letters (Not V-TAC)
        if not internal_ref:
            return None

        # Extracción del título
        item['name'] = f'[{internal_ref}] {driver.find_element(By.XPATH, name_xpath).text}'

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
        extracted = []
        for cat in categories:
            try:
                driver.get(cat)
            except TimeoutException:
                cls.logger.error("ERROR navegando a la página. Reintentando...")
                ScraperVtacSpain.extract_all_links(driver, categories, update)
                return

            inner_categories_links = [cat.get_attribute("href") for cat in driver.find_elements(By.XPATH,
                                                                                                "/html/body/div[1]/div/section[3]/div/main/div/div[2]/div[2]/div/section//h4//a")]

            for inner_cat in inner_categories_links:
                driver.get(f'{inner_cat}?limit=9999')
                links = driver.find_elements(By.XPATH, "//div[@id='bd_results']//img/parent::a")
                time.sleep(Util.PRODUCT_LINK_EXTRACTION_DELAY)

                before = len(extracted)

                for link in links:
                    extracted.append(link.get_attribute('href'))

                cls.logger.info(f'ADDED: {len(extracted) - before} TOTAL: {len(extracted)} URL: {driver.current_url}')

        cls.logger.info(f'EXTRACTED {len(extracted)} LINKS')

        extracted = set(extracted)

        cls.logger.info(f'EXTRACTED {len(extracted)} UNIQUE LINKS')

        if update:
            links_path = ScraperVtacSpain.PRODUCTS_LINKS_PATH

            if os.path.exists(links_path):
                with open(links_path, 'r') as file:
                    old_links = set(json.load(file))
                    new_links = extracted - old_links
                    return extracted, new_links

        return extracted, None

    @classmethod
    def count_pdfs_of_link(cls, link):
        time.sleep(Util.PDF_DOWNLOAD_DELAY)

        if ScraperVtacSpain.DRIVER.current_url != link:
            ScraperVtacSpain.DRIVER.get(link)

        attachments_xpath = '//div[@class="downloads"]//a'
        pdf_elements = []

        try:
            # Get the <a> elements
            pdf_elements = ScraperVtacSpain.DRIVER.find_elements(By.XPATH, attachments_xpath)
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

            nested_dir = f'{ScraperVtacSpain.PRODUCTS_PDF_PATH}/{sku}'
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

    @classmethod
    def get_internal_category(cls, link):
        # Extracción de las categorías del producto
        cls.DRIVER.get(link)
        categories_crumbs = cls.DRIVER.find_elements(By.CLASS_NAME, "breadcrumb-item")
        categories = ""

        # Ignore last crumb (product name)
        for crumb in categories_crumbs[:-1]:
            categories += f'{crumb.text} / '

        return categories[:-2].strip()

    @classmethod
    def get_duplicate_product_links(cls, file_path, base_link):
        with open(file_path, 'r') as f:
            data = json.load(f)

        substring = base_link.split('/')[-1]

        links = []

        for link in data:
            if substring in link:
                print('FOUND DUPLICATE ->', link)
                links.append(link)

        return links
