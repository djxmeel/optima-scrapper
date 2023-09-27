from utils.data_merger import DataMerger
from utils.odoo_import import OdooImport
from utils.loggers import Loggers
from utils.util import Util

TARGET_DATA_DIR_PATH = DataMerger.MERGED_PRODUCT_INFO_DIR_PATH
TARGET_MEDIA_DIR_PATH = DataMerger.MERGED_PRODUCT_MEDIA_DIR_PATH

UPLOADED_DATA_DIR_PATH = DataMerger.UPLOADED_DATA_DIR_PATH
UPLOADED_MEDIA_DIR_PATH = DataMerger.UPLOADED_MEDIA_DIR_PATH

IF_IMPORT_FIELDS = False

IF_IMPORT_PRODUCTS = False
IF_SKIP_ATTRS_OF_EXISTING = True

# TODO TEST
IF_IMPORT_ACC = False
# TODO TEST
IF_IMPORT_PDFS = False
# TODO TEST
IF_IMPORT_IMGS = True
# TODO TEST
IF_IMPORT_ICONS = True

OdooImport.logger = Loggers.setup_odoo_import_logger()

# ODOO IMPORT
if IF_IMPORT_FIELDS:
    OdooImport.logger.info(f'BEGINNING FIELDS IMPORT')
    OdooImport.import_fields(Util.ODOO_CUSTOM_FIELDS)
    OdooImport.logger.info(f'FINISHED FIELDS IMPORT')

if IF_IMPORT_PRODUCTS:
    OdooImport.logger.info(f'BEGINNING PRODUCTS IMPORT')
    OdooImport.import_products(TARGET_DATA_DIR_PATH, UPLOADED_DATA_DIR_PATH, skip_attrs_of_existing=IF_SKIP_ATTRS_OF_EXISTING)
    OdooImport.logger.info(f'FINISHED PRODUCTS IMPORT')

if IF_IMPORT_ACC:
    OdooImport.logger.info(f'BEGINNING ACCESSORIES IMPORT')
    OdooImport.import_accessories(TARGET_DATA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ACCESSORIES IMPORT')

if IF_IMPORT_PDFS:
    OdooImport.logger.info(f'BEGINNING PDFS IMPORT')
    OdooImport.import_pdfs(Util.get_unique_skus_from_dir(TARGET_DATA_DIR_PATH))
    OdooImport.logger.info(f'FINISHED PDFS IMPORT')

if IF_IMPORT_IMGS:
    OdooImport.logger.info(f'BEGINNING IMGS IMPORT')
    # TODO uncomment
    #OdooImport.import_imgs(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH)
    OdooImport.import_imgs(TARGET_DATA_DIR_PATH, UPLOADED_DATA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED IMGS IMPORT')

if IF_IMPORT_ICONS:
    OdooImport.logger.info(f'BEGINNING ICONS IMPORT')
    # TODO uncomment
    #OdooImport.import_icons(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH)
    OdooImport.import_icons(TARGET_DATA_DIR_PATH, UPLOADED_DATA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ICONS IMPORT')
