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

# WEEKLY 1. New products link extraction and scraping
# WEEKLY 2. Compare pricelists when new pricelist is available
# WEEKLY 3. Upload stock when new stock is available
# WEEKLY 4. Delete unused attributes and values
# WEEKLY 5. Check new spec sheets in V-TAC UK

# TODO sug. Store scraped products individually (instead of 50 at a time)
# TODO create missing SKUS in "blistered excel"
# TODO NEW import for public categories
# TODO when scraping for NEW links, generate an excel that separates skus not in odoo
# TODO check and delete icons in extra media
# TODO crear unidades medidas de Odoo15 en Odoo16

TARGET_DATA_DIR_PATH = DataMerger.MERGED_PRODUCT_INFO_DIR_PATH
TARGET_MEDIA_DIR_PATH = DataMerger.MERGED_PRODUCT_MEDIA_DIR_PATH

UPLOADED_DATA_DIR_PATH = DataMerger.UPLOADED_DATA_DIR_PATH
UPLOADED_MEDIA_DIR_PATH = DataMerger.UPLOADED_MEDIA_DIR_PATH

PRODUCTS_PUBLIC_CATEGORIES_FILE_PATH = 'data/common/excel/products_public_categories_odoo.xlsx'

SUPPLIER_STOCK_EXCEL_FILE_PATH = 'data/common/excel/eu_stock/eu_stock.xlsx'
SUPPLIER_PRICELIST_EXCEL_FILE_PATH = 'data/common/excel/pricelist_compra_coste.xlsx'

BRANDS_EXCEL_FILE_PATH = 'data/common/excel/product_brands.xlsx'

PRODUCT_TO_ARCHIVE_CONDITIONS_JSON_PATH = 'data/common/json/PRODUCT_TO_ARCHIVE_CONDITIONS.json'

LOCAL_STOCK_EXCEL_PATH = 'data/common/excel/local_stock/local_stock.xlsx'

IF_IMPORT_FIELDS = False

IF_IMPORT_BRANDS = False

IF_IMPORT_PRODUCTS = False
# When False, products with changed origin URL to ES will be updated anyway
# When True, only new SKUS will be imported
IF_SKIP_EXISTING = False
# True if you want to update products even if their origin URL is the same
IF_FORCE_UPDATE = False
USE_PRIORITY_EXCEL = False

IF_IMPORT_PUBLIC_CATEGORIES = False
PRODUCTS_PUBLIC_CATEGORIES_BEGIN_FROM = 0

IF_IMPORT_ACC = False

IF_IMPORT_IMGS_AND_VIDEOS = False
# If True, existing media will be deleted before importing. Product with x_lock_main_media will not be cleaned
IF_CLEAN_EXISTING = False
SKIP_PRODUCTS_W_MEDIA = False

IF_IMPORT_ICONS = False
ICONS_BEGIN_FROM = 0

# Always upload before PDFs
IF_IMPORT_SPEC_SHEETS = False
SPEC_SHEETS_BEGIN_FROM = 0
IF_UPDATE_SPEC_SHEETS = False

IF_IMPORT_PDFS = False
PDF_BEGIN_FROM = 0
IF_CLEAN_ATTACHMENTS = False
SKIP_PRODUCTS_W_ATTACHMENTS = False

IF_IMPORT_SUPPLIER_INFO_AND_COST = False
IF_UPDATE_MODE = False

IF_IMPORT_CORRECT_NAMES_FROM_EXCEL = False
# If True, correct names will be extracted from product jsons
IF_GET_CORRECT_NAMES_FROM_JSONS = False

IF_IMPORT_DESCATALOGADOS_CATALOGO = False

IF_IMPORT_LOCAL_STOCK = False

IF_IMPORT_AVAILABILITY = False
IF_GENERATE_MISSING_PRODUCTS_EXCEL = False
AVAILABILITY_BEGIN_FROM = 0

IF_ARCHIVE_PRODUCTS_FROM_JSON = False


if IF_IMPORT_FIELDS:
    OdooImport.logger.info(f'BEGINNING FIELDS IMPORT')
    OdooImport.import_fields(Util.ODOO_CUSTOM_FIELDS)
    OdooImport.logger.info(f'FINISHED FIELDS IMPORT')

if IF_IMPORT_PUBLIC_CATEGORIES:
    OdooImport.logger.info(f'BEGINNING PRODUCTS PUBLIC CATEGORIES IMPORT')
    OdooImport.import_public_categories(PRODUCTS_PUBLIC_CATEGORIES_FILE_PATH, PRODUCTS_PUBLIC_CATEGORIES_BEGIN_FROM)
    OdooImport.logger.info(f'FINISHED PRODUCTS PUBLIC CATEGORIES IMPORT')

