import json
import math
import time
import requests
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from util import Util

# VTAC ES SCRAPER

# Datos productos
IF_EXTRACT_ITEM_INFO = False
# PDFs productos
IF_DL_ITEM_PDF = False
# Enlaces productos en la página de origen
IF_EXTRACT_ITEM_LINKS = False
# Todos los campos de los productos a implementar en ODOO
IF_EXTRACT_DISTINCT_ITEMS_FIELDS = True

DRIVER = webdriver.Firefox()

JSON_DUMP_FREQUENCY = 5

DLs_XPATH = '//div[@class="downloads"]//a'

CATEGORIES_LINKS = [
    'https://v-tac.es/sistemas-solares.html',
    'https://v-tac.es/iluminaci%C3%B3n.html',
    'https://v-tac.es/smart-digital.html',
    'https://v-tac.es/el%C3%A9ctrico.html',
]


def scrape_item(driver, url):
    try:
        # Se conecta el driver instanciado a la URL
        driver.get(url)
    except:
        print(f'ERROR extrayendo los datos de {url}. Reintentando...')
        time.sleep(5)
        scrape_item(driver, url)
        return

    NAME_XPATH = "//h3[@itemprop='name']"
    SKU_XPATH = "//div[@class='sku-inner']"
    KEYS_VALUES_XPATH = "//div[@class='product-field product-field-type-S']"
    ENERGY_TAG_XPATH = "//img[@alt = 'Energy Class']"
    GRAPH_DIMENSIONS_XPATH = "//img[@alt = 'Dimensions']"
    PRODUCT_DESC_XPATH = "//div[@class='product-description']"

    # Diccionario que almacena todos los datos de un artículo
    item = {'x_url': driver.current_url, 'list_price': 0, 'imgs': [], 'x_mas_info': '', 'videos': []}

    print(f'BEGINNING EXTRACTION OF: {driver.current_url}')

    # Extracción del SKU
    try:
        item['x_SKU'] = f"VS{driver.find_element(By.XPATH, SKU_XPATH).text.split(' ')[1]}"
    except NoSuchElementException:
        print(f'SKU NOT FOUND FOR URL {driver.current_url}')

    # Extracción de los campos
    keys_values = driver.find_elements(By.XPATH, KEYS_VALUES_XPATH)

    for key_value in keys_values:
        key = key_value.find_element(By.TAG_NAME, "strong")
        try:
            value = key_value.find_element(By.TAG_NAME, "div")
        except NoSuchElementException:
            print(f'Field {key.text} has no value.')
            item[Util.format_field_odoo(key.text)] = ''
            continue

        item[Util.format_field_odoo(key.text)] = value.text

    # Extracción de la etiqueta energética y dimensiones gráficas
    try:
        energy_tag_src = driver.find_element(By.XPATH, ENERGY_TAG_XPATH).get_attribute('src')
        item['imgs'].append(Util.src_to_base64(energy_tag_src))
    except NoSuchElementException:
        pass

    try:
        graph_dimensions_src = driver.find_element(By.XPATH, GRAPH_DIMENSIONS_XPATH).get_attribute('src')
        item['imgs'].append(Util.src_to_base64(graph_dimensions_src))
    except NoSuchElementException:
        pass

    # Extracción de la descripción del producto
    try:
        product_desc = driver.find_element(By.XPATH, PRODUCT_DESC_XPATH).get_attribute('innerHTML')
        item['x_mas_info'] = product_desc
    except NoSuchElementException:
        pass

    # Extracción del título
    item['name'] = driver.find_element(By.XPATH, NAME_XPATH).text

    # Uso de los campos de ODOO para el volumen y el peso si están disponibles
    if 'x_volumen_del_articulo' in item.keys():
        item['volume'] = item['x_volumen_del_articulo']
        del item['x_volumen_del_articulo']
    if 'x_peso_del_articulo' in item.keys():
        item['weight'] = item['x_peso_del_articulo']
        del item['x_peso_del_articulo']

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

        inner_categories_links = [cat.get_attribute("href") for cat in driver.find_elements(By.XPATH, "/html/body/div[1]/div/section[3]/div/main/div/div[2]/div[2]/div/section//h4//a")]

        for inner_cat in inner_categories_links:
            driver.get(f'{inner_cat}?limit=9999')
            links = driver.find_elements(By.XPATH, "//div[@id='bd_results']//img/parent::a")
            time.sleep(Util.PRODUCT_LINK_EXTRACTION_DELAY)

            before = len(extracted)

            for link in links:
                extracted.add(link.get_attribute('href'))

            print(f'ADDED: {len(extracted) - before} TOTAL: {len(extracted)} URL: {driver.current_url}')

    return extracted


