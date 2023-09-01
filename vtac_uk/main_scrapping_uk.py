import json
import math
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from util import Util


# VTAC UK SCRAPER

logger = Util.setup_logger(Util.UK_LOG_FILE_PATH)

# Datos productos
IF_EXTRACT_ITEM_INFO = True
# PDFs productos
IF_DL_ITEM_PDF = True
# Enlaces productos en la página de origen
IF_EXTRACT_ITEM_LINKS = False
# Todos los campos de los productos a implementar en ODOO
IF_EXTRACT_DISTINCT_ITEMS_FIELDS = True

DRIVER = webdriver.Firefox()

JSON_DUMP_FREQUENCY = 10

SUBCATEGORIES_IDS = ["product-attributes", "product-packaging", "product-features"]

CATEGORIES_LINKS = [
    'https://www.vtacexports.com/default/digital-accessories.html',
    'https://www.vtacexports.com/default/led-lighting.html',
    'https://www.vtacexports.com/default/decorative-lighting.html',
    'https://www.vtacexports.com/default/smart-products.html',
    'https://www.vtacexports.com/default/electrical.html'
]


def scrape_item(driver, subcategories_ids, url):
    try:
        # Se conecta el driver instanciado a la URL
        driver.get(url)
    except:
        print(f'ERROR extrayendo los datos de {url}. Reintentando...')
        time.sleep(5)
        scrape_item(driver, subcategories_ids, url)
        return

    subcategories_li_elements = []

    for subcat_id in subcategories_ids:
        try:
            subcategories_li_elements += driver.find_elements(By.XPATH, f'//div[@id = "{subcat_id}"]//ul/li')
        except NoSuchElementException:
            continue

    # Diccionario que almacena todos los datos de un artículo
    item = {'url': driver.current_url, 'list_price': 0, 'imgs': [], 'icons': [], 'descripcion': '', 'videos': []}

    print(f'BEGINNING EXTRACTION OF: {driver.current_url}')

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
            item[key] = value

        except NoSuchElementException:
            # Se hace click() sobre el botón de Features para acceder al texto
            driver.find_element(By.ID, 'tab-label-features').click()

            # <li> que no contiene <span> -> Feature
            item['descripcion'] += f'{Util.translate_from_to_spanish("en", subcat_li.text)}\n'

        if 'Peso bruto (kg)' in item:
            item['weight'] = float(item['Peso bruto (kg)'].replace(',', '.'))
            del item['Peso bruto (kg)']

    # Extracción del SKU
    try:
        item['SKU'] = f'VS{Util.get_sku_from_link_uk(driver)}'
    except NoSuchElementException:
        print('SKU NO ENCONTRADO')

    # Extracción del precio
    try:
        item['list_price'] = driver.find_element(By.XPATH,
                                                 f'/html/body/div[3]/main/div[4]/div/div/section[1]/div/div/div[2]/div[3]/div/div/div[2]/div[1]/span').text

        item['list_price'] = float(item['list_price'].replace('£', '').replace(',', '.'))
    except NoSuchElementException:
        print('PRECIO NO ENCONTRADO')

    # Extracción del titulo
    item['name'] = Util.translate_from_to_spanish('en',
        driver.find_element(By.XPATH, '/html/body/div[3]/main/div[4]/div/div/section[1]/div/div/div[2]/div[1]/div').text)

    # Formateo del titulo
    item['name'] = f'[{item["SKU"]}] {item["name"]}'

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

        print(f'ENCODED IMAGES')
    except NoSuchElementException:
        print('PRODUCT HAS NO IMGS')

    # Extracción de iconos
    try:
        icons = driver.find_elements(By.XPATH, '/html/body/div[3]/main/div[4]/div/div/section[1]/div/div/div[1]/div[2]//*[name()="svg"]')

        for icon in icons:
            item['icons'].append(icon.screenshot_as_base64)

        print(f'ENCODED ICONS')
    except NoSuchElementException:
        print('PRODUCT HAS NO ICONS')

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

        # Número total de productos por categoría
        product_count = int(driver.find_element(By.XPATH, '//*[@id="maincontent"]/div[4]/div[1]/h5').text.split(' ')[0])

        # Número de páginas (Total / 16)
        page_count = math.ceil(product_count / 16)

        for page in range(1, page_count + 1):
            driver.get(f'{cat}?p={page}')

            time.sleep(Util.PRODUCT_LINK_EXTRACTION_DELAY)

            links = driver.find_elements(By.XPATH, '/html/body/div[3]/main/div[4]/div[2]/section/div[2]/div//form/a')

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

    pdf_elements = []

    try:
        # Specs tab certificates
        pdf_elements = driver.find_elements(By.XPATH, "//span[text() = 'Check the certificate']/parent::a")

        # Downloads tab
        driver.find_element(By.XPATH, pdf_download_tab_xpath).click()
        pdf_elements += driver.find_elements(By.XPATH, "//div[@class='attachment-item']/a")

        print(f'Found {len(pdf_elements)} PDFs in SKU {sku}')

        for pdf_element in pdf_elements:
            url = pdf_element.get_attribute('href')
            response = requests.get(url)

            nested_dir = f'{Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}/{sku}'
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
    with open(f'{Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_UK}') as f:
        loaded_links = json.load(f)

    counter = begin_from
    try:
        for link in loaded_links[begin_from:]:
            sku = Util.get_sku_from_link(DRIVER, link, 'UK')

            found = download_pdfs_of_sku(DRIVER, sku)
            print(f'DOWNLOADED {found} PDFS FROM : {link}  {counter + 1}/{len(loaded_links)}')
            counter += 1
    except KeyError:
        print("Error en la descarga de PDFs. Reintentando...")
        time.sleep(Util.PDF_DOWNLOAD_DELAY)
        begin_items_PDF_download(counter)


