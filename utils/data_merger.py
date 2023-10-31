import json
import copy
import threading

from utils.util import Util
from scrapers.scraper_vtac_es import ScraperVtacSpain
from scrapers.scraper_vtac_ita import ScraperVtacItalia
from scrapers.scraper_vtac_uk import ScraperVtacUk


class DataMerger:
    logger = None

    JSON_DUMP_FREQUENCY = 25
    DATA_DUMP_PATH_TEMPLATE = 'data/vtac_merged/PRODUCT_INFO/MERGED_INFO_{}.json'
    MEDIA_DUMP_PATH_TEMPLATE = 'data/vtac_merged/PRODUCT_MEDIA/MERGED_MEDIA_{}.json'

    MERGED_PRODUCTS_FIELDS_JSON_PATH = 'data/vtac_merged/FIELDS/PRODUCTS_FIELDS.json'
    MERGED_PRODUCTS_FIELDS_EXCEL_PATH = 'data/vtac_merged/FIELDS/DISTINCT_FIELDS_EXCEL.xlsx'

    MERGED_PRODUCTS_EXAMPLE_FIELDS_JSON_PATH = 'data/vtac_merged/FIELDS/PRODUCTS_FIELDS_EXAMPLES.json'
    MERGED_PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH = 'data/vtac_merged/FIELDS/DISTINCT_FIELDS_EXAMPLES_EXCEL.xlsx'

    MERGED_PRODUCT_INFO_DIR_PATH = 'data/vtac_merged/PRODUCT_INFO'
    MERGED_PRODUCT_MEDIA_DIR_PATH = 'data/vtac_merged/PRODUCT_MEDIA'

    UPLOADED_DATA_DIR_PATH = 'data/vtac_merged/PRODUCT_INFO_UPLOADED'
    UPLOADED_MEDIA_DIR_PATH = 'data/vtac_merged/PRODUCT_MEDIA_UPLOADED'

    # Path to [CATEGORY ES|CATEGORY EN|SKU] Excel file
    PUBLIC_CATEGORY_EXCEL_PATH = 'data/common/PUBLIC_CATEGORY_SKU.xlsx'

    COUNTRY_SCRAPERS = {
        'es': ScraperVtacSpain,
        'uk': ScraperVtacUk,
        'ita': ScraperVtacItalia
    }

    # Field priorities, 'default' is for fields that are not in this list
    FIELD_PRIORITIES = {
        'default': ('es', 'uk', 'ita'),
        'website_description': ('es', 'uk'),
        'accesorios': ('ita')
    }

    MEDIA_FIELDS_PRIORITIES = {
        'icons': ('uk', 'ita', 'es'),
        'imgs': ('ita', 'uk', 'es'),
        'videos': ('uk', 'ita', 'es')
    }

    # Fields to delete from products
    FIELDS_TO_DELETE = [
        "Código de producto"
    ]

    # Fields to rename for common naming between data sources
    FIELDS_RENAMES_JSON_PATH = 'data/common/FIELDS_RENAMES.json'

    VALUES_RENAMES_JSON_PATH = 'data/common/VALUES_RENAMES.json'

    # Fields that are always kept from a country (field must be stored as a list in json)
    # Example: 'imgs' priority is ['uk', 'ita', 'es'] but we want to also keep all images from 'es' country
    COUNTRY_FIELDS_ALWAYS_KEEP = [
        # All ES imgs are getting extracted, therefore we will not always keep (before: only graph_dimensions were extracted)
        # {'country': 'es', 'field': 'imgs'}
    ]

    merged_data = []
    merged_media = []

    country_data = {
        'es': [],
        'uk': [],
        'ita': []
    }

    country_media = {
        'es': [],
        'uk': [],
        'ita': []
    }

    @classmethod
    def load_data_for_country(cls, country, only_media=False, if_only_new=False):
        if if_only_new:
            directory_path = cls.COUNTRY_SCRAPERS[country].NEW_PRODUCTS_INFO_PATH
        else:
            directory_path = cls.COUNTRY_SCRAPERS[country].PRODUCTS_INFO_PATH
        data = []

        if only_media:
            if if_only_new:
                directory_path = cls.COUNTRY_SCRAPERS[country].NEW_PRODUCTS_MEDIA_PATH
            else:
                directory_path = cls.COUNTRY_SCRAPERS[country].PRODUCTS_MEDIA_PATH

        # Load data
        file_list = Util.get_all_files_in_directory(directory_path)
        for file_path in file_list:
            with open(file_path, "r", encoding='utf-8') as file:
                data += json.load(file)

        if not only_media:
            # Filtering None
            # Merging fields when necessary
            data = [cls.rename__delete_product_fields__values(p, cls.FIELDS_RENAMES_JSON_PATH, cls.FIELDS_TO_DELETE, cls.VALUES_RENAMES_JSON_PATH) for p in data if p is not None]
            cls.logger.info(f"FINISHED MERGING {country} PRODUCTS FIELDS")

        return data

    @classmethod
    def load_all(cls, if_only_new):
        for country in cls.COUNTRY_SCRAPERS.keys():
            if cls.country_data.get(country):
                if input(f"DATA for {country} already loaded. Load again? (y/n): ") == 'n':
                    continue
                cls.country_data[country] = {'es': [], 'uk': [], 'ita': []}
            cls.country_data[country] = cls.load_data_for_country(country, if_only_new)

        for country in cls.COUNTRY_SCRAPERS.keys():
            if cls.country_media.get(country):
                if input(f"MEDIA for {country} already loaded. Load again? (y/n): ") == 'n':
                    continue
                cls.country_media[country] = {'es': [], 'uk': [], 'ita': []}
            cls.country_media[country] = cls.load_data_for_country(country, True, if_only_new)
        return cls

    @classmethod
    def get_product_data_from_country_sku(cls, sku, country, only_media=False):
        data = cls.country_data[country]
        if only_media:
            data = cls.country_media[country]

        for product in data:
            if product["default_code"] == sku:
                return product
        return None

    @classmethod
    def rename__delete_product_fields__values(cls, product, fields_to_rename_json_path, fields_to_delete, value_renames_json_path):
        fields_to_rename = Util.load_json(fields_to_rename_json_path)
        value_renames = Util.load_json(value_renames_json_path)

        for key, value in fields_to_rename.items():
            if key in product:
                product[value] = product[key]
                del product[key]

        for field in fields_to_delete:
            if field in product:
                del product[field]

        for key, value in value_renames.items():
            if key in product:
                for value_rename in value:
                    product[key] = product[key].replace(value_rename[0], value_rename[1])
        return product

    @classmethod
    def merge_data(cls):
        unique_product_skus = Util.get_unique_skus_from_dictionary(cls.country_data['es'] + cls.country_data['uk'] + cls.country_data['ita'])

        for sku in unique_product_skus:
            product_data = {'es': cls.get_product_data_from_country_sku(sku, 'es'),
                            'uk': cls.get_product_data_from_country_sku(sku, 'uk'),
                            'ita': cls.get_product_data_from_country_sku(sku, 'ita')}

            product_media = {'es': cls.get_product_data_from_country_sku(sku, 'es', True),
                                'uk': cls.get_product_data_from_country_sku(sku, 'uk', True),
                                'ita': cls.get_product_data_from_country_sku(sku, 'ita', True)}

            # Add empty spaces to sku to make it 8 characters long for better readability
            sku_spaced = sku + ' ' * (8 - len(sku))

            cls.logger.info(f'\n{sku_spaced}: ES: {int(product_data.get("es") is not None)} | UK: {int(product_data.get("uk") is not None)} | ITA: {int(product_data.get("ita") is not None)}')

            merged_product = {}
            merged_media = {"default_code": sku}

            # First, deepcopy product from the first country in 'default' priority order
            for country in cls.FIELD_PRIORITIES['default']:
                # Stop at first found in priority order
                if product_data[country] is not None:
                    merged_product = copy.deepcopy(product_data[country])
                    cls.logger.info(f'{sku_spaced}: DEFAULT -> {country}')
                    break

            # Then, merge fields from other countries in priority order
            for field in cls.FIELD_PRIORITIES.keys():
                if field == 'default':
                    continue
                for country in cls.FIELD_PRIORITIES[field]:
                    if product_data.get(country) and product_data[country].get(field) and product_data[country][field]:
                        if type(product_data[country][field]) is list:
                            merged_product[field] = copy.deepcopy(product_data[country][field])
                            cls.logger.info(f'{sku_spaced}: MERGE {country} -> {field}')
                            break
                        merged_product[field] = product_data[country][field]
                        cls.logger.info(f'{sku_spaced}: MERGE {country} -> {field}')
                        break

            # Then, merge MEDIA fields in priority order
            for field in cls.MEDIA_FIELDS_PRIORITIES.keys():
                for country in cls.MEDIA_FIELDS_PRIORITIES[field]:
                    if product_media.get(country) and product_media[country].get(field) and product_media[country][field]:
                        if type(product_media[country][field]) is list:
                            merged_media[field] = copy.deepcopy(product_media[country][field])
                            cls.logger.info(f'{sku_spaced}: MERGE {country} -> {field}')
                            break
                        merged_media[field] = product_media[country][field]
                        cls.logger.info(f'{sku_spaced}: MERGE {country} -> {field}')
                        break

            for field_country in cls.COUNTRY_FIELDS_ALWAYS_KEEP:
                try:
                    if product_data[field_country['country']]:
                        field_to_keep = product_data[field_country['country']][field_country['field']]
                        if field_to_keep and merged_product[field_country['field']] is not field_to_keep:
                            merged_product[field_country['field']] += field_to_keep
                            cls.logger.info(f'{sku_spaced}: KEEP {field_country["country"]} -> {field_country["field"]}')
                except KeyError:
                    pass

            merged_product['public_categories'] = Util.get_public_category_from_sku(sku, cls.PUBLIC_CATEGORY_EXCEL_PATH)

            cls.merged_data.append(merged_product)
            cls.merged_media.append(merged_media)

    @classmethod
    def extract_merged_data(cls, data, media):
        data_path_temp = cls.DATA_DUMP_PATH_TEMPLATE
        media_path_temp = cls.MEDIA_DUMP_PATH_TEMPLATE

        def async_task(data_type, path):
            for index in range(0, len(data_type), cls.JSON_DUMP_FREQUENCY):
                counter = index + cls.JSON_DUMP_FREQUENCY

                if index + cls.JSON_DUMP_FREQUENCY > len(data_type):
                    counter = len(data_type)

                Util.dump_to_json(data_type[index:counter], path.format(counter))

        t1 = threading.Thread(target=async_task, args=(data, data_path_temp), name='t1')
        t2 = threading.Thread(target=async_task, args=(media, media_path_temp), name='t2')

        t1.start()
        t2.start()
        t1.join()
        t2.join()
