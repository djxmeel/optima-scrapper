import json
import copy
from utils.util import Util
from scrapers.scraper_vtac_es import ScraperVtacSpain
from scrapers.scraper_vtac_ita import ScraperVtacItalia
from scrapers.scraper_vtac_uk import ScraperVtacUk

# TODO TEST SEPARATE MERGE
class DataMerger:
    logger = None

    JSON_DUMP_FREQUENCY = 10
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


    COUNTRY_PRODUCT_INFO_DIR_PATHS = {
        'es': ScraperVtacSpain.PRODUCTS_INFO_PATH,
        'uk': ScraperVtacUk.PRODUCTS_INFO_PATH,
        'ita': ScraperVtacItalia.PRODUCTS_INFO_PATH
    }

    COUNTRY_PRODUCT_MEDIA_DIR_PATHS = {
        'es': ScraperVtacSpain.PRODUCTS_MEDIA_PATH,
        'uk': ScraperVtacUk.PRODUCTS_MEDIA_PATH,
        'ita': ScraperVtacItalia.PRODUCTS_MEDIA_PATH
    }

    # Field priorities, 'default' is for fields that are not in this list
    FIELD_PRIORITIES = {
        'default': ('es', 'uk', 'ita'),
        'accesorios': ('ita', 'uk', 'es')
    }

    MEDIA_FIELDS_PRIORITIES = {
        'icons': ('uk', 'ita', 'es'),
        'imgs': ('ita', 'uk', 'es'),
        'videos': ('uk', 'ita', 'es')
    }

    # Fields to rename for common naming between data sources
    FIELDS_RENAMES = {
        "Código EAN": "EAN",
        'EAN Código': 'EAN',
        'ean': 'EAN',
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
        'Hora de inicio al 100% encendido': 'Tiempo de inicio al 100% encendido',
        'SKU': 'sku',
        'kit': 'accesorios'
    }

    # Fields that are always kept from a country (field must be stored as a list in json)
    # Example: 'imgs' priority is ['uk', 'ita', 'es'] but we want to also keep all images from 'es' country
    COUNTRY_FIELDS_ALWAYS_KEEP = [
        # All ES imgs are getting extracted, therefore we will not always keep (before: only graph_dimensions were extracted)
        #{'country': 'es', 'field': 'imgs'}
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
    def load_data_for_country(cls, country, only_media= False):
        directory_path = cls.COUNTRY_PRODUCT_INFO_DIR_PATHS[country]
        data = []

        if only_media:
            directory_path = cls.COUNTRY_PRODUCT_MEDIA_DIR_PATHS[country]

        # Load data
        file_list = Util.get_all_files_in_directory(directory_path)
        for file_path in file_list:
            with open(file_path, "r", encoding='utf-8') as file:
                data += json.load(file)

        if not only_media:
            # Filtering None
            # Merging fields when necessary
            data = [cls.rename_product_fields(p, cls.FIELDS_RENAMES) for p in data if p is not None]
            cls.logger.info(f"FINISHED MERGING {country} PRODUCTS FIELDS")

        return data


    @classmethod
    def load_all(cls):
        for country in cls.COUNTRY_PRODUCT_INFO_DIR_PATHS.keys():
            if cls.country_data.get(country):
                if input(f"DATA for {country} already loaded. Load again? (y/n): ") == 'n':
                    continue
                cls.country_data[country] = {'es': [], 'uk': [], 'ita': []}
            cls.country_data[country] = cls.load_data_for_country(country)

        for country in cls.COUNTRY_PRODUCT_INFO_DIR_PATHS.keys():
            if cls.country_media.get(country):
                if input(f"MEDIA for {country} already loaded. Load again? (y/n): ") == 'n':
                    continue
                cls.country_media[country] = {'es': [], 'uk': [], 'ita': []}
            cls.country_media[country] = cls.load_data_for_country(country, True)
        return cls

    @classmethod
    def get_country_data(cls, country):
        if cls.country_data.get(country):
            return cls.country_data.get(country, None)

        return cls.load_data_for_country(country)

    @classmethod
    def get_product_data_from_country_sku(cls, sku, country, only_media= False):
        data = cls.country_data[country]
        if only_media:
            data = cls.country_media[country]

        for product in data:
            if product["sku"] == sku:
                return product
        return None


    @classmethod
    def rename_product_fields(cls, product, fields_to_rename):
        for key, value in fields_to_rename.items():
            if product.get(key):
                product[value] = product[key]
                del product[key]
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

            # Add empty spaces to SKU to make it 8 characters long for better readability
            sku += ' ' * (8 - len(sku))

            cls.logger.info(f'\n{sku} : ES: {int(product_data.get("es") is not None)} | UK: {int(product_data.get("uk") is not None)} | ITA: {int(product_data.get("ita") is not None)}')

            merged_product = {}
            merged_media = {"sku": sku}

            # First, deepcopy product from the first country in 'default' priority order
            for country in cls.FIELD_PRIORITIES['default']:
                # Stop at first found in priority order
                if product_data[country] is not None:
                    merged_product = copy.deepcopy(product_data[country])
                    cls.logger.info(f'{sku}: DEFAULT -> {country}')
                    break

            # Then, merge fields from other countries in priority order
            for field in cls.FIELD_PRIORITIES.keys():
                if field == 'default':
                    continue
                for country in cls.FIELD_PRIORITIES[field]:
                    if product_data.get(country) and product_data[country].get(field) and product_data[country][field]:
                        if type(product_data[country][field]) is list:
                            merged_product[field] = copy.deepcopy(product_data[country][field])
                            cls.logger.info(f'{sku}: MERGE {country} -> {field}')
                            break
                        merged_product[field] = product_data[country][field]
                        cls.logger.info(f'{sku}: MERGE {country} -> {field}')
                        break

            # Then, merge MEDIA fields in priority order
            for field in cls.MEDIA_FIELDS_PRIORITIES.keys():
                for country in cls.MEDIA_FIELDS_PRIORITIES[field]:
                    if product_media.get(country) and product_media[country].get(field) and product_media[country][field]:
                        if type(product_media[country][field]) is list:
                            merged_media[field] = copy.deepcopy(product_media[country][field])
                            cls.logger.info(f'{sku}: MERGE {country} -> {field}')
                            break
                        merged_media[field] = product_media[country][field]
                        cls.logger.info(f'{sku}: MERGE {country} -> {field}')
                        break

            for field_country in cls.COUNTRY_FIELDS_ALWAYS_KEEP:
                try:
                    if product_data[field_country['country']]:
                        field_to_keep = product_data[field_country['country']][field_country['field']]
                        if field_to_keep and merged_product[field_country['field']] is not field_to_keep:
                            merged_product[field_country['field']] += field_to_keep
                            cls.logger.info(f'{sku}: KEEP {field_country["country"]} -> {field_country["field"]}')
                except KeyError:
                    pass

            cls.merged_data.append(merged_product)
            cls.merged_media.append(merged_media)

    @classmethod
    def extract_merged_data(cls, data, is_media=False):
        if not data:
            cls.load_all().merge_data()
            data = cls.merged_media if is_media else cls.merged_data

        for index in range(0, len(data), cls.JSON_DUMP_FREQUENCY):
            counter = index + cls.JSON_DUMP_FREQUENCY

            if index + cls.JSON_DUMP_FREQUENCY > len(data):
                counter = len(data)

            Util.dump_to_json(data[index:counter], cls.DATA_DUMP_PATH_TEMPLATE.format(counter))
