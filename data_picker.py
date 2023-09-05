import json

from util import Util


class DataPicker:
    DATA_DIR_PATH_ES = 'vtac_spain/VTAC_PRODUCT_INFO'
    DATA_DIR_PATH_UK = 'vtac_uk/VTAC_PRODUCT_INFO'
    DATA_DIR_PATH_ITA = 'vtac_italia/VTAC_PRODUCT_INFO'

    merged_data, data_es, data_uk, data_ita = [], [], [], []

    @classmethod
    def load_all(cls):
        file_list_ita = Util.get_all_files_in_directory(cls.DATA_DIR_PATH_ITA)
        file_list_es = Util.get_all_files_in_directory(cls.DATA_DIR_PATH_ES)
        file_list_uk = Util.get_all_files_in_directory(cls.DATA_DIR_PATH_UK)

        for file_path in file_list_ita:
            with open(file_path, "r") as file:
                cls.data_ita.append(json.load(file))

        for file_path in file_list_es:
            with open(file_path, "r") as file:
                cls.data_es.append(json.load(file))

        for file_path in file_list_uk:
            with open(file_path, "r") as file:
                cls.data_uk.append(json.load(file))

    @classmethod
    def get_data(cls, country):
        if country == 'es':
            return cls.data_es
        elif country == 'uk':
            return cls.data_uk
        elif country == 'ita':
            return cls.data_ita
        else:
            return None

    @classmethod
    def product_exists(cls, sku, country_data):
        for product in country_data:
            if product["SKU"] == sku:
                return True, product
        return False, None

    @classmethod
    def get_merged_data(cls):
        cls.load_all()
        all_data = cls.data_es + cls.data_uk + cls.data_ita
        unique_product_skus = set(product["SKU"] for product in all_data)

        for sku in unique_product_skus:
            exists_in_es, product_from_es = cls.product_exists(sku, cls.data_es)
            exists_in_uk, product_from_uk = cls.product_exists(sku, cls.data_uk)
            exists_in_ita, product_from_ita = cls.product_exists(sku, cls.data_ita)
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
                        product_from_uk["imgs"] = product_from_ita["imgs"]
                merged_product = product_from_uk
            # If not exists in spain or uk, add ita data to the merged data
            elif exists_in_ita:
                merged_product = product_from_ita

            # Icons from 1.ITA 2.UK
            if exists_in_ita and len(product_from_ita['icons']) > 1:
                merged_product['icons'] = product_from_ita['icons']
            elif exists_in_uk and len(product_from_uk['icons']) > 1:
                merged_product['icons'] = product_from_uk['icons']

            if merged_product is not None:
                cls.merged_data.append(merged_product)

        return cls.merged_data

    @classmethod
    def extract_merged_data(cls):
        if len(cls.merged_data) < 1:
            cls.get_merged_data()

        for index in range(0, len(cls.merged_data), 50):
            Util.dump_to_json(cls.merged_data[index:index + 50], f"VTAC_MERGED_INFO_{index}.json")
        return cls.merged_data
