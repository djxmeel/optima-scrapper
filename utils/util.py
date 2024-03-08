import base64
import copy
import io
import json
import os
import random
import re
import time
import shutil
from datetime import datetime
from io import BytesIO

import pypdf
from PIL import Image


import openpyxl
import pandas as pd
import requests
from pypdf.errors import PdfReadError

from googletrans import Translator
from httpcore import ReadTimeout
from reportlab.pdfgen import canvas
from selenium.common import NoSuchElementException
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from urllib3.exceptions import ReadTimeoutError

os.environ['path'] += r';dlls/'
import cairosvg

class Util:
    DATETIME = datetime.now().strftime("%m-%d-%Y, %Hh %Mmin %Ss")

    JSON_DUMP_FREQUENCY = 25

    PDF_DOWNLOAD_DELAY = 2
    PRODUCT_LINK_EXTRACTION_DELAY = 2

    PRODUCT_INFO_FILENAME_TEMPLATE = 'PRODUCTS_INFO_{}.json'
    PRODUCT_MEDIA_FILENAME_TEMPLATE = 'PRODUCTS_MEDIA_{}.json'

    # The fields kept in ODOO as custom fields
    ODOO_CUSTOM_FIELDS = ('url', 'Código de familia')
    # Default fields supported by Odoo (not custom)
    ODOO_SUPPORTED_FIELDS = ('list_price', 'volume', 'weight', 'name', 'website_description', 'default_code', 'barcode', 'product_brand_id', 'invoice_policy', 'detailed_type', 'show_availability', 'allow_out_of_stock_order', 'available_threshold', 'out_of_stock_message', 'description_purchase')
    # Media fields
    MEDIA_FIELDS = ('imgs', 'icons', 'videos')

    ATTACHMENT_NAME_REPLACEMENTS_JSON_PATH_ITA = 'data/common/json/attachment_renames/ATTACHMENT_NAME_RENAMES_ITA.json'
    ATTACHMENT_NAME_REPLACEMENTS_JSON_PATH_ES = 'data/common/json/attachment_renames/ATTACHMENT_NAME_RENAMES_ES.json'
    ATTACHMENT_NAME_REPLACEMENTS_JSON_PATH_UK = 'data/common/json/attachment_renames/ATTACHMENT_NAME_RENAMES_UK.json'

    SKUS_CATALOGO_Q12024_FILE_PATH = 'data/common/excel/skus_catalogo_Q1_2024.xlsx'
    CORRECT_NAMES_EXCEL_PATH = 'data/common/excel/product_correct_names.xlsx'

    ODOO_FETCHED_PRODUCTS = []

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
    def translate_from_to_spanish(_from, text, to='es'):
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
                translation = translator.translate(text, src=detected_language, dest=to)
                return translation.text
        except (TimeoutException, ReadTimeoutError, ReadTimeout):
            print('TRANSLATION TIMED OUT. Retrying...')
            time.sleep(3)
            return Util.translate_from_to_spanish(_from, text)
        except (AttributeError ,TypeError, ValueError):
            print(f'{text} NOT TRANSLATABLE. SKIPPING...')

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
            raise Exception(f'Invalid country: {country}')

    @staticmethod
    def get_sku_from_link_ita(driver, link=None):
        if link:
            return str(link).split('/')[6]
        return str(driver.current_url).split('/')[6]

    @staticmethod
    def get_sku_from_link_uk(driver, link=None):
        if link:
            time.sleep(1)
            driver.get(link)
        try:
            return driver.find_element(By.XPATH,"//main/div[3]/div/div/section[1]/div/div/div[2]/div[2]/div[1]").text.split(" ")[1]
        except NoSuchElementException:
            return None

    @staticmethod
    def get_sku_from_link_es(driver, link=None):
        try:
            if link:
                driver.get(link)
            return driver.find_element(By.XPATH, "//div[@class='sku-inner']").text.split(' ')[1]
        except NoSuchElementException:
            from scrapers.scraper_vtac_es import ScraperVtacSpain
            ScraperVtacSpain.logger.error("ERROR getting SKU. Retrying...")
            time.sleep(5)
            return Util.get_sku_from_link(driver, driver.current_url, 'ES')

    @staticmethod
    def get_internal_ref_from_sku(sku):
        try:
            return f'VS{int(sku) * 2}'
        except ValueError:
            if "-" in sku:
                sku_split = sku.split('-')
                if sku_split[0].isdigit():
                    return f'VS{int(sku_split[0]) * 2}-{sku_split[1]}'
                elif sku_split[1].isdigit():
                    return f'VS{int(sku_split[1]) * 2}-{sku_split[0]}'
            return None

    @staticmethod
    def load_json(file_path):
        """
        Loads JSON data from a given file path.

        Parameters:
        file_path (str): Path to the JSON file.

        Returns:
        list: A list of data loaded from the JSON file.
        """
        try:
            with open(file_path, encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f'File not found: {file_path}')
            return []


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
            for f in files:
                path = os.path.join(root, f)
                all_files.append(path)
        return all_files

    @staticmethod
    def load_data_in_dir(directory):
        loaded_data = []

        file_list = Util.get_all_files_in_directory(directory)

        for file_path in file_list:
            loaded_data += Util.load_json(file_path)

        return loaded_data

    @staticmethod
    def get_unique_skus_from_dir(directory):
        return set(product['default_code'] for product in Util.load_data_in_dir(directory))

    @staticmethod
    def get_unique_skus_from_dictionary(dictionary):
        return set(product['default_code'] for product in dictionary)

    @staticmethod
    def format_odoo_custom_field_name(field):
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
                logger.warn(f'DOWNLOADED {found} PDFS FROM: {link}  {counter + 1}/{len(loaded_links)}')
        except TimeoutError:
            logger.error("Error en la descarga de PDFs. Reintentando...")
            time.sleep(5)
            Util.begin_items_pdf_download(scraper, links_path, downloads_path, logger, counter)

    @staticmethod
    def begin_items_uk_specsheets_download(scraper, links_path, logger, begin_from=0):
        with open(links_path) as f:
            loaded_links = json.load(f)

        counter = begin_from

        try:
            for link in loaded_links[begin_from:]:
                counter += 1

                sku = Util.get_sku_from_link(scraper.DRIVER, link, scraper.COUNTRY)

                if scraper.COUNTRY == 'uk':
                    scraper.download_specsheet_of_sku(scraper.DRIVER, sku)
        except:
            logger.error("Error en la descarga de fichas técnicas. Reintentando...")
            time.sleep(5)
            Util.begin_items_uk_specsheets_download(scraper, links_path, logger, counter)

    @staticmethod
    def begin_items_info_extraction(scraper, links_path, data_extraction_dir, media_extraction_dir, logger, if_only_new=False, begin_from=0):
        """
        Begins item info extraction.

        Parameters:
        start_from (int): The index to start extraction from.
        """
        # Load links from JSON file
        links = Util.load_json(links_path)

        skipped = 0

        products_data = []
        counter = begin_from

        # Different links but same product
        duplicate_links = []

        try:
            for link in links[begin_from:]:
                # Skip duplicate links for ES
                if scraper.COUNTRY == 'es':
                    if link in duplicate_links:
                        skipped += 1
                        continue

                    for dup in scraper.get_duplicate_product_links(links_path, link):
                        duplicate_links.append(dup)

                product = scraper.scrape_item(scraper.DRIVER, link, scraper.SPECS_SUBCATEGORIES)

                # If product is None, it's SKU contains letters (Not V-TAC)
                if not product:
                    skipped+=1
                    logger.warn(f'Failed to scrape product with link: {link}. Skipping...')
                    continue

                products_data.append(product)
                counter += 1
                logger.info(f'{counter}/{len(links)}\n')

                # Save each X to a JSON
                if counter % Util.JSON_DUMP_FREQUENCY == 0 or counter == len(links) - skipped:
                    data_filename = f'{data_extraction_dir}/{Util.PRODUCT_INFO_FILENAME_TEMPLATE.format(counter)}'
                    media_filename = f'{media_extraction_dir}/{Util.PRODUCT_MEDIA_FILENAME_TEMPLATE.format(counter)}'

                    products_media_only = Util.get_products_media(products_data, scraper)

                    Util.dump_to_json(products_data, data_filename, exclude=Util.MEDIA_FIELDS)
                    # Dump PRODUCT MEDIA only
                    Util.dump_to_json(products_media_only, media_filename)

                    products_data.clear()

            if if_only_new:
                Util.append_new_scrape_to_old_scrape(scraper.PRODUCTS_INFO_PATH, scraper.NEW_PRODUCTS_INFO_PATH, Util.PRODUCT_INFO_FILENAME_TEMPLATE, exclude=Util.MEDIA_FIELDS)
                Util.append_new_scrape_to_old_scrape(scraper.PRODUCTS_MEDIA_PATH, scraper.NEW_PRODUCTS_MEDIA_PATH, Util.PRODUCT_MEDIA_FILENAME_TEMPLATE)
                # Remove new products files
                os.remove(scraper.NEW_PRODUCTS_LINKS_PATH)
        except (TimeoutError, TimeoutException) as e:
            logger.error('ERROR con extracción de información de productos. Reintentando...')
            logger.error(e.with_traceback(None))
            time.sleep(2)
            products_data.clear()
            Util.begin_items_info_extraction(scraper, links_path, data_extraction_dir, media_extraction_dir, logger, if_only_new,
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
            " / __ \\|  __ |__   __|_   _|  \\/  |   /\\      / ____|/ ____|  __ \\    /\\   |  __ \\|  __ \\|  ____|  __ \\\n" 
            "| |  | | |__) | | |    | | | \\  / |  /  \\    | (___ | |    | |__) |  /  \\  | |__) | |__) | |__  | |__) |\n"
            "| |  | |  ___/  | |    | | | |\\/| | / /\\ \\    \\___ \\| |    |  _  /  / /\\ \\ |  ___/|  ___/|  __| |  _  /\n" 
            "| |__| | |      | |   _| |_| |  | |/ ____ \\   ____) | |____| | \\ \\ / ____ \\| |    | |    | |____| | \\ \\\n" 
            " \\____/|_|      |_|  |_____|_|  |_/_/    \\_\\ |_____/ \\_____|_|  \\_/_/    \\_|_|    |_|    |______|_|  \\_\\\n")

    @staticmethod
    def get_chosen_country_from_menu(country_scrapers, if_extract_item_links, if_update, if_extract_item_info, if_only_new_items, if_dl_item_pdf):
        Util.print_title()
        # Prompt user to choose country
        while True:
            print("\nConfiguracion de scraping actual:\n"
                  f"\nExtracción de URLs: {if_extract_item_links}\n"
                  f"Extraer NOVEDADES: {if_update}\n"
                  f"\nScrapear información productos: {if_extract_item_info}\n"
                  f"Sólamente NOVEDADES: {if_only_new_items}\n"
                  f"\nScrapear descargables productos: {if_dl_item_pdf}\n")
            chosen_country = input(f'ELEGIR PAÍS PARA EL SCRAPING ({list(country_scrapers.keys())}) : ').strip().lower()
            if chosen_country in country_scrapers:
                if input(
                        f'¿Está seguro de que desea hacer scraping de "{chosen_country}"? (s/n) :').strip().lower() == 's':
                    break
            print("País no válido, inténtelo de nuevo")

        return chosen_country

    # TODO adapt to the new Excel structure (with the new columns)
    @classmethod
    def get_public_category_from_sku(cls, sku, public_categories_excel_path, logger):
        categories_sku = Util.load_excel_columns_in_dictionary_list(public_categories_excel_path)
        public_categories = []

        for category_sku in categories_sku:
            if str(sku) == str(category_sku['SKU']):
                public_categories.append(str(category_sku['CATEGORY ES']).strip())

        if not public_categories:
            logger.warn(f'{sku}: NO PUBLIC CATEGORIES FOUND')
        else:
            logger.info(f'{sku}: ASSIGNED PUBLIC CATEGORIES {public_categories} FROM CATALOG EXCEL')

        return public_categories


    @classmethod
    def get_public_category_from_name(cls, product_name, name_to_categ_json_path, logger=None):
        name_to_categ = Util.load_json(name_to_categ_json_path)
        samsung_categs_map = Util.load_json('data/common/json/SAMSUNG_CATEGORIES_MAP.json')

        categs = []

        for substr, categ in name_to_categ.items():
            if substr in product_name:
                if 'SAMSUNG' in product_name and categ in samsung_categs_map:
                    categ = samsung_categs_map[categ]
                categs.append(categ)

        if categs:
            if logger:
                logger.info(f'{product_name}: ASSIGNED PUBLIC CATEGORIES {categs} FROM NAME')
            else:
                print(f'{product_name}: ASSIGNED PUBLIC CATEGORIES {categs} FROM NAME')

        return categs


    @classmethod
    def get_priority_excel_skus(cls, file_path, column_letter, sheet_name=None):
        try:
            workbook = openpyxl.load_workbook(file_path)

            # If sheet_name is not specified, use the active sheet. Otherwise, use the specified sheet.
            sheet = workbook[sheet_name] if sheet_name else workbook.active

            # Extract data from the desired column
            data = [cell.value for cell in sheet[column_letter] if cell.value is not None]

            # Close the workbook and return the data
            workbook.close()
            return data
        except FileNotFoundError:
            print(f'File not found: {file_path}')
            return []


    @classmethod
    def load_excel_columns_in_dictionary_list(cls, file_path):
        # Read the Excel file using pandas
        df = pd.read_excel(file_path, engine='openpyxl')

        # Convert the DataFrame to dictionary
        result_dict = df.to_dict(orient='records')

        return result_dict

    @classmethod
    def get_website_product_count(cls):
        from scrapers.scraper_vtac_uk import ScraperVtacUk
        from scrapers.scraper_vtac_es import ScraperVtacSpain
        from scrapers.scraper_vtac_ita import ScraperVtacItalia

        scrapers = [
            ScraperVtacUk,
            ScraperVtacSpain,
            ScraperVtacItalia
        ]

        website_product_count = []
        for scraper in scrapers:
            website_product_count.append(
                {
                    'website': scraper.WEBSITE_NAME,
                    'count': len(cls.load_json(scraper.PRODUCTS_LINKS_PATH)),
                    'new': len(cls.load_json(scraper.NEW_PRODUCTS_LINKS_PATH)),
                    'local_count': len(cls.load_data_in_dir(scraper.PRODUCTS_INFO_PATH)),
                    'local_new': len(cls.load_data_in_dir(scraper.NEW_PRODUCTS_INFO_PATH))
                }
            )

        return website_product_count

    @classmethod
    def attachment_naming_replacements(cls, attachment_name, country):
        if country == 'es':
            replacements = Util.load_json(cls.ATTACHMENT_NAME_REPLACEMENTS_JSON_PATH_ES)
        elif country == 'uk':
            replacements = Util.load_json(cls.ATTACHMENT_NAME_REPLACEMENTS_JSON_PATH_UK)
        else:
            replacements = Util.load_json(cls.ATTACHMENT_NAME_REPLACEMENTS_JSON_PATH_ITA)


        for incorrect, replacement in replacements.items():
            if incorrect in attachment_name:
                attachment_name = attachment_name.replace(incorrect, replacement)

        return attachment_name

    @classmethod
    def randomize_barcode(cls, barcode):
        return f"{barcode}-{random.randrange(99)}"

    @classmethod
    def append_new_scrape_to_old_scrape(cls, product_data_path, new_product_data_path, file_template, exclude=None):
        all_products_data_filenames = Util.get_all_files_in_directory(product_data_path)

        if all_products_data_filenames:
            last_products_data_file = cls.find_last_product_data_file(all_products_data_filenames)
            new_products_data = Util.load_json(last_products_data_file) + Util.load_data_in_dir(new_product_data_path)
            old_product_count = (len(all_products_data_filenames) - 1) * Util.JSON_DUMP_FREQUENCY
            os.remove(last_products_data_file)
        else:
            new_products_data = Util.load_data_in_dir(new_product_data_path)
            old_product_count = 0

        counter = 0

        print(f'Appending {len(new_products_data)} new products to old scrape...')

        while True:
            if len(new_products_data) > Util.JSON_DUMP_FREQUENCY:
                counter += Util.JSON_DUMP_FREQUENCY
                data_filename = f'{product_data_path}/{file_template.format(old_product_count + counter)}'
                Util.dump_to_json(new_products_data[:Util.JSON_DUMP_FREQUENCY], data_filename, exclude=exclude)
                new_products_data = new_products_data[Util.JSON_DUMP_FREQUENCY:]
            else:
                data_filename = f'{product_data_path}/{file_template.format(old_product_count + counter + len(new_products_data))}'
                Util.dump_to_json(new_products_data, data_filename, exclude=exclude)
                break

        for file_name in os.listdir(new_product_data_path):
            # construct full file path
            file = new_product_data_path +'/'+ file_name
            if os.path.isfile(file):
                print('Deleting file:', file)
                os.remove(file)

    @classmethod
    def resize_image_b64(cls, image_b64, new_width):
        # Decode the base64 string
        decoded_image = base64.b64decode(image_b64)
        image = Image.open(BytesIO(decoded_image))

        # Calculate new height maintaining the aspect ratio
        original_width, original_height = image.size

        if original_width <= new_width:
            return image_b64

        new_height = int(new_width * original_height / original_width)

        # Resize the image
        resized_image = image.resize((new_width, new_height), Image.Resampling.NEAREST)

        # Convert the resized image back to base64
        buffer = BytesIO()
        resized_image.save(buffer, format="PNG")
        resized_b64 = base64.b64encode(buffer.getvalue()).decode()

        return resized_b64

    @classmethod
    def get_correct_name_from_excel(cls, excel_path, sku, original_name):
        line_dicts = Util.load_excel_columns_in_dictionary_list(excel_path)
        for line_dict in line_dicts:
            if str(sku) == str(line_dict['Referencia interna']):
                print(f'{sku}: ASSIGNED CORRECT NAME {line_dict["Nombre"]} FROM EXCEL')
                return line_dict['Nombre']
        return original_name

    @classmethod
    def find_last_product_data_file(cls, all_products_data_filenames):
        """
            Finds the last file in a list of files with format {any}_XXXX.json. 
            
            parameters:
                all_products_data_filenames: products data jsons names list.

            Returns:
                The last file in the list.
        """
        last_file = all_products_data_filenames[0]
        for file in all_products_data_filenames:
            if int(file.split('\\')[-1].split('_')[2].split('.')[0]) > int(
                    last_file.split('\\')[-1].split('_')[2].split('.')[0]):
                last_file = file
        return last_file

    @classmethod
    def convert_image_to_base64(cls, image_path):
        """
            Converts an image to base64 string

            Parameters:
                image_path: path to the image file

            Returns:
                :return: base64 string of the image
        """
        with Image.open(image_path) as image:
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()

    @classmethod
    def create_white_square_overlay(cls, position, size=(100, 100)):
        # Create a PDF in memory
        packet = io.BytesIO()
        c = canvas.Canvas(packet)
        c.setFillColorRGB(0, 0.807843137254902, 0.48627450980392156)  # White color
        c.rect(position[0], position[1], size[0], size[1], stroke=0, fill=1)
        c.save()

        packet.seek(0)
        return pypdf.PdfReader(packet)

    @classmethod
    def remove_elements_within_square(cls, pdf_path, position, size, output_pdf_path):
        # Read the input PDF
        try:
            input_pdf = pypdf.PdfReader(open(pdf_path, "rb"))
        except PdfReadError:
            print(f"ERROR READING {pdf_path}")
            return
        except FileNotFoundError:
            print(f"ERROR READING {pdf_path}")
            return

        # Create a new PDF to write the modified content
        output_pdf = pypdf.PdfWriter()

        # Create the white square overlay PDF
        overlay_pdf = cls.create_white_square_overlay(position, size)

        # Iterate through each page and apply the white square overlay
        for i in range(len(input_pdf.pages)):
            page = input_pdf.pages[i]
            if i == 0:
                page.merge_page(overlay_pdf.pages[0])
            output_pdf.add_page(page)

        # Write the modified content to a new file
        with open(output_pdf_path, "wb") as f:
            output_pdf.write(f)

    @classmethod
    def remove_hyperlinks_from_pdf(cls, input_pdf_path, output_pdf_path):
        # Read the input PDF
        try:
            input_pdf = pypdf.PdfReader(open(input_pdf_path, "rb"))
        except PdfReadError:
            print(f"ERROR READING {input_pdf_path}")
            return

        # Create a new PDF to write the modified content
        output_pdf = pypdf.PdfWriter()

        # Iterate through each page and remove annotations
        for i in range(len(input_pdf.pages)):
            page = input_pdf.pages[i]
            page[pypdf.generic.NameObject("/Annots")] = pypdf.generic.ArrayObject()
            output_pdf.add_page(page)

        # Write the modified content to a new file
        with open(output_pdf_path, "wb") as f:
            output_pdf.write(f)

    @classmethod
    def remove_hyperlinks_and_qr_code_from_pdfs(cls, parent_folder, position, size):
        unedited_specsheets = []

        for root, dirs, files in os.walk(parent_folder):
            for file in files:
                if file.lower().endswith('.pdf') and not file.__contains__('FICHA_TECNICA_SKU'):
                    input_pdf_path = os.path.join(root, file)
                    output_pdf_path = os.path.join(root, f"FICHA_TECNICA_SKU_{file}")
                    cls.remove_hyperlinks_from_pdf(input_pdf_path, output_pdf_path)
                    cls.remove_elements_within_square(output_pdf_path, position, size, output_pdf_path)
                    print(f"PROCESSED {input_pdf_path}")
                    unedited_specsheets.append(input_pdf_path)

        for specsheet in unedited_specsheets:
            os.remove(specsheet)

    @classmethod
    def remove_a_tags(cls, html_string):
        """
        Removes all <a> tags and their content from the given HTML string.

        :param html_string: A string containing HTML content.
        :return: A string with all <a> tags and their contents removed.
        """
        return re.sub(r'<a[^>]*>.*?</a>', '', html_string, flags=re.DOTALL)

    @classmethod
    def get_encoded_icons_from_excel(cls, icons_names):
        icons = []
        for icon_name in icons_names:
            if not icon_name:
                continue

            icon_name = str(icon_name).lower()
            icon_b64 = dict(Util.load_json(f'data/common/icons/icons_b64/{icon_name}.json'))
            icons.append(icon_b64[icon_name])
        return icons

    @classmethod
    def get_vtac_logo_icon_b64(cls):
        return Util.load_json(f'data/common/icons/icons_b64/vtaclogo.json')
