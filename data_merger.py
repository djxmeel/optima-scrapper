import json
from datetime import datetime

from util import Util


# TODO test this class
class DataMerger:
    # Creación del logger
    logger_path = Util.MERGER_LOG_FILE_PATH.format(datetime.now().strftime("%m-%d-%Y, %Hh %Mmin %Ss"))
    logger = Util.setup_logger(logger_path)
    print(f'LOGGER CREATED: {logger_path}')

    COUNTRY_DATA_DIR_PATHS = {
        'es': 'vtac_spain/VTAC_PRODUCT_INFO',
        'uk': 'vtac_uk/VTAC_PRODUCT_INFO',
        'ita': 'vtac_italia/VTAC_PRODUCT_INFO'
    }

    # Field priorities, 'default' is for fields that are not in this list
    FIELD_PRIORITIES = {
        'default': ['es', 'uk', 'ita'],
        'icons': ['uk', 'ita', 'es'],
        'imgs': ['uk', 'ita', 'es'],
        'descripcion': ['es', 'uk', 'ita'],
    }

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
            with open(file_path, "r") as file:
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

            for country in cls.FIELD_PRIORITIES['default']:
                # Stop at first found in priority order
                if product[country] is not None:
                    merged_product = product[country]
                    break

            for field in cls.FIELD_PRIORITIES.keys():
                if field == 'default':
                    continue
                for country in cls.FIELD_PRIORITIES[field]:
                    if product[country] is not None and field in product[country] and len(product[country][field]) > 0:
                        merged_product[field] = product[country][field]
                        break

            cls.merged_data.append(merged_product)

        return cls.merged_data

    @classmethod
    def extract_merged_data(cls):
        if len(cls.merged_data) < 1:
            cls.get_merged_data()

        for index in range(0, len(cls.merged_data), 50):
            Util.dump_to_json(cls.merged_data[index:index + 50], f"merged_data/VTAC_MERGED_INFO_{index + 50}.json")


DataMerger.extract_merged_data()