def begin_items_info_extraction(start_from):
    """
    Begins item info extraction.

    Parameters:
    start_from (int): The index to start extraction from.
    """
    # Load links from JSON file
    links = Util.load_json_data(f'{Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_UK}')

    products_data = []
    counter = start_from

    try:
        for link in links[start_from:]:
            products_data.append(scrape_item(DRIVER, SUBCATEGORIES_IDS, link))
            counter += 1
            print(f'{counter}/{len(links)}\n')

            # Save each X to a JSON
            if counter % JSON_DUMP_FREQUENCY == 0 or counter == len(links):
                filename = f'{Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}/{Util.ITEMS_INFO_FILENAME_TEMPLATE.format(counter)}'
                Util.dump_to_json(products_data, filename)

                # Dump lighter version of json
                dump_product_info_lite(products_data, counter)

                products_data.clear()

    except:
        time.sleep(2)
        products_data.clear()
        begin_items_info_extraction(counter - counter % JSON_DUMP_FREQUENCY)


def dump_product_info_lite(products_data, counter):
    for product in products_data:
        del product['imgs'], product['icons'], product['videos']

    Util.dump_to_json(products_data, f"{Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCT_INFO_LITE}/{Util.ITEMS_INFO_LITE_FILENAME_TEMPLATE.format(counter)}")
    print('DUMPED LITE PRODUCT INFO ')


# LINK EXTRACTION
if IF_EXTRACT_ITEM_LINKS:
    print(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_UK}')
    extracted_links = extract_all_links(DRIVER, CATEGORIES_LINKS)  # EXTRACTION LINKS TO A set()
    Util.dump_to_json(list(extracted_links), f'{Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_UK}')  # DUMPING LINKS TO JSON
    print(f'FINISHED LINK EXTRACTION TO {Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCTS_LINKS_FILE_UK}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    print(f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}')
    begin_items_info_extraction(0)  # EXTRACTION OF ITEMS INFO TO VTAC_PRODUCT_INFO
    print(f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCTS_INFO_DIR}')

# PDF DL
if IF_DL_ITEM_PDF:
    print(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}')
    begin_items_PDF_download()
    print(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_UK_DIR}/{Util.VTAC_PRODUCT_PDF_DIR}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    print(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(Util.VTAC_UK_DIR)
    print(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

DRIVER.close()
