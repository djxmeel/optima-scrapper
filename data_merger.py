import json
from datetime import datetime

from util import Util


# TODO test this class
class DataMerger:
    # Creación del logger
    logger_path = Util.MERGER_LOG_FILE_PATH.format(datetime.now().strftime("%m-%d-%Y, %Hh %Mmin %Ss"))
    logger = Util.setup_logger(logger_path)
    print(f'LOGGER CREATED: {logger_path}')

    DATA_DIR_PATHS = {
        'es': 'vtac_spain/VTAC_PRODUCT_INFO',
        'uk': 'vtac_uk/VTAC_PRODUCT_INFO',
        'ita': 'vtac_italia/VTAC_PRODUCT_INFO'
    }

    merged_data = []

    data = {
        'es': [],
        'uk': [],
        'ita': []
    }

    @classmethod
    def load_data_for_country(cls, country):
        file_list = Util.get_all_files_in_directory(cls.DATA_DIR_PATHS[country])
        for file_path in file_list:
            with open(file_path, "r") as file:
                cls.data[country] += json.load(file)

    @classmethod
    def load_all(cls):
        for country in cls.DATA_DIR_PATHS.keys():
            cls.load_data_for_country(country)

    @classmethod
    def get_data(cls, country):
        return cls.data.get(country, None)

    @classmethod
    def product_exists(cls, sku, country):
        for product in cls.data[country]:
            if product["SKU"] == sku:
                return True, product
        return False, None

    @classmethod
    def get_merged_data(cls):
        cls.load_all()
        all_data = cls.data['es'] + cls.data['uk'] + cls.data['ita']
        unique_product_skus = set(product['SKU'] for product in all_data)

        for sku in unique_product_skus:
            exists_in_es, product_from_es = cls.product_exists(sku, 'es')
            exists_in_uk, product_from_uk = cls.product_exists(sku, 'uk')
            exists_in_ita, product_from_ita = cls.product_exists(sku, 'ita')
            merged_product = None

            # If exists in spain, add it to the merged data
            if exists_in_es:
                # If exists in ita, add the images from ita to the merged data
                if exists_in_ita:
                    if len(product_from_ita["imgs"]) > 1:
                        product_from_es["imgs"] += product_from_ita["imgs"]
                    if len(product_from_es["descripcion"]) < 1:
                        if exists_in_uk and len(product_from_uk["descripcion"]) > 1:
                            product_from_es["descripcion"] = product_from_uk["descripcion"]
                        elif len(product_from_ita["descripcion"]) > 1:
                            product_from_es["descripcion"] = product_from_ita["descripcion"]
                # If not exists in ita, add the images from uk to the merged data
                elif exists_in_uk:
                    if len(product_from_uk["imgs"]) > 1:
                        product_from_es["imgs"] += product_from_uk["imgs"]
                    if len(product_from_es["descripcion"]) < 1:
                        if len(product_from_uk["descripcion"]) > 1:
                            product_from_es["descripcion"] = product_from_uk["descripcion"]
                        else:
                            product_from_es["descripcion"] = product_from_ita["descripcion"]
                merged_product = product_from_es
            # If not exists in spain, add uk data to the merged data
            elif exists_in_uk:
                # If exists in ita, add the images from ita to the merged data
                if exists_in_ita:
                    if len(product_from_uk["imgs"]) > 1:
                    if len(product_from_ita["imgs"]) > 1:
                        product_from_uk["imgs"] = product_from_ita["imgs"]
                merged_product = product_from_uk
            # If not exists in spain or uk, add ita data to the merged data
            elif exists_in_ita:
                merged_product = product_from_ita

            # Icons from 1.UK 2.ITA
            if exists_in_uk and len(product_from_uk['icons']) > 1:
                merged_product['icons'] = product_from_uk['icons']
            elif exists_in_ita and len(product_from_ita['icons']) > 1:
                merged_product['icons'] = product_from_ita['icons']

            if merged_product is not None:
                cls.merged_data.append(merged_product)

        return cls.merged_data

    @classmethod
    def extract_merged_data(cls):
        if len(cls.merged_data) < 1:
            cls.get_merged_data()

        for index in range(0, len(cls.merged_data), 50):
            Util.dump_to_json(cls.merged_data[index:index + 50], f"merged_data/VTAC_MERGED_INFO_{index + 50}.json")


DataMerger.extract_merged_data()
