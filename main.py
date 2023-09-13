import odoo_import as odoo_imp
from data_merger import DataMerger
from util import Util


# DATA MERGING
if DataMerger.IF_MERGE:
    DataMerger.logger.info('BEGINNING DATA MERGING')
    DataMerger.extract_merged_data()
    DataMerger.logger.info('FINISHED DATA MERGING')
if DataMerger.IF_EXTRACT_FIELDS:
    DataMerger.logger.info('BEGINNING FIELD EXTRACTION')
    Util.extract_distinct_fields_to_excel(DataMerger.MERGED_DATA_DIR_PATH)
    DataMerger.logger.info('FINISHED FIELD EXTRACTION')


# ODOO IMPORT
if odoo_imp.IF_IMPORT_PRODUCTS:
    print(f'BEGINNING PRODUCTS IMPORT')
    odoo_imp.import_products()
    print(f'FINISHED PRODUCTS IMPORT')

if odoo_imp.IF_IMPORT_ACC:
    print(f'BEGINNING ACCESSORIES/KITS IMPORT')
    odoo_imp.import_accessories_kits()
    print(f'FINISHED ACCESSORIES/KITS IMPORT')

if odoo_imp.IF_IMPORT_PDFS:
    print(f'BEGINNING PDFS IMPORT')
    odoo_imp.import_pdfs()
    print(f'FINISHED PDFS IMPORT')

if odoo_imp.IF_IMPORT_IMGS:
    print(f'BEGINNING IMGS IMPORT')
    odoo_imp.import_imgs()
    print(f'FINISHED IMGS IMPORT')

if odoo_imp.IF_IMPORT_ICONS:
    print(f'BEGINNING ICONS IMPORT')
    odoo_imp.import_icons()
    print(f'FINISHED ICONS IMPORT')