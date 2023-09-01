import json
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from util import Util

# VTAC ES SCRAPER

logger = Util.setup_logger('ES_LOG.txt')

# Datos productos
IF_EXTRACT_ITEM_INFO = True
# PDFs productos
IF_DL_ITEM_PDF = True
# Enlaces productos en la página de origen
IF_EXTRACT_ITEM_LINKS = False
# Todos los campos de los productos a implementar en ODOO
IF_EXTRACT_DISTINCT_ITEMS_FIELDS = True

DRIVER = webdriver.Firefox()

JSON_DUMP_FREQUENCY = 100

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
    KEYS_VALUES_XPATH = "//div[@class='product-field product-field-type-S']"
    ENERGY_TAG_XPATH = "//img[@alt = 'Energy Class']"
    GRAPH_DIMENSIONS_XPATH = "//img[@alt = 'Dimensions']"
    PRODUCT_DESC_XPATH = "//div[@class='product-description']"

    # Diccionario que almacena todos los datos de un artículo
    item = {'url': driver.current_url, 'list_price': 0, 'imgs': [], 'descripcion': '', 'videos': []}

    print(f'BEGINNING EXTRACTION OF: {driver.current_url}')

    # Extracción de los campos
    keys_values = driver.find_elements(By.XPATH, KEYS_VALUES_XPATH)

    for key_value in keys_values:
        key = key_value.find_element(By.TAG_NAME, "strong")
        try:
            value = key_value.find_element(By.TAG_NAME, "div")
        except NoSuchElementException:
            print(f'Field {key.text} has no value.')
            item[key.text] = ''
            continue

        item[key.text] = value.text

    # Extracción y formateo del SKU
    if 'Código de orden' in item.keys():
        item['SKU'] = f'VS{item["Código de orden"]}'
        del item['Código de orden']

    # Renombrado de campos determinados
    if 'Ángulo de haz' in item.keys():
        item['Ángulo de apertura'] = item['Ángulo de haz']
        del item['Ángulo de haz']
    if 'EAN Código' in item.keys():
        item['EAN'] = item['EAN Código']
        del item['EAN Código']
    if 'Código de producto' in item.keys():
        item['Código de familia'] = item['Código de producto']
        del item['Código de producto']
    if 'Las condiciones de trabajo' in item.keys():
        item['Temperaturas de trabajo'] = item['Las condiciones de trabajo']
        del item['Las condiciones de trabajo']
    if 'Hora de inicio al 100% encendido' in item.keys():
        item['Tiempo de inicio al 100% encendido'] = item['Hora de inicio al 100% encendido']
        del item['Hora de inicio al 100% encendido']

    # Extracción de la etiqueta energética
    try:
        energy_tag_src = driver.find_element(By.XPATH, ENERGY_TAG_XPATH).get_attribute('src')
        item['imgs'].append(Util.src_to_base64(energy_tag_src))
    except NoSuchElementException:
        pass

    # Extracción de las dimensiones gráficas
    try:
        graph_dimensions_src = driver.find_element(By.XPATH, GRAPH_DIMENSIONS_XPATH).get_attribute('src')
        item['imgs'].append(Util.src_to_base64(graph_dimensions_src))
    except NoSuchElementException:
        pass

    # Extracción de la descripción del producto
    try:
        product_desc = driver.find_element(By.XPATH, PRODUCT_DESC_XPATH).get_attribute('innerHTML')
        item['descripcion'] = product_desc
    except NoSuchElementException:
        pass

    # Extracción del título
    item['name'] = driver.find_element(By.XPATH, NAME_XPATH).text

    # Uso de los campos de ODOO para el volumen y el peso si están disponibles
    if 'Volumen del artículo' in item.keys():
        item['volume'] = float(item['Volumen del artículo'].replace(',', '.'))
        del item['Volumen del artículo']
    if 'Peso del artículo' in item.keys():
        item['weight'] = float(item['Peso del artículo'].replace(',', '.').replace('kg', ''))
        del item['Peso del artículo']

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

    DLs_XPATH = '//div[@class="downloads"]//a'
    pdf_elements = []

    try:
        # Get the <a> elements
        pdf_elements = driver.find_elements(By.XPATH, DLs_XPATH)

        print(f'Found {len(pdf_elements)} attachments in SKU {sku}')

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

            filename = filename.replace('%20', '_')

            with open(f'{nested_dir}/{filename}', 'wb') as file:
                file.write(response.content)

    except NoSuchElementException:
        print(f'No PDFs found for SKU -> {sku}')

    return len(pdf_elements)


def begin_items_PDF_download(begin_from=0):  # TODO DUPLICATE CHECK
    # Read the JSON file
    with open(f'{Util.VTAC_ES_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_ES}') as f:
        loaded_links = json.load(f)

    counter = begin_from
    try:
        for link in loaded_links[begin_from:]:
            sku = Util.get_sku_from_link(DRIVER, link, 'ES')

            found = download_pdfs_of_sku(DRIVER, sku)
            print(f'DOWNLOADED {found} PDFS FROM : {link}  {counter + 1}/{len(loaded_links)}')
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
