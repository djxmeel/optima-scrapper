from utils import odoo_import as odoo_imp
from vtac_merged.data_merger import DataMerger
from utils.util import Util


IF_MERGE = True
IF_EXTRACT_FIELDS = True
# If False : only extracts CUSTOM fields presen in ODOO
IF_ALL_FIELDS = False

IF_IMPORT_PRODUCTS = True
IF_IMPORT_ACC = True
IF_IMPORT_PDFS = True
IF_IMPORT_IMGS = True
IF_IMPORT_ICONS = True

# DATA MERGING
if IF_MERGE:
    DataMerger.logger.info('BEGINNING DATA MERGING')
    DataMerger.extract_merged_data()
    DataMerger.logger.info('FINISHED DATA MERGING')
if IF_EXTRACT_FIELDS:
    DataMerger.logger.info('BEGINNING FIELD EXTRACTION')
    Util.extract_distinct_fields_to_excel(DataMerger.MERGED_DATA_DIR_PATH, extract_all=IF_ALL_FIELDS)
    # Util.extract_fields_example_to_excel(DataMerger.MERGED_DATA_DIR_PATH)
    DataMerger.logger.info('FINISHED FIELD EXTRACTION')


# ODOO IMPORT
if IF_IMPORT_PRODUCTS:
    odoo_imp.logger.info(f'BEGINNING PRODUCTS IMPORT')
    odoo_imp.import_products()
    odoo_imp.logger.info(f'FINISHED PRODUCTS IMPORT')

if IF_IMPORT_ACC:
    odoo_imp.logger.info(f'BEGINNING ACCESSORIES/KITS IMPORT')
    odoo_imp.import_accessories_kits()
    odoo_imp.logger.info(f'FINISHED ACCESSORIES/KITS IMPORT')

if IF_IMPORT_PDFS:
    odoo_imp.logger.info(f'BEGINNING PDFS IMPORT')
    odoo_imp.import_pdfs()
    odoo_imp.logger.info(f'FINISHED PDFS IMPORT')

if IF_IMPORT_IMGS:
    odoo_imp.logger.info(f'BEGINNING IMGS IMPORT')
    odoo_imp.import_imgs()
    odoo_imp.logger.info(f'FINISHED IMGS IMPORT')

if IF_IMPORT_ICONS:
    odoo_imp.logger.info(f'BEGINNING ICONS IMPORT')
    odoo_imp.import_icons()
    odoo_imp.logger.info(f'FINISHED ICONS IMPORT')