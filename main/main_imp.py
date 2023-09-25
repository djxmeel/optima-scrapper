from utils.odoo_import import OdooImport
from utils.loggers import Loggers


IF_IMPORT_FIELDS = True

IF_IMPORT_PRODUCTS = False
# TODO TEST
IF_IMPORT_ACC = False
# TODO TEST
IF_IMPORT_PDFS = False
# TODO TEST
IF_IMPORT_IMGS = False
# TODO TEST
IF_IMPORT_ICONS = False

OdooImport.logger = Loggers.setup_odoo_import_logger()

# ODOO IMPORT
if IF_IMPORT_FIELDS:
    OdooImport.logger.info(f'BEGINNING FIELDS IMPORT')
    OdooImport.import_fields()
    OdooImport.logger.info(f'FINISHED FIELDS IMPORT')

if IF_IMPORT_PRODUCTS:
    OdooImport.logger.info(f'BEGINNING PRODUCTS IMPORT')
    OdooImport.import_products()
    OdooImport.logger.info(f'FINISHED PRODUCTS IMPORT')

if IF_IMPORT_ACC:
    OdooImport.logger.info(f'BEGINNING ACCESSORIES IMPORT')
    OdooImport.import_accessories()
    OdooImport.logger.info(f'FINISHED ACCESSORIES IMPORT')

if IF_IMPORT_PDFS:
    OdooImport.logger.info(f'BEGINNING PDFS IMPORT')
    OdooImport.import_pdfs()
    OdooImport.logger.info(f'FINISHED PDFS IMPORT')

if IF_IMPORT_IMGS:
    OdooImport.logger.info(f'BEGINNING IMGS IMPORT')
    OdooImport.import_imgs()
    OdooImport.logger.info(f'FINISHED IMGS IMPORT')

if IF_IMPORT_ICONS:
    OdooImport.logger.info(f'BEGINNING ICONS IMPORT')
    OdooImport.import_icons()
    OdooImport.logger.info(f'FINISHED ICONS IMPORT')