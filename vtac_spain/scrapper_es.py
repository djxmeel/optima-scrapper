import json
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from util import Util


# VTAC ES SCRAPER
class ScraperVtacSpain:
    COUNTRY = 'es'

    # Creación del logger
    logger_path = Util.LOG_FILE_PATH[COUNTRY].format(Util.DATETIME)
    logger = Util.setup_logger(logger_path)
    print(f'LOGGER CREATED: {logger_path}')

    # Datos productos
    IF_EXTRACT_ITEM_INFO = False
    # PDFs productos
    IF_DL_ITEM_PDF = False
    # Enlaces productos en la página de origen
    IF_EXTRACT_ITEM_LINKS, IF_UPDATE = False, False
    # Todos los campos de los productos a implementar en ODOO
    IF_EXTRACT_DISTINCT_ITEMS_FIELDS = False

    DRIVER = webdriver.Firefox()

    JSON_DUMP_FREQUENCY = 100
    BEGIN_SCRAPE_FROM = 0

    SUBCATEGORIES = ()

    CATEGORIES_LINKS = (
        'https://v-tac.es/sistemas-solares.html',
        'https://v-tac.es/iluminaci%C3%B3n.html',
        'https://v-tac.es/smart-digital.html',
        'https://v-tac.es/el%C3%A9ctrico.html',
    )

    FIELDS_TO_DELETE_LITE = ('imgs', 'videos')

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
        energy_tag_xpath = "//img[@alt = 'Energy Class']"
        graph_dimensions_xpath = "//img[@alt = 'Dimensions']"
        product_desc_xpath = "//div[@class='product-description']"

        # Diccionario que almacena todos los datos de un artículo
        item = {'url': driver.current_url, 'list_price': 0, 'imgs': [], 'icons': [], 'descripcion': '', 'videos': []}

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
            item['sku'] = f'VS{item["Código de orden"]}'
            del item['Código de orden']
        else:
            item['sku'] = f'VS{Util.get_sku_from_link(driver, driver.current_url, "ES")}'

        # Extracción de la etiqueta energética
        # try:
        #     energy_tag_src = driver.find_element(By.XPATH, energy_tag_xpath).get_attribute('src')
        #     item['imgs'].append(Util.src_to_base64(energy_tag_src))
        # except NoSuchElementException:
        #     pass

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

        # Extracción de la descripción del producto
        try:
            product_desc = driver.find_element(By.XPATH, product_desc_xpath).get_attribute('innerHTML')
            item['descripcion'] = product_desc
        except NoSuchElementException:
            pass

        # Extracción del título
        item['name'] = f'[{item["sku"]}] {driver.find_element(By.XPATH, name_xpath).text}'

        # Uso de los campos de ODOO para el volumen y el peso si están disponibles
        if 'Volumen del artículo' in item.keys():
            item['volume'] = float(item['Volumen del artículo'].replace(',', '.'))
            del item['Volumen del artículo']
        if 'Peso del artículo' in item.keys():
            item['weight'] = float(item['Peso del artículo'].replace(',', '.').split(' ')[0].replace('kg', ''))
            del item['Peso del artículo']

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
                ScraperVtacSpain.extract_all_links(driver, categories)
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
            links_path = f'{Util.VTAC_COUNTRY_DIR[cls.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[cls.COUNTRY]}'

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

            nested_dir = f'{Util.VTAC_COUNTRY_DIR[cls.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}/{sku}'
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


# LINK EXTRACTION
if ScraperVtacSpain.IF_EXTRACT_ITEM_LINKS:
    ScraperVtacSpain.logger.info(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')
    
    if not ScraperVtacSpain.IF_UPDATE:
        # EXTRACT LINKS TO A set()
        extracted_links = ScraperVtacSpain.extract_all_links(ScraperVtacSpain.DRIVER, ScraperVtacSpain.CATEGORIES_LINKS)

        Util.dump_to_json(list(extracted_links),
                          f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')
    else:
        extracted_links, links_new = ScraperVtacSpain.extract_all_links(ScraperVtacSpain.DRIVER,
                                                                     ScraperVtacSpain.CATEGORIES_LINKS, update=True)

        Util.dump_to_json(list(extracted_links),
                          f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')
        if links_new:
            Util.dump_to_json(list(links_new),f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.NEW_VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')
    
    ScraperVtacSpain.logger.info(f'FINISHED LINK EXTRACTION TO {Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')

# PRODUCTS INFO EXTRACTION
if ScraperVtacSpain.IF_EXTRACT_ITEM_INFO:
    ScraperVtacSpain.logger.info(f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}')
    # EXTRACTION OF ITEMS INFO TO VTAC_PRODUCT_INFO
    Util.begin_items_info_extraction(
        ScraperVtacSpain,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}',
        ScraperVtacSpain.logger,
        ScraperVtacSpain.BEGIN_SCRAPE_FROM,
    )
    ScraperVtacSpain.logger.info(f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}')

# PDF DL
if ScraperVtacSpain.IF_DL_ITEM_PDF:
    ScraperVtacSpain.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_PRODUCT_PDF_DIR}')
    Util.begin_items_PDF_download(
        ScraperVtacSpain,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}',
        'ES',
        ScraperVtacSpain.logger
    )
    ScraperVtacSpain.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_PRODUCT_PDF_DIR}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if ScraperVtacSpain.IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    ScraperVtacSpain.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCT_INFO_LITE_DIR}')
    ScraperVtacSpain.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

ScraperVtacSpain.DRIVER.close()
