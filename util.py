import base64
import json
import os
import requests
from googletrans import Translator
from selenium.webdriver.common.by import By


class Util:
    VTAC_PRODUCT_PDF_DIR = 'VTAC_PRODUCT_PDF'
    VTAC_PRODUCTS_INFO_DIR = 'VTAC_PRODUCT_INFO'
    VTAC_PRODUCT_INFO_LITE = 'VTAC_PRODUCT_INFO_LITE'

    VTAC_ES_DIR = 'vtac_spain'
    VTAC_ITA_DIR = 'vtac_italia'
    VTAC_UK_DIR = 'vtac_uk'

    PDF_DOWNLOAD_DELAY = 2
    PRODUCT_LINK_EXTRACTION_DELAY = 2

    VTAC_PRODUCTS_LINKS_FILE_ITA = 'VTAC_PRODUCTS_LINKS_ITA.json'
    VTAC_PRODUCTS_LINKS_FILE_ES = 'VTAC_PRODUCTS_LINKS_ES.json'
    VTAC_PRODUCTS_LINKS_FILE_UK = 'VTAC_PRODUCTS_LINKS_UK.json'

    VTAC_PRODUCTS_FIELDS_FILE = 'VTAC_PRODUCTS_FIELDS.json'
    ITEMS_INFO_FILENAME_TEMPLATE = 'VTAC_PRODUCTS_INFO_{}.json'
    ITEMS_INFO_LITE_FILENAME_TEMPLATE = 'VTAC_PRODUCTS_INFO_LITE_{}.json'

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
            translator = Translator()

            detected_language = translator.detect(text).lang

            if detected_language == _from:
                translation = translator.translate(text, src=detected_language, dest='es')
                return translation.text
        except:
            pass

        return text

    @staticmethod
    def src_to_base64(src):
        response = requests.get(src)
        return base64.b64encode(response.content).decode('utf-8')

    @staticmethod
    def get_sku_from_link_ita(link):
        return str(link).split('/')[6]

    @staticmethod
    def get_sku_from_link_uk(driver):
        return driver.find_element(By.XPATH, "/html/body/div[3]/main/div[4]/div/div/section[1]/div/div/div[2]/div[2]/div[1]").text.split(" ")[1]

    @staticmethod
    def get_sku_from_link_es(driver):
        return driver.find_element(By.XPATH, "//div[@class='sku-inner']").text

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
        field = field.lower().replace(" ", "_") \
            .replace("(", "") \
            .replace(")", "") \
            .replace("-", "_") \
            .replace("é", "e") \
            .replace("á", "a") \
            .replace("í", "i") \
            .replace("ó", "o") \
            .replace("ú", "u") \
            .replace("/", "_") \
            .replace(".", "_") \
            .replace("ñ", "n")
        return f'x_{field}'[:61]
