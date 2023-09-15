import base64
import json
import os
import re
import time
from datetime import datetime

import pandas as pd
import requests
from googletrans import Translator
from selenium.common import NoSuchElementException
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
import logging

os.environ['path'] += r';dlls/'
import cairosvg


class Util:
    DATETIME = datetime.now().strftime("%m-%d-%Y, %Hh %Mmin %Ss")

    JSON_DUMP_FREQUENCY = 25

    VTAC_PRODUCT_PDF_DIR = 'VTAC_PRODUCT_PDF'
    VTAC_PRODUCTS_INFO_DIR = 'VTAC_PRODUCT_INFO'
    VTAC_PRODUCT_MEDIA_DIR = 'VTAC_PRODUCT_MEDIA'

    VTAC_COUNTRY_DIR = {
        'es': 'vtac_spain',
        'uk': 'vtac_uk',
        'ita': 'vtac_italia'
    }

    PDF_DOWNLOAD_DELAY = 2
    PRODUCT_LINK_EXTRACTION_DELAY = 2

    VTAC_PRODUCTS_LINKS_FILE = {
        'es': 'LINKS/VTAC_PRODUCTS_LINKS_ES.json',
        'uk': 'LINKS/VTAC_PRODUCTS_LINKS_UK.json',
        'ita': 'LINKS/VTAC_PRODUCTS_LINKS_ITA.json'
    }

    NEW_VTAC_PRODUCTS_LINKS_FILE = {
        'es': 'LINKS/NEW_VTAC_PRODUCTS_LINKS_ES.json',
        'uk': 'LINKS/NEW_VTAC_PRODUCTS_LINKS_UK.json',
        'ita': 'LINKS/NEW_VTAC_PRODUCTS_LINKS_ITA.json'
    }

    LOG_FILE_PATH = {
        'es': 'logs/es/es_{}.log',
        'uk': 'logs/uk/uk_{}.log',
        'ita': 'logs/ita/ita_{}.log',
    }

    MERGER_LOG_FILE_PATH = 'logs/datamerger/merge_{}.log'
    ODOO_IMPORT_LOG_FILE_PATH = 'logs/odooimport/import_{}.log'

    VTAC_PRODUCTS_FIELDS_FILE = 'VTAC_PRODUCTS_FIELDS.json'
    ITEMS_INFO_FILENAME_TEMPLATE = 'VTAC_PRODUCTS_INFO_{}.json'
    ITEMS_MEDIA_FILENAME_TEMPLATE = 'VTAC_PRODUCTS_MEDIA_{}.json'

    NOT_TO_EXTRACT_FIELDS = ('list_price', 'volume', 'weight', 'name', 'kit', 'accesorios', 'imgs', 'videos', 'icons')
    MEDIA_FIELDS = ('imgs', 'icons', 'videos')

    @staticmethod
    def setup_logger(target_file, name):
        # Create or get a logger
        logger = logging.getLogger(name)

        # Set log level
        logger.setLevel(logging.DEBUG)

        # Create a file handler
        fh = logging.FileHandler(target_file)
        fh.setLevel(logging.DEBUG)

        # Create a console handler and set its logging level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Create a formatter and set the formatter for the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        # Add the handlers to logger
        logger.addHandler(fh)
        logger.addHandler(console_handler)

        return logger

    @staticmethod
    def dump_to_json(dump, filename):
        """
            Dumps data to a JSON file.

            Parameters:
            data (list): A list of data to be dumped to JSON.
            filename (str): Name of the JSON file.
            """
        with open(filename, 'w') as file:
            json.dump(dump, file)
            print(f'Items extracted to JSON successfully: {filename}\n')

    @staticmethod
    def translate_from_to_spanish(_from, text):
        """
        Translates Italian text to Spanish using Google Translate.

        Parameters:
        text (str): The text in Italian.

        Returns:
        str: The translated text in Spanish.
        """
        try:
            # If text is empty, do nothing
            if len(text) < 1:
                return text

            translator = Translator()
            detected_language = translator.detect(text).lang

            if detected_language == _from or _from == 'detect':
                translation = translator.translate(text, src=detected_language, dest='es')
                return translation.text
        except:
            print('ERROR TRANSLATING TEXT. Retrying...')
            time.sleep(3)
            return Util.translate_from_to_spanish(_from, text)

        return text

    @staticmethod
    def src_to_base64(src):
        response = requests.get(src)
        return base64.b64encode(response.content).decode('utf-8')

    @staticmethod
    def get_sku_from_link(driver, link, country):
        try:
            driver.get(link)
        except TimeoutException:
            time.sleep(5)
            return Util.get_sku_from_link(driver, link, country)

        if country.upper() == 'ITA':
            return Util.get_sku_from_link_ita(driver)
        elif country.upper() == 'UK':
            return Util.get_sku_from_link_uk(driver)
        elif country.upper() == 'ES':
            return Util.get_sku_from_link_es(driver)
        else:
            raise Exception(f'Invalid country : {country}')

    @staticmethod
    def get_sku_from_link_ita(driver):
        link = driver.current_url
        return str(link).split('/')[6]

    @staticmethod
    def get_sku_from_link_uk(driver):
        try:
            return driver.find_element(By.XPATH,
                                       "/html/body/div[3]/main/div[4]/div/div/section[1]/div/div/div[2]/div[2]/div[1]").text.split(
                " ")[1]
        except NoSuchElementException:
            from vtac_uk.scraper_uk import ScraperVtacUk
            ScraperVtacUk.logger.error("ERROR getting SKU. Retrying...")
            time.sleep(5)
            return Util.get_sku_from_link(driver, driver.current_url, 'UK')

    @staticmethod
    def get_sku_from_link_es(driver):
        try:
            return driver.find_element(By.XPATH, "//div[@class='sku-inner']").text.split(' ')[1]
        except NoSuchElementException:
            from vtac_spain.scrapper_es import ScraperVtacSpain
            ScraperVtacSpain.logger.error("ERROR getting SKU. Retrying...")
            time.sleep(5)
            return Util.get_sku_from_link(driver, driver.current_url, 'ES')

    @staticmethod
    def load_json_data(file_path):
        """
        Loads JSON data from a given file path.

        Parameters:
        file_path (str): Path to the JSON file.

        Returns:
        list: A list of data loaded from the JSON file.
        """
        with open(file_path) as file:
            return json.load(file)

    @staticmethod
    def get_nested_directories(path):
        directories = []
        for root, dirs, _ in os.walk(path):
            for name in dirs:
                directories.append(os.path.join(root, name))
        return directories

    @staticmethod
    def get_all_files_in_directory(directory_path):
        all_files = []
        for root, dirs, files in os.walk(directory_path):
            for f in files:
                path = os.path.join(root, f)
                all_files.append(path)
        return all_files

    @staticmethod
    def format_field_odoo(field):
        # No need to format default fields
        if Util.NOT_TO_EXTRACT_FIELDS.__contains__(field):
            return field
        replacements = [
            (" ", "_"),
            ("(", ""),
            (")", ""),
            ("-", "_"),
            ("é", "e"),
            ("á", "a"),
            ("í", "i"),
            ("ó", "o"),
            ("ú", "u"),
            ("/", "_"),
            (".", "_"),
            ("ñ", "n"),
            ("%", ""),
            (",", ""),
            ("°", ""),
            ("'", "e_"),
            ("__", "_")
        ]
        formatted_field = field.lower()
        for search, replace in replacements:
            formatted_field = formatted_field.replace(search, replace)
        return f'x_{formatted_field}'[:61]

    @staticmethod
    def extract_distinct_fields_to_excel(directory_path):
        file_list = Util.get_all_files_in_directory(f'{directory_path}/{Util.VTAC_PRODUCTS_INFO_DIR}')
        json_data = []
        fields = set()

        for file_path in file_list:
            with open(file_path, "r", encoding='ISO-8859-1') as file:
                json_data.extend(json.load(file))

        for product in json_data:
            for attr in product.keys():
                # Filter out non-custom fields
                if attr not in Util.NOT_TO_EXTRACT_FIELDS:
                    fields.add(attr)

        excel_dicts = []

        print(f'FOUND {len(fields)} DISTINCT FIELDS')

        for field in fields:
            excel_dicts.append(
                {'Nombre de campo': Util.format_field_odoo(field),
                 'Etiqueta de campo': field,
                 'Modelo': 'product.template',
                 'Tipo de campo': 'texto',
                 'Indexado': True,
                 'Almacenado': True,
                 'Sólo lectura': False,
                 'Modelo relacionado': ''
                 }
            )

        Util.dump_to_json(excel_dicts, f'{directory_path}/{Util.VTAC_PRODUCTS_FIELDS_FILE}')

        # Read the JSON file
        data = pd.read_json(f'{directory_path}/{Util.VTAC_PRODUCTS_FIELDS_FILE}')

        # Write the DataFrame to an Excel file
        excel_file_path = f"{directory_path}/DISTINCT_FIELDS_EXCEL.xlsx"
        data.to_excel(excel_file_path,
                      index=False)  # Set index=False if you don't want the DataFrame indices in the Excel file

    @staticmethod
    def begin_items_PDF_download(scraper, links_path, downloads_path, country, logger, begin_from=0):
        with open(links_path) as f:
            loaded_links = json.load(f)

        pdf_existing_dirs_sku = [path.split('\\')[-1] for path in Util.get_nested_directories(downloads_path)]

        counter = begin_from
        try:
            for link in loaded_links[begin_from:]:
                counter += 1
                sku = Util.get_sku_from_link(scraper.DRIVER, link, country)

                # Check if sku directory exists and has the same number of files as the number of files
                if pdf_existing_dirs_sku.__contains__(sku):
                    count_downloaded = len(Util.get_all_files_in_directory(f'{downloads_path}/{sku}'))
                    count_existing = scraper.count_pdfs_of_link(link)

                    if count_existing == count_downloaded:
                        logger.info(f'SKIPPING SKU {sku} AS IT\'S FILES HAVE ALREADY BEEN DOWNLOADED')
                        continue

                found = scraper.download_pdfs_of_sku(scraper.DRIVER, sku)
                logger.warn(f'DOWNLOADED {found} PDFS FROM : {link}  {counter + 1}/{len(loaded_links)}')
        except:
            logger.error("Error en la descarga de PDFs. Reintentando...")
            time.sleep(5)
            Util.begin_items_PDF_download(scraper, links_path, downloads_path, country, logger, counter)

    @staticmethod
    def begin_items_info_extraction(scraper, links_path, extraction_dir, logger, start_from=0):
        """
        Begins item info extraction.

        Parameters:
        start_from (int): The index to start extraction from.
        """
        # Load links from JSON file
        links = Util.load_json_data(links_path)

        products_data = []
        counter = start_from

        try:
            for link in links[start_from:]:
                products_data.append(
                    scraper.scrape_item(scraper.DRIVER, link, scraper.SUBCATEGORIES))
                counter += 1
                logger.info(f'{counter}/{len(links)}\n')

                # Save each X to a JSON
                if counter % Util.JSON_DUMP_FREQUENCY == 0 or counter == len(links):
                    filename = f'{extraction_dir}/{Util.ITEMS_INFO_FILENAME_TEMPLATE.format(counter)}'
                    Util.dump_to_json(products_data, filename)

                    # Dump lighter version of json
                    Util.dump_product_info_lite(products_data, counter, scraper)

                    products_data.clear()
        except:
            logger.error('ERROR con extracción de información de productos. Reintentando...')
            time.sleep(2)
            products_data.clear()
            Util.begin_items_info_extraction(scraper, links_path, extraction_dir, logger,
                                             counter - counter % Util.JSON_DUMP_FREQUENCY)

    @staticmethod
    def dump_product_media(products_data, counter, scraper):
        for product in products_data:
            for field in Util.MEDIA_FIELDS:
                del product[field]

        Util.dump_to_json(products_data,f"{Util.VTAC_COUNTRY_DIR[scraper.COUNTRY]}/{Util.VTAC_PRODUCT_MEDIA_DIR}/{Util.ITEMS_MEDIA_FILENAME_TEMPLATE.format(counter)}")
        scraper.logger.info(f'DUMPED {len(products_data)} PRODUCTS MEDIA')

    # Replace <use> tags with the referenced element for cairosvg to work
    @staticmethod
    def resolve_svg_use_tags(match, svg_html):
        use_tag = match.group(0)
        href_attr = re.search(r'xlink:href="(#\w+)"', use_tag)
        if href_attr:
            referenced_id = href_attr.group(1)
            referenced_element = re.search(fr'<(\w+) id="{referenced_id[1:]}"(.*?)<\/\1>', svg_html, re.DOTALL)
            if referenced_element:
                return referenced_element.group(0)
        return use_tag

    @staticmethod
    def remove_defs_tags(svg_html):
        # Use regular expression to find and remove <defs> tags and their contents
        cleaned_svg = re.sub(r'<defs>.*?</defs>', '', svg_html, flags=re.DOTALL)
        return cleaned_svg

    @staticmethod
    def svg_to_base64(svg_html, logger):
        try:
            # Replace <use> tags in the SVG content
            svg_resolved_html = Util.remove_defs_tags(re.sub(r'<use .*?<\/use>', lambda match: Util.resolve_svg_use_tags(match, svg_html), svg_html, flags=re.DOTALL))

            # Convert the SVG to a PNG image using cairosvg
            png_data = cairosvg.svg2png(bytestring=svg_resolved_html.encode())

            # return the image as a base64 string
            return base64.b64encode(png_data).decode('utf-8')
        except:
            logger.error('ERROR CONVERTING SVG TO BASE64. Retrying...')
            time.sleep(10)
            return Util.svg_to_base64(svg_html, logger)
