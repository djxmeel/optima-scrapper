import base64
import copy
import json
import os
import re
import time
import shutil
from datetime import datetime

import pandas as pd
import requests
from googletrans import Translator
from selenium.common import NoSuchElementException
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By

os.environ['path'] += r';dlls/'
import cairosvg


class Util:
    DATETIME = datetime.now().strftime("%m-%d-%Y, %Hh %Mmin %Ss")

    JSON_DUMP_FREQUENCY = 10

    PDF_DOWNLOAD_DELAY = 2
    PRODUCT_LINK_EXTRACTION_DELAY = 2

    PRODUCT_INFO_FILENAME_TEMPLATE = 'PRODUCTS_INFO_{}.json'
    PRODUCT_MEDIA_FILENAME_TEMPLATE = 'PRODUCTS_MEDIA_{}.json'

    # The fields kept in ODOO as custom fields
    ODOO_CUSTOM_FIELDS = ('Sku', 'url', 'Código de familia', 'Marca')
    # Default fields supported by Odoo (not custom)
    ODOO_SUPPORTED_FIELDS = ('list_price', 'volume', 'weight', 'name', 'website_description', 'default_code', 'barcode')
    # Media fields
    MEDIA_FIELDS = ('imgs', 'icons', 'videos')


    @staticmethod
    def dump_to_json(dump, filename, exclude=None):
        """
            Dumps data to a JSON file.

            Parameters:
            data (list): A list of data to be dumped to JSON.
            filename (str): Name of the JSON file.
            """
        products_info = []
        if exclude:
            for item in dump:
                for field in exclude:
                    if field in item:
                        del item[field]
                products_info.append(item)
            dump = products_info


        with open(filename, 'w') as file:
            json.dump(dump, file)
            print(f'Items extracted to JSON successfully: {filename}\n')


    @staticmethod
    def get_products_media(products_data, scraper):
        products_media = []
        for product in products_data:
            product_media = {}
            # Get product SKU
            if 'default_code' in product:
                product_media['default_code'] = product['default_code']

            for field in Util.MEDIA_FIELDS:
                if field in product:
                    product_media[field] = copy.deepcopy(product[field])
            products_media.append(product_media)

        scraper.logger.info(f'DUMPED {len(products_media)} PRODUCTS MEDIA')
        return products_media


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
        except TimeoutException:
            print('TRANSLATION TIMED OUT. Retrying...')
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
            from scrapers.scraper_vtac_uk import ScraperVtacUk
            ScraperVtacUk.logger.error("ERROR getting SKU. Retrying...")
            time.sleep(5)
            return Util.get_sku_from_link(driver, driver.current_url, 'UK')


    @staticmethod
    def get_sku_from_link_es(driver):
        try:
            return driver.find_element(By.XPATH, "//div[@class='sku-inner']").text.split(' ')[1]
        except NoSuchElementException:
            from scrapers.scraper_vtac_es import ScraperVtacSpain
            ScraperVtacSpain.logger.error("ERROR getting SKU. Retrying...")
            time.sleep(5)
            return Util.get_sku_from_link(driver, driver.current_url, 'ES')


    @staticmethod
    def get_internal_ref_from_sku(sku):
        return f'VS{int(sku) * 2}'


    @staticmethod
    def load_json_data(file_path):
        """
        Loads JSON data from a given file path.

        Parameters:
        file_path (str): Path to the JSON file.

        Returns:
        list: A list of data loaded from the JSON file.
        """
        with open(file_path, encoding='utf-8') as file:
            return json.load(file)


    @staticmethod
    def get_nested_directories(path):
        directories = []
        for root, dirs, _ in os.walk(path):
            for name in dirs:
                directories.append(os.path.join(root, name))
        return directories


    @staticmethod
    def move_file_or_directory(src_path, dest_path, move_only_content=False):
        if not os.path.exists(src_path):
            print(f"Error: Source path '{src_path}' does not exist.")
            return

        if move_only_content and os.path.isdir(src_path):
            # Iterate over all the files and directories inside the source directory
            for item in os.listdir(src_path):
                src_item = os.path.join(src_path, item)
                dst_item = os.path.join(dest_path, item)

                # Move each item to the destination directory
                shutil.move(src_item, dst_item)
                print(f"'{item}' has been moved to '{dest_path}'.")
            return

        try:
            shutil.move(src_path, dest_path)
            print(f"'{src_path}' has been moved to '{dest_path}'.")
        except Exception as e:
            print(f"Error occurred while moving: {e}")


    @staticmethod
    def get_all_files_in_directory(directory_path):
        all_files = []
        for root, dirs, files in os.walk(directory_path):
            for f in sorted(files):
                path = os.path.join(root, f)
                all_files.append(path)
        return sorted(all_files)


    @staticmethod
    def load_data_in_dir(directory):
        loaded_data = []

        file_list = Util.get_all_files_in_directory(directory)

        for file_path in file_list:
            loaded_data += Util.load_json_data(file_path)

        return loaded_data


    @staticmethod
    def get_unique_skus_from_dir(directory):
         return set(product['Sku'] for product in Util.load_data_in_dir(directory))


    @staticmethod
    def get_unique_refs_from_dictionary(dictionary):
        return set(product['default_code'] for product in dictionary)


    @staticmethod
    def format_field_odoo(field):
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
    def extract_fields_example_to_excel(product_info_path, example_field_json_path, example_field_excel_path):
        file_list = Util.get_all_files_in_directory(product_info_path)
        json_data = []
        fields = set()
        ejemplos = {}
        urls = {}

        for file_path in file_list:
            with open(file_path, "r", encoding='ISO-8859-1') as file:
                json_data.extend(json.load(file))

        for product in json_data:
            for field in product.keys():
                fields.add(field)
                ejemplos[field] = f'{product["Sku"]} -> {product[field]}'
                urls[field] = product["url"]

        excel_dicts = []

        print(f'FOUND {len(fields)} DISTINCT FIELDS')

        for field in fields:
            if field in Util.ODOO_SUPPORTED_FIELDS:
                continue
            excel_dicts.append(
                {
                 'Etiqueta de campo': field,
                 'Ejemplo': ejemplos[field],
                 'URL': urls[field]
                 }
            )

        Util.dump_to_json(excel_dicts, example_field_json_path)

        # Read the JSON file
        data = pd.read_json(example_field_json_path)

        # Write the DataFrame to an Excel file
        excel_file_path = example_field_excel_path
        data.to_excel(excel_file_path,
                      index=False)  # Set index=False if you don't want the DataFrame indexes in the Excel file


    @staticmethod
    def extract_distinct_fields_to_excel(product_info_path, field_json_path, field_excel_path, extract_all=False):
        file_list = Util.get_all_files_in_directory(product_info_path)
        json_data = []
        fields = set()

        for file_path in file_list:
            with open(file_path, "r", encoding='ISO-8859-1') as file:
                json_data.extend(json.load(file))

        for product in json_data:
            for field in product.keys():
                # Filter out non-custom fields
                if extract_all or field in Util.ODOO_CUSTOM_FIELDS:
                    fields.add(field)

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
                 'Modelo relacionado': '',
                 }
            )

        Util.dump_to_json(excel_dicts, field_json_path)

        # Read the JSON file
        data = pd.read_json(field_json_path)

        # Write the DataFrame to an Excel file
        excel_file_path = field_excel_path
        data.to_excel(excel_file_path,
                      index=False)  # Set index=False if you don't want the DataFrame indices in the Excel file


    @staticmethod
    def begin_items_pdf_download(scraper, links_path, downloads_path, logger, begin_from=0):
        with open(links_path) as f:
            loaded_links = json.load(f)

        pdf_existing_dirs_sku = [path.split('\\')[-1] for path in Util.get_nested_directories(downloads_path)]

        counter = begin_from
        try:
            for link in loaded_links[begin_from:]:
                counter += 1
                sku = Util.get_sku_from_link(scraper.DRIVER, link, scraper.COUNTRY)

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
            Util.begin_items_pdf_download(scraper, links_path, downloads_path, logger, counter)


    @staticmethod
    def begin_items_info_extraction(scraper, links_path, data_extraction_dir, media_extraction_dir, logger, start_from=0):
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
                product = scraper.scrape_item(scraper.DRIVER, link, scraper.SPECS_SUBCATEGORIES)

                # If product is None, it's SKU contains letters (Not V-TAC)
                if not product:
                    continue

                products_data.append(product)
                counter += 1
                logger.info(f'{counter}/{len(links)}\n')

                # Save each X to a JSON
                if counter % Util.JSON_DUMP_FREQUENCY == 0 or counter == len(links):
                    data_filename = f'{data_extraction_dir}/{Util.PRODUCT_INFO_FILENAME_TEMPLATE.format(counter)}'
                    media_filename = f'{media_extraction_dir}/{Util.PRODUCT_MEDIA_FILENAME_TEMPLATE.format(counter)}'

                    products_media_only = Util.get_products_media(products_data, scraper)

                    Util.dump_to_json(products_data, data_filename, exclude=Util.MEDIA_FIELDS)
                    # Dump PRODUCT MEDIA only
                    Util.dump_to_json(products_media_only, media_filename)

                    products_data.clear()
        except:
            logger.error('ERROR con extracción de información de productos. Reintentando...')
            time.sleep(2)
            products_data.clear()
            Util.begin_items_info_extraction(scraper, links_path, data_extraction_dir, media_extraction_dir, logger,
                                             counter - counter % Util.JSON_DUMP_FREQUENCY)


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


    @staticmethod
    def get_elapsed_time(start_seconds, end_seconds):
        # Calculate the difference in seconds
        elapsed_seconds = end_seconds - start_seconds

        # Convert seconds to minutes and hours
        elapsed_minutes = elapsed_seconds // 60
        elapsed_hours = elapsed_minutes // 60
        remaining_minutes = elapsed_minutes % 60
        remaining_seconds = elapsed_seconds % 60

        return int(elapsed_hours), int(remaining_minutes), int(remaining_seconds)


    @staticmethod
    def print_title():
        print(
            "  ____  _____ _______ _____ __  __             _____  _____ _____           _____  _____  ______ _____\n"  
            " / __ \|  __ |__   __|_   _|  \/  |   /\      / ____|/ ____|  __ \    /\   |  __ \|  __ \|  ____|  __ \\\n" 
            "| |  | | |__) | | |    | | | \  / |  /  \    | (___ | |    | |__) |  /  \  | |__) | |__) | |__  | |__) |\n"
            "| |  | |  ___/  | |    | | | |\/| | / /\ \    \___ \| |    |  _  /  / /\ \ |  ___/|  ___/|  __| |  _  /\n" 
            "| |__| | |      | |   _| |_| |  | |/ ____ \   ____) | |____| | \ \ / ____ \| |    | |    | |____| | \ \\\n" 
            " \____/|_|      |_|  |_____|_|  |_/_/    \_\ |_____/ \_____|_|  \_/_/    \_|_|    |_|    |______|_|  \_\\\n")


    @classmethod
    def get_chosen_country_from_menu(cls, country_scrapers, if_extract_item_links, if_update, if_extract_item_info, if_only_new_items, if_dl_item_pdf, if_extract_distinct_items_fields):
        Util.print_title()
        # Prompt user to choose country
        while True:
            print("\nConfiguracion de scraping actual:\n"
                  f"\nExtracción de URLs : {if_extract_item_links}\n"
                  f"Extraer NOVEDADES : {if_update}\n"
                  f"\nScrapear información productos : {if_extract_item_info}\n"
                  f"Sólamente NOVEDADES : {if_only_new_items}\n"
                  f"\nScrapear descargables productos : {if_dl_item_pdf}\n"
                  f"\nExtraer campos : {if_extract_distinct_items_fields}\n")
            chosen_country = input(f'ELEGIR PAÍS PARA EL SCRAPING ({list(country_scrapers.keys())}) : ').strip().lower()
            if chosen_country in country_scrapers:
                if input(
                        f'¿Está seguro de que desea hacer scraping de "{chosen_country}"? (s/n) :').strip().lower() == 's':
                    break
            print("País no válido, inténtelo de nuevo")

        return chosen_country
