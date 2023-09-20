from utils import odoo_import as odoo_imp

# TODO TEST
IF_IMPORT_PRODUCTS = False
# TODO TEST
IF_IMPORT_ACC = False
# TODO TEST
IF_IMPORT_PDFS = False
# TODO TEST
IF_IMPORT_IMGS = True
# TODO TEST
IF_IMPORT_ICONS = True

# ODOO IMPORT
if IF_IMPORT_PRODUCTS:
    odoo_imp.logger.info(f'BEGINNING PRODUCTS IMPORT')
    odoo_imp.import_products()
    odoo_imp.logger.info(f'FINISHED PRODUCTS IMPORT')

if IF_IMPORT_ACC:
    odoo_imp.logger.info(f'BEGINNING ACCESSORIES IMPORT')
    odoo_imp.import_accessories()
    odoo_imp.logger.info(f'FINISHED ACCESSORIES IMPORT')

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