import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from util import Util


# VTAC ITALIA SCRAPER

class ScraperVtacItalia:
    logger = Util.setup_logger(Util.ITA_LOG_FILE_PATH)

    # Datos productos
    IF_EXTRACT_ITEM_INFO = False
    # PDFs productos
    IF_DL_ITEM_PDF = True
    # Enlaces productos en la página de origen
    IF_EXTRACT_ITEM_LINKS = False
    # Todos los campos de los productos a implementar en ODOO
    IF_EXTRACT_DISTINCT_ITEMS_FIELDS = False

    DRIVER = webdriver.Firefox()

    JSON_DUMP_FREQUENCY = 50
    BEGIN_SCRAPE_FROM = 0

    SUBCATEGORIES = ["Specifiche tecniche", "Packaging"]

    CATEGORIES_LINKS = [
        'https://led-italia.it/prodotti/M4E-fotovoltaico',
        'https://led-italia.it/prodotti/M54-illuminazione-led',
        'https://led-italia.it/prodotti/M68-elettronica-di-consumo'
    ]

    @staticmethod
    def scrape_item(driver, url, subcategories=None):
        try:
            # Se conecta el driver instanciado a la URL
            driver.get(url)
        except:
            print(f'ERROR extrayendo los datos de {url}. Reintentando...')
            time.sleep(5)
            ScraperVtacItalia.scrape_item(driver, url, subcategories)
            return

        subcategories_elements = []

        for subcat in subcategories:
            subcategories_elements.append(driver.find_element(By.XPATH, f'//h4[text() = \'{subcat}\']/parent::div'))

        # Diccionario que almacena todos los datos de un artículo
        item = {'url': driver.current_url, 'kit': [], 'accesorios': [], 'list_price': 0, 'videos': [],
                'descripcion': '',
                'imgs': [], 'icons': []}

        print(f'BEGINNING EXTRACTION OF: {driver.current_url}')

        # Extracción de los enlaces de videos
        iframes = driver.find_elements(By.XPATH, '//main//iframe')

        for iframe in iframes:
            item['videos'].append(iframe.get_attribute('src'))

        # Extracción del kit
        try:
            kit_anchor = driver.find_elements(By.XPATH, f'//h4[text() = \'Il kit comprende\']/parent::div//a')

            for anchor in kit_anchor:
                kit_span = anchor.find_element(By.TAG_NAME, 'span')

                kit_info = {'link': anchor.get_attribute('href'),
                            'sku': kit_span.find_element(By.TAG_NAME, 'span').text,
                            'cantidad': kit_span.text.split('x')[0]
                            }

                item['kit'].append(kit_info)

        except NoSuchElementException:
            print('EL ARTICULO NO TIENE KIT')

        # Extracción de los accesorios
        try:
            acces_li_tags = driver.find_elements(By.XPATH, f'//h4[text() = \'Accessori inclusi\']/parent::div//ul/li')

            for li in acces_li_tags:
                acces_cantidad = li.find_element(By.TAG_NAME, 'span')
                acces_anchor = li.find_element(By.TAG_NAME, 'a')

                acces_info = {'link': acces_anchor.get_attribute('href'),
                              'sku': acces_anchor.find_element(By.TAG_NAME, 'b').text,
                              'cantidad': acces_cantidad.text.split('x')[0]
                              }

                item['accesorios'].append(acces_info)

        except NoSuchElementException:
            print('EL ARTICULO NO TIENE ACCESORIOS')

        # Extracción del precio
        try:
            item['list_price'] = driver.find_element(By.XPATH,
                                                     f'//*[normalize-space() = \'Prezzo di listino\']/parent::span/span[2]').text

            if item['list_price'].__contains__('('):
                item['list_price'] = item['list_price'].split('(')[0]

            item['list_price'] = float(item['list_price'].replace('€', '').replace('.', '').replace(',', '.'))
        except NoSuchElementException:
            try:
                item['list_price'] = driver.find_element(By.XPATH,
                                                         f'//*[normalize-space() = \'Prezzo al pubblico\']/parent::span').text[
                                     19:-9]

                if item['list_price'].__contains__('('):
                    item['list_price'] = item['list_price'].split('(')[0]

                item['list_price'] = float(item['list_price'].replace('€', '').replace('.', '').replace(',', '.'))
            except NoSuchElementException:
                print('PRECIO NO ENCONTRADO')

        # Comprobacion de la existencia de una descripcion (Maggiori informazioni)
        try:
            desc_innerHTML = driver.find_element(By.XPATH,
                                                 f'//h4[text() = \'Maggiori informazioni\']/parent::div/div').get_attribute(
                'innerHTML')

            item['descripcion'] = desc_innerHTML
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

                item[key] = Util.translate_from_to_spanish('it', field.find_element(By.TAG_NAME, 'span').text)

            # Uso de los campos de ODOO para el volumen y el peso si están disponibles
            if 'Volume' in item:
                item['volume'] = float(item['Volume'].replace(',', '.').replace('m³', ''))
                del item['Volume']
            if 'Peso' in item:
                item['weight'] = float(item['Peso'].replace(',', '.').replace('Kg', ''))
                del item['Peso']

        # Extracción del titulo
        item['name'] = Util.translate_from_to_spanish('it',
                                                      driver.find_element(By.XPATH,
                                                                          '/html/body/main/div[1]/div/div[2]/div[2]/div[1]/h2').text)

        # Extracción de iconos
        try:
            icons = driver.find_elements(By.XPATH, '/html/body/main/div[1]/div/div[2]/div[2]/div[4]/div[2]/img')

            # Mapeo de icons a una lista de sus base64
            item['icons'] = [Util.src_to_base64(icon.get_attribute('src')) for icon in icons]
            print(f'ENCODED ICONS')
        except NoSuchElementException:
            print('PRODUCT HAS NO ICONS')

        try:
            # Find the image elements and extract their data
            image_elements = driver.find_element(By.ID, 'images-slider-list') \
                .find_elements(By.TAG_NAME, 'img')

            for index, image_element in enumerate(image_elements):
                src = image_element.get_attribute('src')
                item['imgs'].append({'src': src, 'img64': Util.src_to_base64(src)})

            print(f'ENCODED IMAGES')
        except NoSuchElementException:
            print('PRODUCT HAS NO IMGS')

        # Formateo del SKU
        item['SKU'] = f'VS{item["SKU"]}'

        # Formateo del titulo
        item['name'] = f'[{item["SKU"]}] {item["name"]}'

        print(item['name'])

        return item

    @staticmethod
    def extract_all_links(driver, categories):
        extracted = set()
        for cat in categories:
            try:
                driver.get(cat)
            except:
                print("ERROR navegando a la página. Reintentando...")
                ScraperVtacItalia.extract_all_links(driver, categories)
                return

            item_subcats = [link.get_attribute('href') for link in
                            driver.find_elements(By.XPATH, '/html/body/main/div[1]/div/a')]

            for item_subcat in item_subcats:
                current_page = 0
                do_page_exist = True

                while do_page_exist:
                    if item_subcat.__contains__('?sub'):
                        driver.get(f'{item_subcat}&page={current_page}')
                    else:
                        driver.get(f'{item_subcat}?page={current_page}')

                    time.sleep(Util.PRODUCT_LINK_EXTRACTION_DELAY)
                    articles_in_page = driver.find_elements(By.XPATH,
                                                            '/html/body/main/div/div/div[2]/div[2]/div[2]/div/a')
                    print(f'FOUND {len(articles_in_page)} ARTICLES')

                    before = len(extracted)

                    if len(articles_in_page) > 0:
                        for article in articles_in_page:
                            extracted.add(article.get_attribute('href').split('?asq=')[0])
                    else:
                        do_page_exist = False

                    print(f'ADDED: {len(extracted) - before} TOTAL: {len(extracted)} URL: {driver.current_url}')
                    current_page += 1

        return extracted

    @staticmethod
    def download_pdfs_of_sku(driver, sku):
        """
        Downloads PDF from a given URL.

        Parameters:
        driver: Selenium WebDriver instance.
        url (str): URL to download the PDF from.
        sku (str): SKU of the product.

        """
        time.sleep(Util.PDF_DOWNLOAD_DELAY)

        pdf_download_xpath = '//h4[text() = \'Download\']/parent::div/div/a'

        pdf_elements = []

        try:
            pdf_elements = driver.find_elements(By.XPATH, pdf_download_xpath)
            print(f'Found {len(pdf_elements)} elements in SKU {sku}')

            for pdf_element in pdf_elements:
                response = requests.get(pdf_element.get_attribute('href'))
                name = pdf_element.get_attribute('data-tippy-content')

                if '/' in name:
                    name = name.replace('/', '-')

                nested_dir = f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}/{sku}'
                os.makedirs(nested_dir, exist_ok=True)

                with open(f'{nested_dir}/{name}.pdf', 'wb') as file:
                    file.write(response.content)

        except NoSuchElementException:
            print(f'No PDFs found for SKU -> {sku}')

        return len(pdf_elements)

    @staticmethod
    def dump_product_info_lite(products_data, counter):
        for product in products_data:
            del product['imgs'], product['icons'], product['kit'], product['accesorios'], product['videos']

        Util.dump_to_json(products_data,
                          f"{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCT_INFO_LITE}/{Util.ITEMS_INFO_LITE_FILENAME_TEMPLATE.format(counter)}")
        print('DUMPED LITE PRODUCT INFO ')


