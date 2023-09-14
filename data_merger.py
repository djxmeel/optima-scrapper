import json
import copy
from datetime import datetime

from util import Util


class DataMerger:
    # Creación del logger
    logger_path = Util.MERGER_LOG_FILE_PATH.format(datetime.now().strftime("%m-%d-%Y, %Hh %Mmin %Ss"))
    logger = Util.setup_logger(logger_path)
    print(f'LOGGER CREATED: {logger_path}')

    JSON_DUMP_FREQUENCY = 10
    JSON_DUMP_PATH_TEMPLATE = 'merged_data/VTAC_PRODUCT_INFO/VTAC_MERGED_INFO_{}.json'
    MERGED_PRODUCT_INFO_DIR_PATH = 'merged_data/VTAC_PRODUCT_INFO'
    MERGED_DATA_DIR_PATH = 'merged_data'

    COUNTRY_DATA_DIR_PATHS = {
        'es': 'vtac_spain/VTAC_PRODUCT_INFO',
        'uk': 'vtac_uk/VTAC_PRODUCT_INFO',
        'ita': 'vtac_italia/VTAC_PRODUCT_INFO'
    }

    # Field priorities, 'default' is for fields that are not in this list
    FIELD_PRIORITIES = {
        'default': ('es', 'uk', 'ita'),
        'icons': ('uk', 'ita', 'es'),
        'imgs': ('ita', 'uk', 'es'),
        'descripcion': ('es', 'uk', 'ita'),
        'videos': ('uk', 'ita', 'es'),
    }

    # Fields to rename for common naming between countries
    FIELD_TO_MERGE = {
        "Código EAN": "EAN",
        'EAN Código': 'EAN',
        "Ciclos de encendido / apagado": "Ciclos de encendido/apagado",
        "Código de la Familia": "Código de familia",
        "Eficacia luminosa (lm/W)": "Eficacia luminosa",
        "Factor de potencia (FP)": "Factor de potencia",
        "FP": "Factor de potencia",
        "Flujo luminoso (lm)": "Flujo luminoso",
        "Flujo luminoso/m": "Flujo luminoso",
        "Garanzia": "Garantía",
        "Dimensión": "Dimensiones",
        "Dimensioni (AxLxP)": "Dimensiones",
        "Nombre de la marca": "Marca",
        'Ángulo de haz°': 'Ángulo de apertura',
        'Ángulo de haz': 'Ángulo de apertura',
        'Código de producto': 'Código de familia',
        'Las condiciones de trabajo': 'Temperaturas de trabajo',
        'Hora de inicio al 100% encendido': 'Tiempo de inicio al 100% encendido'
    }

    # Fields that are always kept from a country (field must be stored as a list in json)
    # Example: 'imgs' priority is ['uk', 'ita', 'es'] but we want to also keep all images from 'es' country
    COUNTRY_FIELDS_ALWAYS_KEEP = [
        {'country': 'es', 'field': 'imgs'}
    ]

    merged_data = []

    data = {
        'es': [],
        'uk': [],
        'ita': []
    }

    @classmethod
    def load_data_for_country(cls, country):
        file_list = Util.get_all_files_in_directory(cls.COUNTRY_DATA_DIR_PATHS[country])
        for file_path in file_list:
            with open(file_path, "r", encoding='utf-8') as file:
                cls.data[country] += json.load(file)

        # Filtering None
        # Merging fields when necessary
        cls.data[country] = [cls.merge_product_fields(p) for p in cls.data[country] if p is not None]

        cls.logger.info(f"FINISHED MERGING {country} PRODUCTS FIELDS")

    @classmethod
    def load_all(cls):
        for country in cls.COUNTRY_DATA_DIR_PATHS.keys():
            if len(cls.data.get(country)) > 0:
                if input(f"Data for {country} already loaded. Load again? (y/n): ") == 'n':
                    continue
                cls.data[country] = []
            cls.load_data_for_country(country)
        return cls

    @classmethod
    def get_data(cls, country):
        if len(cls.data.get(country)) > 0:
            return cls.data.get(country, None)
        else:
            cls.load_data_for_country(country)
            return cls.data.get(country, None)

    @classmethod
    def get_product_from_country_sku(cls, sku, country):
        for product in cls.data[country]:
            if product["sku"] == sku:
                return product
        return None

    @classmethod
    def merge_product_fields(cls, product):
        for key, value in cls.FIELD_TO_MERGE.items():
            if product.get(key):
                product[value] = product[key]
                del product[key]
        return product

    @classmethod
    def load_merged_data(cls, always_load=False):
        if not always_load and len(cls.merged_data) > 0:
            return cls.merged_data

        file_list = Util.get_all_files_in_directory(cls.MERGED_PRODUCT_INFO_DIR_PATH)
        for file_path in file_list:
            with open(file_path, "r", encoding='ISO-8859-1') as file:
                cls.merged_data += json.load(file)

        return cls.merged_data

    @classmethod
    def get_unique_skus_from_merged(cls):
        return set(product['sku'] for product in cls.load_merged_data())

    @classmethod
    def get_unique_skus_from_countries(cls):
        return set(product['sku'] for product in cls.data['es'] + cls.data['uk'] + cls.data['ita'])

    @classmethod
    def merge_data(cls):
        unique_product_skus = cls.get_unique_skus_from_countries()

        for sku in unique_product_skus:
            product = {'es': cls.get_product_from_country_sku(sku, 'es'),
                       'uk': cls.get_product_from_country_sku(sku, 'uk'),
                       'ita': cls.get_product_from_country_sku(sku, 'ita')}

            # Add empty spaces to SKU to make it 8 characters long for better readability
            sku += ' ' * (8 - len(sku))

            cls.logger.info(f'\n{sku} : ES: {int(product.get("es") is not None)} | UK: {int(product.get("uk") is not None)} | ITA: {int(product.get("ita") is not None)}')

            merged_product = {}

            # First, deepcopy product from the first country in 'default' priority order
            for country in cls.FIELD_PRIORITIES['default']:
                # Stop at first found in priority order
                if product[country] is not None:
                    merged_product = copy.deepcopy(product[country])
                    cls.logger.info(f'{sku}: DEFAULT -> {country}')
                    break

            # Then, merge fields from other countries in priority order
            for field in cls.FIELD_PRIORITIES.keys():
                if field == 'default':
                    continue
                for country in cls.FIELD_PRIORITIES[field]:
                    if product.get(country) and product[country].get(field) and len(product[country][field]) > 0:
                        if type(product[country][field]) is list:
                            merged_product[field] = copy.deepcopy(product[country][field])
                            cls.logger.info(f'{sku}: MERGE {country} -> {field}')
                            break
                        merged_product[field] = product[country][field]
                        cls.logger.info(f'{sku}: MERGE {country} -> {field}')
                        break

            for field_country in cls.COUNTRY_FIELDS_ALWAYS_KEEP:
                try:
                    if product[field_country['country']]:
                        field_to_keep = product[field_country['country']][field_country['field']]
                        if len(field_to_keep) > 0 and merged_product[field_country['field']] is not field_to_keep:
                            merged_product[field_country['field']] += field_to_keep
                            cls.logger.info(f'{sku}: KEEP {field_country["country"]} -> {field_country["field"]}')
                except KeyError:
                    pass

            cls.merged_data.append(merged_product)

    @classmethod
    def extract_merged_data(cls):
        if len(cls.merged_data) < 1:
            cls.load_all().merge_data()

        for index in range(0, len(cls.merged_data), cls.JSON_DUMP_FREQUENCY):
            counter = index + cls.JSON_DUMP_FREQUENCY

            if index + cls.JSON_DUMP_FREQUENCY > len(cls.merged_data):
                counter = len(cls.merged_data)

            Util.dump_to_json(cls.merged_data[index:counter], cls.JSON_DUMP_PATH_TEMPLATE.format(counter))
