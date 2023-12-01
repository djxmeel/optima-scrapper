from utils.data_merger import DataMerger
from utils.loggers import Loggers
from utils.util import Util

# Merge uk + eso + ita
IF_MERGE = True
IF_ONLY_NEW_PRODUCTS = False
IF_UPDATE_EU_STOCK_ATTRIBUTES = True

# Extract distinct fields examples to excel
IF_EXTRACT_DISTINCT_FIELDS_EXAMPLES = False
# Generate custom fields excel & json
IF_GENERATE_CUSTOM_FIELDS_EXCEL_JSON = False

DataMerger.logger = Loggers.setup_merge_logger()

# DATA MERGING
if IF_MERGE:
    DataMerger.logger.info('BEGINNING DATA MERGING')
    data, media =DataMerger.load_all(IF_ONLY_NEW_PRODUCTS).merge_data(IF_UPDATE_EU_STOCK_ATTRIBUTES)
    DataMerger.extract_merged_data(data, media, IF_ONLY_NEW_PRODUCTS)
    DataMerger.logger.info('FINISHED DATA MERGING')

if IF_EXTRACT_DISTINCT_FIELDS_EXAMPLES:
    DataMerger.logger.info('BEGINNING FIELD EXAMPLES EXTRACTION')
    Util.extract_fields_example_to_excel(DataMerger.MERGED_PRODUCT_INFO_DIR_PATH, DataMerger.MERGED_PRODUCTS_EXAMPLE_FIELDS_JSON_PATH, DataMerger.MERGED_PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH)
    DataMerger.logger.info('FINISHED FIELD EXAMPLES EXTRACTION')

if IF_GENERATE_CUSTOM_FIELDS_EXCEL_JSON:
    DataMerger.logger.info('GENERATING CUSTOM FIELDS EXCEL & JSON')
    Util.generate_custom_fields_excel_json(DataMerger.MERGED_PRODUCTS_FIELDS_JSON_PATH, DataMerger.MERGED_PRODUCTS_FIELDS_EXCEL_PATH, Util.ODOO_CUSTOM_FIELDS)
    DataMerger.logger.info('FINISHED GENERATING CUSTOM FIELDS EXCEL & JSON')