if IF_IMPORT_BRANDS:
    OdooImport.logger.info(f'BEGINNING BRANDS IMPORT')
    OdooImport.import_brands(BRANDS_EXCEL_FILE_PATH)
    OdooImport.logger.info(f'FINISHED BRANDS IMPORT')

if IF_IMPORT_PRODUCTS:
    OdooImport.logger.info(f'BEGINNING PRODUCTS IMPORT')
    OdooImport.import_products(TARGET_DATA_DIR_PATH, UPLOADED_DATA_DIR_PATH, IF_SKIP_EXISTING, USE_PRIORITY_EXCEL, IF_FORCE_UPDATE)
    OdooImport.logger.info(f'FINISHED PRODUCTS IMPORT')

if IF_IMPORT_ACC:
    OdooImport.logger.info(f'BEGINNING ACCESSORIES IMPORT')
    OdooImport.import_accessories(TARGET_DATA_DIR_PATH)
    OdooImport.logger.info(f'FINISHED ACCESSORIES IMPORT')

if IF_IMPORT_IMGS_AND_VIDEOS:
    OdooImport.logger.info(f'BEGINNING IMGS & VIDEOS IMPORT')
    OdooImport.import_imgs_videos(TARGET_MEDIA_DIR_PATH, UPLOADED_MEDIA_DIR_PATH, SKIP_PRODUCTS_W_MEDIA, IF_CLEAN_EXISTING)
    OdooImport.logger.info(f'FINISHED IMGS & VIDEOS IMPORT')

if IF_IMPORT_ICONS:
    OdooImport.logger.info(f'BEGINNING ICONS IMPORT')
    OdooImport.import_icons(ICONS_BEGIN_FROM)
    OdooImport.logger.info(f'FINISHED ICONS IMPORT')

if IF_IMPORT_SPEC_SHEETS:
    OdooImport.logger.info(f'BEGINNING SPEC SHEETS IMPORT')
    OdooImport.import_spec_sheets(IF_UPDATE_SPEC_SHEETS, SPEC_SHEETS_BEGIN_FROM)
    OdooImport.logger.info(f'FINISHED SPEC SHEETS IMPORT')

if IF_IMPORT_PDFS:
    OdooImport.logger.info(f'BEGINNING PDFS IMPORT')
    OdooImport.import_pdfs(PDF_BEGIN_FROM, IF_CLEAN_ATTACHMENTS, SKIP_PRODUCTS_W_ATTACHMENTS)
    OdooImport.logger.info(f'FINISHED PDFS IMPORT')

if IF_IMPORT_SUPPLIER_INFO_AND_COST:
    OdooImport.logger.info(f'BEGINNING SUPPLIER INFO IMPORT')
    OdooImport.import_supplier_info(SUPPLIER_STOCK_EXCEL_FILE_PATH, SUPPLIER_PRICELIST_EXCEL_FILE_PATH, IF_UPDATE_MODE)
    OdooImport.logger.info(f'FINISHED SUPPLIER INFO IMPORT')

if IF_IMPORT_CORRECT_NAMES_FROM_EXCEL:
    OdooImport.logger.info(f'BEGINNING CORRECT NAMES IMPORT')
    OdooImport.import_correct_names_from_excel(Util.CORRECT_NAMES_EXCEL_PATH, IF_GET_CORRECT_NAMES_FROM_JSONS)
    OdooImport.logger.info(f'FINISHED CORRECT NAMES IMPORT')

if IF_IMPORT_DESCATALOGADOS_CATALOGO:
    OdooImport.logger.info(f'BEGINNING DESCATALOGADOS IMPORT')
    OdooImport.import_descatalogados_catalogo(Util.SKUS_CATALOGO_Q12024_FILE_PATH)
    OdooImport.logger.info(f'FINISHED DESCATALOGADOS IMPORT')

if IF_IMPORT_AVAILABILITY:
    OdooImport.logger.info(f'BEGINNING AVAILABILITY IMPORT')
    OdooImport.import_availability_vtac(SUPPLIER_STOCK_EXCEL_FILE_PATH, IF_GENERATE_MISSING_PRODUCTS_EXCEL, AVAILABILITY_BEGIN_FROM)
    OdooImport.logger.info(f'FINISHED AVAILABILITY IMPORT')

if IF_ARCHIVE_PRODUCTS_FROM_JSON:
    OdooImport.logger.info(f'BEGINNING PRODUCTS TO ARCHIVE IMPORT')
    OdooImport.archive_products_from_json(PRODUCT_TO_ARCHIVE_CONDITIONS_JSON_PATH)
    OdooImport.logger.info(f'FINISHED PRODUCTS TO ARCHIVE IMPORT')

if IF_IMPORT_LOCAL_STOCK:
    OdooImport.logger.info(f'BEGINNING LOCAL STOCK IMPORT')
    OdooImport.import_local_stock(LOCAL_STOCK_EXCEL_PATH)
    OdooImport.logger.info(f'FINISHED LOCAL STOCK IMPORT')
