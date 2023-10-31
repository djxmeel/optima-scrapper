from utils.data_merger import DataMerger
from utils.odoo_import import OdooImport
from utils.loggers import Loggers
from utils.util import Util

TARGET_DATA_DIR_PATH = DataMerger.MERGED_PRODUCT_INFO_DIR_PATH
TARGET_MEDIA_DIR_PATH = DataMerger.MERGED_PRODUCT_MEDIA_DIR_PATH

UPLOADED_DATA_DIR_PATH = DataMerger.UPLOADED_DATA_DIR_PATH
UPLOADED_MEDIA_DIR_PATH = DataMerger.UPLOADED_MEDIA_DIR_PATH

PUBLIC_CATEGORIES_FILE_PATH = 'data/common/PUBLIC_CATEGORY_SKU.xlsx'

SUPPLIER_STOCK_EXCEL_FILE_PATH = 'data/common/Supplier Stock.xlsx'

IF_IMPORT_FIELDS = False

IF_IMPORT_PUBLIC_CATEGORIES = True

IF_IMPORT_PRODUCTS = False
IF_UPDATE_EXISTING = False
USE_PRIORITY_EXCEL = False

IF_IMPORT_ACC = False

IF_IMPORT_PDFS = False
SKIP_PRODUCTS_W_ATTACHMENTS = False

IF_IMPORT_IMGS = False

IF_IMPORT_ICONS = False

IF_IMPORT_SUPPLIER_INFO = False

OdooImport.logger = Loggers.setup_odoo_import_logger()

# ODOO IMPORT
if IF_IMPORT_FIELDS:
    OdooImport.logger.info(f'BEGINNING FIELDS IMPORT')
    OdooImport.import_fields(Util.ODOO_CUSTOM_FIELDS)
    OdooImport.logger.info(f'FINISHED FIELDS IMPORT')

# ODOO IMPORT
if IF_IMPORT_PUBLIC_CATEGORIES:
    OdooImport.logger.info(f'BEGINNING PUBLIC CATEGORIES IMPORT')
    OdooImport.import_public_categories(PUBLIC_CATEGORIES_FILE_PATH)
    OdooImport.logger.info(f'FINISHED PUBLIC CATEGORIES IMPORT')

if IF_IMPORT_PRODUCTS:
    OdooImport.logger.info(f'BEGINNING PRODUCTS IMPORT')
    OdooImport.import_products(TARGET_DATA_DIR_PATH, UPLOADED_DATA_DIR_PATH, IF_UPDATE_EXISTING, USE_PRIORITY_EXCEL)
    OdooImport.logger.info(f'FINISHED PRODUCTS IMPORT')

if IF_IMPORT_ACC:
    OdooImport.logger.info(f'BEGINNING ACCESSORIES IMPORT')
    OdooImport.import_accessories(TARGET_DATA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ACCESSORIES IMPORT')

if IF_IMPORT_PDFS:
    OdooImport.logger.info(f'BEGINNING PDFS IMPORT')
    OdooImport.import_pdfs(SKIP_PRODUCTS_W_ATTACHMENTS)
    OdooImport.logger.info(f'FINISHED PDFS IMPORT')

if IF_IMPORT_IMGS:
    OdooImport.logger.info(f'BEGINNING IMGS IMPORT')
    OdooImport.import_imgs_videos(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED IMGS IMPORT')

if IF_IMPORT_ICONS:
    OdooImport.logger.info(f'BEGINNING ICONS IMPORT')
    OdooImport.import_icons(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ICONS IMPORT')

if IF_IMPORT_SUPPLIER_INFO:
    OdooImport.logger.info(f'BEGINNING SUPPLIER INFO IMPORT')
    OdooImport.import_supplier_info(SUPPLIER_STOCK_EXCEL_FILE_PATH)
    OdooImport.logger.info(f'FINISHED SUPPLIER INFO IMPORT')