def download_pdfs_of_sku(driver, sku):
    """
    Downloads PDF from a given URL.

    Parameters:
    driver: Selenium WebDriver instance.
    url (str): URL to download the PDF from.
    sku (str): SKU of the product.

    """
    time.sleep(Util.PDF_DOWNLOAD_DELAY)

    pdf_download_tab_xpath = '//div[@id = \'tab-label-product.downloads\']'

    try:
        # Specs tab certificates
        pdf_elements = [driver.find_elements(By.XPATH, "//span[text() = 'Check the certificate']/parent::a")]

        # Downloads tab
        driver.find_element(By.XPATH, pdf_download_tab_xpath).click()
        pdf_elements.append(driver.find_elements(By.XPATH, "//div[@class='attachment-item']/a"))

        print(f'Found {len(pdf_elements)} PDFs in SKU {sku}')

        for pdf_element in pdf_elements:
            url = pdf_element.get_attribute('href')
            response = requests.get(url)

            nested_dir = f'{Util.VTAC_ES_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}/{sku}'
            os.makedirs(nested_dir, exist_ok=True)

            # Get the original file name if possible
            content_disposition = response.headers.get('content-disposition')
            if content_disposition:
                filename = content_disposition.split('filename=')[-1].strip('"')
            else:
                # Fallback to extracting the filename from URL if no content-disposition header
                filename = os.path.basename(url)

            with open(f'{nested_dir}/{filename}', 'wb') as file:
                file.write(response.content)

    except NoSuchElementException:
        print(f'No PDFs found for SKU -> {sku}')


def begin_items_PDF_download(begin_from=0):  # TODO DUPLICATE CHECK
    # Read the JSON file
    with open(f'{Util.VTAC_ES_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ES}') as f:
        loaded_links = json.load(f)

    counter = begin_from
    try:
        for link in loaded_links[begin_from:]:
            DRIVER.get(link)
            sku = Util.get_sku_from_link_es(DRIVER)

            download_pdfs_of_sku(DRIVER, sku)
            print(f'DOWNLOADED PDFS OF : {link}  {counter + 1}/{len(loaded_links)}')
            counter += 1
    except:
        print("Error en la descarga de PDFs. Reintentando...")
        time.sleep(5)
        begin_items_PDF_download(counter)


def begin_items_info_extraction(start_from):
    """
    Begins item info extraction.

    Parameters:
    start_from (int): The index to start extraction from.
    """
    # Load links from JSON file
    links = Util.load_json_data(f'{Util.VTAC_ES_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ES}')

    products_data = []
    counter = start_from

    try:
        for link in links[start_from:]:
            products_data.append(scrape_item(DRIVER, link))
            counter += 1
            print(f'{counter}/{len(links)}\n')

            # Save each X to a JSON
            if counter % JSON_DUMP_FREQUENCY == 0 or counter == len(links):
                filename = f'{Util.VTAC_ES_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}/{Util.ITEMS_INFO_FILENAME_TEMPLATE.format(counter)}'
                Util.dump_to_json(products_data, filename)

                # Dump lighter version of json
                dump_product_info_lite(products_data, counter)

                products_data.clear()

    except NoSuchElementException:
        products_data.clear()
        begin_items_info_extraction(counter - counter % JSON_DUMP_FREQUENCY)


def dump_product_info_lite(products_data, counter):
    for product in products_data:
        del product['imgs'], product['videos']

    Util.dump_to_json(products_data, f"{Util.VTAC_ES_DIR}/{Util.VTAC_PRODUCT_INFO_LITE}/{Util.ITEMS_INFO_LITE_FILENAME_TEMPLATE.format(counter)}")
    print('DUMPED LITE PRODUCT INFO ')


# LINK EXTRACTION
if IF_EXTRACT_ITEM_LINKS:
    print(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_PRODUCTS_LINKS_FILE_ES}')
    extracted_links = extract_all_links(DRIVER, CATEGORIES_LINKS)  # EXTRACTION LINKS TO A set()
    Util.dump_to_json(list(extracted_links), f'{Util.VTAC_ES_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ES}')  # DUMPING LINKS TO JSON
    print(f'FINISHED LINK EXTRACTION TO {Util.VTAC_PRODUCTS_LINKS_FILE_ES}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    print(f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_PRODUCTS_INFO_DIR}')
    begin_items_info_extraction(0)  # EXTRACTION OF ITEMS INFO TO VTAC_PRODUCT_INFO
    print(f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_PRODUCTS_INFO_DIR}')

# PDF DL
if IF_DL_ITEM_PDF:
    print(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_PRODUCT_PDF_DIR}')
    begin_items_PDF_download()
    print(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_PRODUCT_PDF_DIR}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    print(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(Util.VTAC_ES_DIR)
    print(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

DRIVER.close()
