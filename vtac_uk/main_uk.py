from vtac_uk.scraper_uk import ScraperVtacUk
from utils.util import Util


# VTAC UK SCRAPER

# Datos productos
IF_EXTRACT_ITEM_INFO = False
# PDFs productos
IF_DL_ITEM_PDF = False
# Enlaces productos en la página de origen
IF_EXTRACT_ITEM_LINKS, IF_UPDATE = True, True
# Todos los campos de los productos a implementar en ODOO
IF_EXTRACT_DISTINCT_ITEMS_FIELDS = False

# LINK EXTRACTION
if IF_EXTRACT_ITEM_LINKS:
    ScraperVtacUk.instantiate_driver()
    ScraperVtacUk.logger.info(f'BEGINNING LINK EXTRACTION TO {ScraperVtacUk.PRODUCTS_LINKS_PATH}')

    # EXTRACT LINKS TO A set()
    extracted_links, links_new = ScraperVtacUk.extract_all_links(ScraperVtacUk.DRIVER, ScraperVtacUk.CATEGORIES_LINKS, IF_UPDATE)

    Util.dump_to_json(list(extracted_links),f'{ScraperVtacUk.PRODUCTS_LINKS_PATH}')

    if links_new:
        Util.dump_to_json(list(links_new),f'{ScraperVtacUk.NEW_PRODUCTS_LINKS_PATH}')

    ScraperVtacUk.logger.info(f'FINISHED LINK EXTRACTION TO {ScraperVtacUk.PRODUCTS_LINKS_PATH}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    ScraperVtacUk.instantiate_driver()
    ScraperVtacUk.logger.info(f'BEGINNING PRODUCT INFO EXTRACTION TO {ScraperVtacUk.PRODUCTS_INFO_PATH}')
    # EXTRACTION OF ITEMS INFO TO PRODUCT_INFO
    Util.begin_items_info_extraction(
        ScraperVtacUk,
        f'{ScraperVtacUk.PRODUCTS_LINKS_PATH}',
        f'{ScraperVtacUk.PRODUCTS_INFO_PATH}',
        f'{ScraperVtacUk.PRODUCTS_MEDIA_PATH}',
        ScraperVtacUk.logger,
        ScraperVtacUk.BEGIN_SCRAPE_FROM
    )
    ScraperVtacUk.logger.info(f'FINISHED PRODUCT INFO EXTRACTION TO {ScraperVtacUk.PRODUCTS_INFO_PATH}')

# PDF DL
if IF_DL_ITEM_PDF:
    ScraperVtacUk.instantiate_driver()
    ScraperVtacUk.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {ScraperVtacUk.PRODUCTS_PDF_PATH}')
    Util.begin_items_pdf_download(
        ScraperVtacUk,
        f'{ScraperVtacUk.PRODUCTS_LINKS_PATH}',
        f'{ScraperVtacUk.PRODUCTS_PDF_PATH}',
        'UK',
        ScraperVtacUk.logger
    )
    ScraperVtacUk.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {ScraperVtacUk.PRODUCTS_PDF_PATH}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    ScraperVtacUk.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(ScraperVtacUk.PRODUCTS_INFO_PATH, ScraperVtacUk.PRODUCTS_FIELDS_JSON_PATH, ScraperVtacUk.PRODUCTS_FIELDS_EXCEL_PATH)
    Util.extract_fields_example_to_excel(ScraperVtacUk.PRODUCTS_INFO_PATH, ScraperVtacUk.PRODUCTS_EXAMPLE_FIELDS_JSON_PATH, ScraperVtacUk.PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH)
    ScraperVtacUk.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

try:
    url = ScraperVtacUk.DRIVER.current_url
    ScraperVtacUk.DRIVER.quit()
except AttributeError:
    pass
