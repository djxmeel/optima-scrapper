import json
import copy
from datetime import datetime

from util import Util


# TODO test this class
class DataMerger:
    # Creación del logger
    logger_path = Util.MERGER_LOG_FILE_PATH.format(datetime.now().strftime("%m-%d-%Y, %Hh %Mmin %Ss"))
    logger = Util.setup_logger(logger_path)
    print(f'LOGGER CREATED: {logger_path}')

    JSON_DUMP_FREQUENCY = 50
    JSON_DUMP_PATH_TEMPLATE = 'merged_data/VTAC_MERGED_INFO_{}.json'

    COUNTRY_DATA_DIR_PATHS = {
        'es': 'vtac_spain/VTAC_PRODUCT_INFO',
        'uk': 'vtac_uk/VTAC_PRODUCT_INFO',
        'ita': 'vtac_italia/VTAC_PRODUCT_INFO'
    }

    # Field priorities, 'default' is for fields that are not in this list
    FIELD_PRIORITIES = {
        'default': ['es', 'uk', 'ita'],
        'icons': ['uk', 'ita', 'es'],
        'imgs': ['ita', 'uk', 'es'],
        'descripcion': ['es', 'uk', 'ita'],
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

    @classmethod
    def load_all(cls):
        for country in cls.COUNTRY_DATA_DIR_PATHS.keys():
            cls.load_data_for_country(country)

    @classmethod
    def get_data(cls, country):
        return cls.data.get(country, None)

    @classmethod
    def get_product_from_country_sku(cls, sku, country):
        for product in cls.data[country]:
            if product["SKU"] == sku:
                print(f'Found product {sku} in {country}')
                return product
        return None

    @classmethod
    def get_merged_data(cls):
        cls.load_all()
        all_data = cls.data['es'] + cls.data['uk'] + cls.data['ita']
        unique_product_skus = set(product['SKU'] for product in all_data)

        for sku in unique_product_skus:
            product = {'es': cls.get_product_from_country_sku(sku, 'es'),
                       'uk': cls.get_product_from_country_sku(sku, 'uk'),
                       'ita': cls.get_product_from_country_sku(sku, 'ita')}
            merged_product = {}

            # First, deepcopy product from the first country in 'default' priority order
            for country in cls.FIELD_PRIORITIES['default']:
                # Stop at first found in priority order
                if product[country] is not None:
                    merged_product = copy.deepcopy(product[country])
                    break

            # Then, merge fields from other countries in priority order
            for field in cls.FIELD_PRIORITIES.keys():
                if field == 'default':
                    continue
                for country in cls.FIELD_PRIORITIES[field]:
                    if product.get(country) and product[country].get(field) and len(product[country][field]) > 0:
                        if type(product[country][field]) is list:
                            merged_product[field] = copy.deepcopy(product[country][field])
                            break
                        merged_product[field] = product[country][field]
                        cls.logger.info(f'Field {field} from {country} was merged into {merged_product["SKU"]}')
                        break

            for field_country in cls.COUNTRY_FIELDS_ALWAYS_KEEP:
                try:
                    if product[field_country['country']]:
                        field_to_keep = product[field_country['country']][field_country['field']]
                        if len(field_to_keep) > 0 and merged_product[field_country['field']] is not field_to_keep:
                            merged_product[field_country['field']] += field_to_keep
                            cls.logger.info(f'Field {field_country["field"]} from {field_country["country"]} was kept into {merged_product["SKU"]}')
                except KeyError:
                    pass

            cls.merged_data.append(merged_product)

        return cls.merged_data

    @classmethod
    def extract_merged_data(cls):
        if len(cls.merged_data) < 1:
            cls.get_merged_data()

        for index in range(0, len(cls.merged_data), cls.JSON_DUMP_FREQUENCY):
            Util.dump_to_json(cls.merged_data[index:index + cls.JSON_DUMP_FREQUENCY], cls.JSON_DUMP_PATH_TEMPLATE.format(index + cls.JSON_DUMP_FREQUENCY))


DataMerger.extract_merged_data()
