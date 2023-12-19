from utils.data_merger import DataMerger
from utils.odoo_import import OdooImport
from utils.util import Util

# write() method of the Odoo API
# 0 is for creating a new record.
# 1 is for updating an existing record.
# 2 is for deleting a record (unlink).
# 3 is for removing a relationship link (but not deleting the related record).
# 4 is for adding an existing record.
# 5 is for removing all linked records (similar to 3, but for all).
# 6 is for setting a new set of records.

# TODO WEEKLY 1. New products link extraction and scraping
# TODO WEEKLY 2. Compare pricelists when new pricelist is available
# TODO WEEKLY 3. Upload stock when new stock is available

# TODO 1. Extract GEN/Alicante stock from Odoo 15 and upload to Odoo 16

TARGET_DATA_DIR_PATH = DataMerger.MERGED_PRODUCT_INFO_DIR_PATH
TARGET_MEDIA_DIR_PATH = DataMerger.MERGED_PRODUCT_MEDIA_DIR_PATH

UPLOADED_DATA_DIR_PATH = DataMerger.UPLOADED_DATA_DIR_PATH
UPLOADED_MEDIA_DIR_PATH = DataMerger.UPLOADED_MEDIA_DIR_PATH

PUBLIC_CATEGORIES_FILE_PATH = 'data/common/excel/public_categories_odoo.xlsx'

SUPPLIER_STOCK_EXCEL_FILE_PATH = 'data/common/excel/supplier_stock.xlsx'
SUPPLIER_PRICELIST_EXCEL_FILE_PATH = 'data/common/excel/pricelist_compra_coste.xlsx'

SKUS_CATALOGO_Q12024_FILE_PATH = 'data/common/excel/public_category_sku_Q1_2024.xlsx'

BRANDS_EXCEL_FILE_PATH = 'data/common/excel/product_brands.xlsx'

PRODUCT_TO_ARCHIVE_CONDITIONS_JSON_PATH = 'data/common/json/PRODUCT_TO_ARCHIVE_CONDITIONS.json'


IF_IMPORT_BRANDS = False

IF_IMPORT_FIELDS = False

IF_IMPORT_PUBLIC_CATEGORIES = False

IF_IMPORT_PRODUCTS = False
IF_SKIP_EXISTING = False
USE_PRIORITY_EXCEL = False
# 'no' | 'soft' | 'deep'
ATTRS_UPDATE_MODE = 'no'

IF_IMPORT_SUPPLIER_INFO_AND_COST = False
IF_UPDATE_MODE = False

IF_IMPORT_DESCATALOGADOS_CATALOGO = False

# TODO Auto-generate excel with product in EU Stock not in Odoo & qty > 0 after upload weekly EU Stock
IF_IMPORT_AVAILABILITY = False
IF_GENERATE_MISSING_PRODUCTS_EXCEL = False

IF_IMPORT_ACC = False
IF_ONLY_NEW_PRODUCTS_ACC = False

IF_IMPORT_PDFS = False
PDF_START_FROM = 0
SKIP_PRODUCTS_W_ATTACHMENTS = False

IF_IMPORT_IMGS = False
IF_IMPORT_ICONS = False
IF_ONLY_NEW_PRODUCTS_MEDIA = False

IF_ARCHIVE_PRODUCTS_FROM_JSON = False


if IF_IMPORT_FIELDS:
    OdooImport.logger.info(f'BEGINNING FIELDS IMPORT')
    OdooImport.import_fields(Util.ODOO_CUSTOM_FIELDS)
    OdooImport.logger.info(f'FINISHED FIELDS IMPORT')

if IF_IMPORT_PUBLIC_CATEGORIES:
    OdooImport.logger.info(f'BEGINNING PUBLIC CATEGORIES IMPORT')
    OdooImport.import_public_categories(PUBLIC_CATEGORIES_FILE_PATH)
    OdooImport.logger.info(f'FINISHED PUBLIC CATEGORIES IMPORT')

if IF_IMPORT_BRANDS:
    OdooImport.logger.info(f'BEGINNING BRANDS IMPORT')
    OdooImport.import_brands(BRANDS_EXCEL_FILE_PATH)
    OdooImport.logger.info(f'FINISHED BRANDS IMPORT')

if IF_IMPORT_PRODUCTS:
    OdooImport.logger.info(f'BEGINNING PRODUCTS IMPORT')
    OdooImport.import_products(TARGET_DATA_DIR_PATH, UPLOADED_DATA_DIR_PATH, IF_SKIP_EXISTING, USE_PRIORITY_EXCEL, ATTRS_UPDATE_MODE)
    OdooImport.logger.info(f'FINISHED PRODUCTS IMPORT')

if IF_IMPORT_ACC:
    OdooImport.logger.info(f'BEGINNING ACCESSORIES IMPORT')
    OdooImport.import_accessories(TARGET_DATA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ACCESSORIES IMPORT')

if IF_IMPORT_PDFS:
    OdooImport.logger.info(f'BEGINNING PDFS IMPORT')
    OdooImport.import_pdfs(PDF_START_FROM, SKIP_PRODUCTS_W_ATTACHMENTS)
    OdooImport.logger.info(f'FINISHED PDFS IMPORT')

if IF_IMPORT_IMGS:
    OdooImport.logger.info(f'BEGINNING IMGS IMPORT')
    OdooImport.import_imgs_videos(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED IMGS IMPORT')

if IF_IMPORT_ICONS:
    OdooImport.logger.info(f'BEGINNING ICONS IMPORT')
    OdooImport.import_icons(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ICONS IMPORT')

if IF_IMPORT_SUPPLIER_INFO_AND_COST:
    OdooImport.logger.info(f'BEGINNING SUPPLIER INFO IMPORT')
    OdooImport.import_supplier_info(SUPPLIER_STOCK_EXCEL_FILE_PATH, SUPPLIER_PRICELIST_EXCEL_FILE_PATH, IF_UPDATE_MODE)
    OdooImport.logger.info(f'FINISHED SUPPLIER INFO IMPORT')

if IF_IMPORT_DESCATALOGADOS_CATALOGO:
    OdooImport.logger.info(f'BEGINNING DESCATALOGADOS IMPORT')
    OdooImport.import_descatalogados_catalogo(SKUS_CATALOGO_Q12024_FILE_PATH)
    OdooImport.logger.info(f'FINISHED DESCATALOGADOS IMPORT')

if IF_IMPORT_AVAILABILITY:
    OdooImport.logger.info(f'BEGINNING AVAILABILITY IMPORT')
    OdooImport.import_availability(OdooImport.EU_STOCK_EXCEL_PATH, IF_GENERATE_MISSING_PRODUCTS_EXCEL)
    OdooImport.logger.info(f'FINISHED AVAILABILITY IMPORT')

if IF_ARCHIVE_PRODUCTS_FROM_JSON:
    OdooImport.logger.info(f'BEGINNING BRANDS IMPORT')
    OdooImport.archive_products_from_json(PRODUCT_TO_ARCHIVE_CONDITIONS_JSON_PATH)
    OdooImport.logger.info(f'FINISHED BRANDS IMPORT')
