import json
import time
import requests
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from util import Util

# VTAC ITALIA SCRAPER

# Datos productos
IF_EXTRACT_ITEM_INFO = False
# PDFs productos
IF_DL_ITEM_PDF = False
# Enlaces productos en la página de origen
IF_EXTRACT_ITEM_LINKS = False
# Todos los campos de los productos a implementar en ODOO
IF_EXTRACT_DISTINCT_ITEMS_FIELDS = True


DRIVER = webdriver.Firefox()

JSON_DUMP_FREQUENCY = 50

SUBCATEGORIES = ["Specifiche tecniche", "Packaging"]

CATEGORIES_LINKS = [
    'https://led-italia.it/prodotti/M4E-fotovoltaico',
    'https://led-italia.it/prodotti/M54-illuminazione-led',
    'https://led-italia.it/prodotti/M68-elettronica-di-consumo'
]


def scrape_item(driver, subcategories, url):
    try:
        # Se conecta el driver instanciado a la URL
        driver.get(url)
    except:
        print(f'ERROR extrayendo los datos de {url}. Reintentando...')
        time.sleep(5)
        scrape_item(driver, subcategories, url)
        return

    subcategories_elements = []

    for subcat in subcategories:
        subcategories_elements.append(driver.find_element(By.XPATH, f'//h4[text() = \'{subcat}\']/parent::div'))

    # Diccionario que almacena todos los datos de un artículo
    item = {'x_url': driver.current_url, 'kit': [], 'accesorios': [], 'list_price': 0, 'videos': [], 'x_mas_info': '', 'imgs': [], 'icons': []}

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

        item['x_mas_info'] = desc_innerHTML
    except NoSuchElementException:
        print('Producto no tiene descripción')

    # Para cada subcategoria, extraemos sus campos
    for subcat in subcategories_elements:
        # Divs que contienen el campo y valor (<b> Campo | <span> Valor)
        fields = subcat.find_element(By.TAG_NAME, 'div') \
            .find_elements(By.TAG_NAME, 'div')

        # Guardado de campos y valor en la estructura de datos
        for field in fields:
            key = Util.translate_from_to_spanish('it', field.find_element(By.TAG_NAME, 'b').text)
            key = Util.format_field_odoo(key)

            item[key] = Util.translate_from_to_spanish('it', field.find_element(By.TAG_NAME, 'span').text)

        if 'x_Volume' in item:
            item['volume'] = float(item['x_Volume'].replace(',', '.').replace('m³', ''))
            del item['x_Volume']
        if 'x_Peso' in item:
            item['weight'] = float(item['x_Peso'].replace(',', '.').replace('Kg', ''))
            del item['x_Peso']

    # Extracción del titulo
    item['name'] = Util.translate_from_to_spanish('it',
        driver.find_element(By.XPATH, '/html/body/main/div[1]/div/div[2]/div[2]/div[1]/h2').text)

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
    item['x_SKU'] = f'VS{item["x_SKU"]}'

    # Formateo del titulo
    item['name'] = f'[{item["x_SKU"]}] {item["name"]}'

    print(item['name'])

    return item


def extract_all_links(driver, categories):
    extracted = set()
    for cat in categories:
        try:
            driver.get(cat)
        except:
            print("ERROR navegando a la página. Reintentando...")
            extract_all_links(driver, categories)
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
                articles_in_page = driver.find_elements(By.XPATH, '/html/body/main/div/div/div[2]/div[2]/div[2]/div/a')
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


def download_pdfs_of_sku(driver, url, sku):
    """
    Downloads PDF from a given URL.

    Parameters:
    driver: Selenium WebDriver instance.
    url (str): URL to download the PDF from.
    sku (str): SKU of the product.

    """
    driver.get(url)
    time.sleep(Util.PDF_DOWNLOAD_DELAY)

    pdf_download_xpath = '//h4[text() = \'Download\']/parent::div/div/a'

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


