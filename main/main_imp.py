from utils.data_merger import DataMerger
from utils.odoo_import import OdooImport
from utils.util import Util

# TODO 1. use NEW_LINKS of UK and ES generated from playground.skus_extractor() then scrape new links
# TODO 2. Remerge to update public categories in json files
# TODO 3. Launch categs_from_name assignment after updating PUBLIC_CATEGORY_FROM_NAME.json
# TODO 4. upload new pricelist
TARGET_DATA_DIR_PATH = DataMerger.MERGED_PRODUCT_INFO_DIR_PATH
TARGET_MEDIA_DIR_PATH = DataMerger.MERGED_PRODUCT_MEDIA_DIR_PATH

NEW_TARGET_DATA_DIR_PATH = DataMerger.NEW_MERGED_PRODUCT_INFO_DIR_PATH
NEW_TARGET_MEDIA_DIR_PATH = DataMerger.NEW_MERGED_PRODUCT_MEDIA_DIR_PATH

UPLOADED_DATA_DIR_PATH = DataMerger.UPLOADED_DATA_DIR_PATH
UPLOADED_MEDIA_DIR_PATH = DataMerger.UPLOADED_MEDIA_DIR_PATH

NEW_UPLOADED_DATA_DIR_PATH = DataMerger.NEW_UPLOADED_DATA_DIR_PATH
NEW_UPLOADED_MEDIA_DIR_PATH = DataMerger.NEW_UPLOADED_MEDIA_DIR_PATH

PUBLIC_CATEGORIES_FILE_PATH = 'data/common/excel/public_categories_odoo.xlsx'

SUPPLIER_STOCK_EXCEL_FILE_PATH = 'data/common/excel/supplier_stock.xlsx'
SUPPLIER_PRICELIST_EXCEL_FILE_PATH = 'data/common/excel/pricelist_compra_coste.xlsx'

SKUS_CATALOGO_Q12024_FILE_PATH = 'data/common/excel/public_category_sku.xlsx'

IF_IMPORT_FIELDS = False

IF_IMPORT_PUBLIC_CATEGORIES = False

IF_IMPORT_PRODUCTS = False
IF_UPDATE_EXISTING = False
IF_ONLY_NEW_PRODUCTS_DATA = False
USE_PRIORITY_EXCEL = False

IF_IMPORT_ACC = False
IF_ONLY_NEW_PRODUCTS_ACC = False

IF_IMPORT_PDFS = False
PDF_START_FROM = 0
SKIP_PRODUCTS_W_ATTACHMENTS = False

IF_IMPORT_IMGS = False
IF_IMPORT_ICONS = False
IF_ONLY_NEW_PRODUCTS_MEDIA = False

IF_IMPORT_SUPPLIER_INFO_AND_COST = False
IF_UPDATE_MODE = False

IF_IMPORT_DESCATALOGADOS = True

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
    if IF_ONLY_NEW_PRODUCTS_DATA:
        OdooImport.import_products(NEW_TARGET_DATA_DIR_PATH, NEW_UPLOADED_DATA_DIR_PATH, IF_UPDATE_EXISTING, USE_PRIORITY_EXCEL)
    else:
        OdooImport.import_products(TARGET_DATA_DIR_PATH, UPLOADED_DATA_DIR_PATH, IF_UPDATE_EXISTING, USE_PRIORITY_EXCEL)
    OdooImport.logger.info(f'FINISHED PRODUCTS IMPORT')

if IF_IMPORT_ACC:
    OdooImport.logger.info(f'BEGINNING ACCESSORIES IMPORT')
    if IF_ONLY_NEW_PRODUCTS_ACC:
        OdooImport.import_accessories(NEW_TARGET_DATA_DIR_PATH)
    else:
        OdooImport.import_accessories(TARGET_DATA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ACCESSORIES IMPORT')

if IF_IMPORT_PDFS:
    OdooImport.logger.info(f'BEGINNING PDFS IMPORT')
    OdooImport.import_pdfs(PDF_START_FROM, SKIP_PRODUCTS_W_ATTACHMENTS)
    OdooImport.logger.info(f'FINISHED PDFS IMPORT')

if IF_IMPORT_IMGS:
    OdooImport.logger.info(f'BEGINNING IMGS IMPORT')
    if IF_ONLY_NEW_PRODUCTS_MEDIA :
        OdooImport.import_imgs_videos(NEW_TARGET_MEDIA_DIR_PATH, NEW_UPLOADED_MEDIA_DIR_PATH)
    else:
        OdooImport.import_imgs_videos(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED IMGS IMPORT')

if IF_IMPORT_ICONS:
    OdooImport.logger.info(f'BEGINNING ICONS IMPORT')
    if IF_ONLY_NEW_PRODUCTS_MEDIA:
        OdooImport.import_icons(NEW_TARGET_MEDIA_DIR_PATH, NEW_UPLOADED_MEDIA_DIR_PATH)
    else:
        OdooImport.import_icons(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ICONS IMPORT')

if IF_IMPORT_SUPPLIER_INFO_AND_COST:
    OdooImport.logger.info(f'BEGINNING SUPPLIER INFO IMPORT')
    OdooImport.import_supplier_info(SUPPLIER_STOCK_EXCEL_FILE_PATH, SUPPLIER_PRICELIST_EXCEL_FILE_PATH, IF_UPDATE_MODE)
    OdooImport.logger.info(f'FINISHED SUPPLIER INFO IMPORT')

if IF_IMPORT_DESCATALOGADOS:
    OdooImport.logger.info(f'BEGINNING DESCATALOGADOS IMPORT')
    OdooImport.import_descatalogados(SKUS_CATALOGO_Q12024_FILE_PATH)
    OdooImport.logger.info(f'FINISHED DESCATALOGADOS IMPORT')