# LINK EXTRACTION
if ScraperVtacItalia.IF_EXTRACT_ITEM_LINKS:
    print(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}')
    extracted_links = ScraperVtacItalia.extract_all_links(ScraperVtacItalia.DRIVER,
                                                          ScraperVtacItalia.CATEGORIES_LINKS)  # EXTRACTION LINKS TO A set()
    Util.dump_to_json(list(extracted_links),
                      f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}')  # DUMPING LINKS TO JSON
    print(f'FINISHED LINK EXTRACTION TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}')

# PRODUCTS INFO EXTRACTION
if ScraperVtacItalia.IF_EXTRACT_ITEM_INFO:
    print(f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}')
    # EXTRACTION OF ITEMS INFO TO VTAC_PRODUCT_INFO
    Util.begin_items_info_extraction(
        ScraperVtacItalia,
        f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}',
        f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}',
        ScraperVtacItalia.BEGIN_SCRAPE_FROM
    )
    print(f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}')

# PDF DL
if ScraperVtacItalia.IF_DL_ITEM_PDF:
    print(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}')
    Util.begin_items_PDF_download(
        ScraperVtacItalia,
        f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}',
        'ITA'
    )
    print(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if ScraperVtacItalia.IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    print(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(Util.VTAC_ITA_DIR)
    print(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

ScraperVtacItalia.DRIVER.close()