def begin_items_PDF_download():  # TODO DUPLICATE CHECK
    # Read the JSON file
    with open(f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}') as f:
        loaded_links = json.load(f)

    for index, link in enumerate(loaded_links):
        sku = Util.get_sku_from_link_ita(link)

        download_pdfs_of_sku(DRIVER, link, sku)
        print(f'DOWNLOADED PDFS OF : {link}  {index + 1}/{len(loaded_links)}')


def begin_items_info_extraction(start_from):
    """
    Begins item info extraction.

    Parameters:
    start_from (int): The index to start extraction from.
    """
    # Load links from JSON file
    links = Util.load_json_data(f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}')

    products_data = []
    counter = start_from

    try:
        for link in links[start_from:]:
            products_data.append(scrape_item(DRIVER, SUBCATEGORIES, link))
            counter += 1
            print(f'{counter}/{len(links)}\n')

            # Save each X to a JSON
            if counter % JSON_DUMP_FREQUENCY == 0 or counter == len(links):
                filename = f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}/{Util.ITEMS_INFO_FILENAME_TEMPLATE.format(counter)}'
                Util.dump_to_json(products_data, filename)

                # Dump lighter version of json
                dump_product_info_lite(products_data, counter)

                products_data.clear()

    except Exception as e:
        print(e)
        products_data.clear()
        begin_items_info_extraction(counter - counter % JSON_DUMP_FREQUENCY)


def dump_product_info_lite(products_data, counter):
    for product in products_data:
        del product['imgs'], product['icons'], product['kit'], product['accesorios'], product['videos']

    Util.dump_to_json(products_data, f"{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCT_INFO_LITE}/{Util.ITEMS_INFO_LITE_FILENAME_TEMPLATE.format(counter)}")
    print('DUMPED LITE PRODUCT INFO ')


# GET ALL DISTINCT FIELDS IN A SET AND EXTRACT THEM TO EXCEL
def extract_distinct_fields_to_excel():
    file_list = Util.get_all_files_in_directory(f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCT_INFO_LITE}')
    json_data = []
    fields = set()

    for file_path in file_list:
        with open(file_path, "r") as file:
            json_data.extend(json.load(file))

    for product in json_data:
        for attr in product.keys():
            fields.add(attr)

    excel_dicts = []

    print(f'FOUND {len(fields)} DISTINCT FIELDS')

    for field in fields:
        # Filter out non-custom fields
        if not field.startswith('x_'):
            continue

        excel_dicts.append(
            {'Nombre de campo': field,
             'Etiqueta de campo': field,
             'Modelo': 'product.template',
             'Tipo de campo': 'texto',
             'Indexado': True,
             'Almacenado': True,
             'Sólo lectura': False,
             'Modelo relacionado': ''
             }
        )

    Util.dump_to_json(excel_dicts, f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_FIELDS_FILE}')

    # Read the JSON file
    data = pd.read_json(f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_FIELDS_FILE}')

    # Write the DataFrame to an Excel file
    excel_file_path = "DISTINCT_FIELDS_EXCEL.xlsx"
    data.to_excel(excel_file_path, index=False)  # Set index=False if you don't want the DataFrame indices in the Excel file


# LINK EXTRACTION
if IF_EXTRACT_ITEM_LINKS:
    print(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}')
    extracted_links = extract_all_links(DRIVER, CATEGORIES_LINKS)  # EXTRACTION LINKS TO A set()
    Util.dump_to_json(list(extracted_links), f'{Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}')  # DUMPING LINKS TO JSON
    print(f'FINISHED LINK EXTRACTION TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ITA}')


# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    print(f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}')
    begin_items_info_extraction(0)  # EXTRACTION OF ITEMS INFO TO VTAC_PRODUCT_INFO
    print(f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}')


# PDF DL
if IF_DL_ITEM_PDF:
    print(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}')
    begin_items_PDF_download()
    print(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_ITA_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}')


# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    print(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    extract_distinct_fields_to_excel()
    print(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

DRIVER.close()
