from utils.data_merger import DataMerger
from utils.loggers import Loggers
from utils.util import Util


IF_MERGE = False
IF_EXTRACT_FIELDS = False
# If False : only extracts CUSTOM fields present in ODOO
IF_ALL_FIELDS = False
DataMerger.logger = Loggers.setup_merge_logger()

# DATA MERGING
if IF_MERGE:
    DataMerger.logger.info('BEGINNING DATA MERGING')
    DataMerger.extract_merged_data()
    DataMerger.logger.info('FINISHED DATA MERGING')
if IF_EXTRACT_FIELDS:
    DataMerger.logger.info('BEGINNING FIELD EXTRACTION')
    Util.extract_distinct_fields_to_excel(DataMerger.MERGED_PRODUCT_INFO_DIR_PATH, DataMerger.MERGED_PRODUCTS_FIELDS_JSON_PATH, DataMerger.MERGED_PRODUCTS_FIELDS_EXCEL_PATH, extract_all=IF_ALL_FIELDS)
    Util.extract_fields_example_to_excel(DataMerger.MERGED_PRODUCT_INFO_DIR_PATH, DataMerger.MERGED_PRODUCTS_EXAMPLE_FIELDS_JSON_PATH, DataMerger.MERGED_PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH)
    DataMerger.logger.info('FINISHED FIELD EXTRACTION')
