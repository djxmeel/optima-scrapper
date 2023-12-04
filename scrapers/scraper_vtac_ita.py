import json
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from utils.util import Util


# VTAC ITALIA SCRAPER
class ScraperVtacItalia:
    COUNTRY = 'ita'
    WEBSITE_NAME = 'V-TAC Italia'
    BRAND_NAME = 'V-TAC'

    DRIVER = None
    logger = None
    BEGIN_SCRAPE_FROM = 0

    PRODUCT_LINKS_CATEGORIES_JSON_PATH = 'data/vtac_italia/LINKS/PRODUCT_LINKS_CATEGORIES.json'

    SPECS_SUBCATEGORIES = ("Specifiche tecniche", "Packaging")

    PRODUCTS_INFO_PATH = 'data/vtac_italia/PROD/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH = 'data/vtac_italia/PROD/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH = 'data/vtac_italia/PROD/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH = 'data/vtac_italia/PROD/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH = 'data/vtac_italia/PROD/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH = 'data/vtac_italia/PROD/NEW/PRODUCT_PDF'

    PRODUCTS_INFO_PATH_TEST = 'data/vtac_italia/TEST/PRODUCT_INFO'
    PRODUCTS_MEDIA_PATH_TEST = 'data/vtac_italia/TEST/PRODUCT_MEDIA'
    PRODUCTS_PDF_PATH_TEST = 'data/vtac_italia/TEST/PRODUCT_PDF'

    NEW_PRODUCTS_INFO_PATH_TEST = 'data/vtac_italia/TEST/NEW/PRODUCT_INFO'
    NEW_PRODUCTS_MEDIA_PATH_TEST = 'data/vtac_italia/TEST/NEW/PRODUCT_MEDIA'
    NEW_PRODUCTS_PDF_PATH_TEST = 'data/vtac_italia/TEST/NEW/PRODUCT_PDF'

    PRODUCTS_LINKS_PATH = 'data/vtac_italia/LINKS/PRODUCTS_LINKS_ITA.json'
    NEW_PRODUCTS_LINKS_PATH = 'data/vtac_italia/LINKS/NEW_PRODUCTS_LINKS_ITA.json'

    PRODUCTS_FIELDS_JSON_PATH = 'data/vtac_italia/FIELDS/PRODUCTS_FIELDS.json'
    PRODUCTS_FIELDS_EXCEL_PATH = 'data/vtac_italia/FIELDS/DISTINCT_FIELDS_EXCEL.xlsx'

    PRODUCTS_EXAMPLE_FIELDS_JSON_PATH = 'data/vtac_italia/FIELDS/PRODUCTS_FIELDS_EXAMPLES.json'
    PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH = 'data/vtac_italia/FIELDS/DISTINCT_FIELDS_EXAMPLES_EXCEL.xlsx'

    CATEGORIES_LINKS = (
        'https://led-italia.it/prodotti/M4E-fotovoltaico',
        'https://led-italia.it/prodotti/M54-illuminazione-led',
        'https://led-italia.it/prodotti/M68-elettronica-di-consumo'
    )

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
            time.sleep(5)
            ScraperVtacItalia.scrape_item(driver, url, subcategories)
            return

        subcategories_elements = []

        try:
            for subcat in subcategories:
                subcategories_elements.append(driver.find_element(By.XPATH, f'//h4[text() = \'{subcat}\']/parent::div'))
        except NoSuchElementException:
            cls.logger.error(f'Enlace de producto no encontrado {url}.')
            return None

        # Diccionario que almacena todos los datos de un artículo
        item = {'url': driver.current_url, 'accesorios': [], 'list_price': 0, 'videos': [],
                'website_description': '',
                'imgs': [], 'icons': [],
                'Stock europeo': '0 unidades (Disponible en un plazo de 5 a 9 días hábiles)',
                'invoice_policy': 'delivery',
                'detailed_type': 'product',
                'show_availability': True,
                'allow_out_of_stock_order': True,
                'available_threshold': 100000,
                'out_of_stock_message': cls.OOS_MESSAGE}

        cls.logger.info(f'BEGINNING EXTRACTION OF: {driver.current_url}')

        # Extracción de los enlaces de videos
        iframes = driver.find_elements(By.XPATH, '//main//iframe')

        for iframe in iframes:
            item['videos'].append(iframe.get_attribute('src'))

        # Extracción del kit al campo accesorios
        try:
            kit_anchor = driver.find_elements(By.XPATH, f'//h4[text() = \'Il kit comprende\']/parent::div//a')

            for anchor in kit_anchor:
                kit_span = anchor.find_element(By.TAG_NAME, 'span')

                kit_info = {'link': anchor.get_attribute('href'),
                            'default_code': kit_span.find_element(By.TAG_NAME, 'span').text,
                            'cantidad': kit_span.text.split('x')[0]
                            }

                item['accesorios'].append(kit_info)

        except NoSuchElementException:
            cls.logger.warning('EL ARTICULO NO TIENE KIT')

        # Extracción de los accesorios
        try:
            acces_li_tags = driver.find_elements(By.XPATH, f'//h4[text() = \'Accessori inclusi\']/parent::div//ul/li')

            for li in acces_li_tags:
                acces_cantidad = li.find_element(By.TAG_NAME, 'span')
                acces_anchor = li.find_element(By.TAG_NAME, 'a')

                acces_info = {'link': acces_anchor.get_attribute('href'),
                              'default_code': acces_anchor.find_element(By.TAG_NAME, 'b').text,
                              'cantidad': acces_cantidad.text.split('x')[0]
                              }

                item['accesorios'].append(acces_info)

        except NoSuchElementException:
            cls.logger.warning('EL ARTICULO NO TIENE ACCESORIOS')

        # Comprobacion de la existencia de una descripcion (Maggiori informazioni)
        try:
            desc_outer_html = driver.find_element(By.XPATH,
                                                    f'//h4[text() = \'Maggiori informazioni\']/parent::div/div').get_attribute(
                'outerHTML')

            item['website_description'] = Util.translate_from_to_spanish('it', desc_outer_html)
        except NoSuchElementException:
            pass

        # Para cada subcategoria, extraemos sus campos
        for subcat in subcategories_elements:
            # Divs que contienen el campo y valor (<b> Campo | <span> Valor)
            fields = subcat.find_element(By.TAG_NAME, 'div') \
                .find_elements(By.TAG_NAME, 'div')

            # Guardado de campos y valor en la estructura de datos
            for field in fields:
                key = Util.translate_from_to_spanish('it', field.find_element(By.TAG_NAME, 'b').text)

                item[str(key).capitalize()] = Util.translate_from_to_spanish('it', field.find_element(By.TAG_NAME, 'span').text)

            # Uso de los campos de ODOO para el volumen y el peso si están disponibles
            if 'Volume' in item:
                item['volume'] = float(item['Volume'].replace(',', '.').replace('m³', ''))
                del item['Volume']
            if 'Peso' in item:
                item['weight'] = float(item['Peso'].lower().replace(',', '.').replace('kg', ''))
                del item['Peso']

        internal_ref = Util.get_internal_ref_from_sku(item['Sku'])

        if not internal_ref:
            return None

        item['default_code'] = item['Sku']
        del item['Sku']

        # Extracción del titulo
        item['name'] = Util.translate_from_to_spanish('it',
                                                      driver.find_element(By.XPATH,
                                                                          '/html/body/main/div[1]/div/div[2]/div[2]/div[1]/h2').text).upper()

        # Extracción de iconos
        try:
            icons = driver.find_elements(By.XPATH, '/html/body/main/div[1]/div/div[2]/div[2]/div[4]/div[2]/img')

            # Mapeo de icons a una lista de sus base64
            item['icons'] = [Util.src_to_base64(icon.get_attribute('src')) for icon in icons]
        except NoSuchElementException:
            cls.logger.warning('PRODUCT HAS NO ICONS')

        # Extracción de imágenes
        try:
            # Find the image elements and extract their data
            image_elements = driver.find_element(By.ID, 'images-slider-list') \
                .find_elements(By.TAG_NAME, 'img')

            for index, image_element in enumerate(image_elements):
                src = image_element.get_attribute('src')
                item['imgs'].append({'src': src, 'img64': Util.src_to_base64(src)})
        except NoSuchElementException:
            cls.logger.warning('PRODUCT HAS NO IMGS')

        # Formateo del titulo
        item['name'] = f'[{internal_ref}] {item["name"]}'

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
                ScraperVtacItalia.extract_all_links(driver, categories)
                return

            item_subcats = driver.find_elements(By.XPATH, '/html/body/main/div[1]/div/a')

            item_subcats_links = [link.get_attribute('href') for link in item_subcats]

            item_subcats_strings = [element.find_element(By.XPATH, 'div[2]').text for element in item_subcats]

            main_category = f'{driver.find_element(By.XPATH, "//main//h1").text} / '

            for subcat_link, subcat_string in zip(item_subcats_links, item_subcats_strings):
                if subcat_string == main_category[:-3]:
                    category_string = subcat_string
                else:
                    category_string = main_category + subcat_string

                current_page = 0
                do_page_exist = True

                while do_page_exist:
                    if subcat_link.__contains__('?sub'):
                        driver.get(f'{subcat_link}&page={current_page}')
                    else:
                        driver.get(f'{subcat_link}?page={current_page}')

                    time.sleep(Util.PRODUCT_LINK_EXTRACTION_DELAY)
                    articles_in_page = driver.find_elements(By.XPATH,
                                                            '/html/body/main/div/div/div[2]/div[3]/div[2]/div/a')

                    before = len(extracted)

                    if articles_in_page:
                        for article in articles_in_page:
                            article_href = article.get_attribute('href').split('?asq=')[0]
                            extracted.append(article_href)
                            if article_href in product_links_categories:
                                product_links_categories[article_href].append(category_string)
                            else:
                                product_links_categories[article_href] = [category_string]
                    else:
                        do_page_exist = False

                    cls.logger.info(f'ADDED: {len(extracted) - before} TOTAL: {len(extracted)} URL: {driver.current_url}')
                    current_page += 1

        Util.dump_to_json(product_links_categories, cls.PRODUCT_LINKS_CATEGORIES_JSON_PATH)

        cls.logger.info(f'EXTRACTED {len(extracted)} LINKS')

        extracted = set(extracted)

        cls.logger.info(f'EXTRACTED {len(extracted)} UNIQUE LINKS')

        if update:
            links_path = ScraperVtacItalia.PRODUCTS_LINKS_PATH

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

        if ScraperVtacItalia.DRIVER.current_url != link:
            ScraperVtacItalia.DRIVER.get(link)

        pdf_download_xpath = '//h4[text() = \'Download\']/parent::div/div/a'
        pdf_elements = []

        try:
            pdf_elements = ScraperVtacItalia.DRIVER.find_elements(By.XPATH, pdf_download_xpath)
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

        pdf_download_xpath = '//h4[text() = \'Download\']/parent::div/div/a'

        pdf_elements = driver.find_elements(By.XPATH, pdf_download_xpath)
        cls.logger.info(f'Found {len(pdf_elements)} elements in SKU {sku}')

        for pdf_element in pdf_elements:
            response = requests.get(pdf_element.get_attribute('href'))
            name = pdf_element.get_attribute('data-tippy-content')

            if '/' in name:
                name = name.replace('/', '-')

            nested_dir = f'{ScraperVtacItalia.PRODUCTS_PDF_PATH}/{sku}'
            os.makedirs(nested_dir, exist_ok=True)

            with open(f'{nested_dir}/{name}.pdf', 'wb') as file:
                file.write(response.content)

        return len(pdf_elements)
