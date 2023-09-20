from vtac_spain.scrapper_es import ScraperVtacSpain
from utils.util import Util


# VTAC ES SCRAPER

# Datos productos
IF_EXTRACT_ITEM_INFO = True
# PDFs productos
IF_DL_ITEM_PDF = False
# Enlaces productos en la página de origen
IF_EXTRACT_ITEM_LINKS, IF_UPDATE = False, False
# Todos los campos de los productos a implementar en ODOO
IF_EXTRACT_DISTINCT_ITEMS_FIELDS = False

# LINK EXTRACTION
if IF_EXTRACT_ITEM_LINKS:
    ScraperVtacSpain.instantiate_driver()
    ScraperVtacSpain.logger.info(f'BEGINNING LINK EXTRACTION TO {ScraperVtacSpain.PRODUCTS_LINKS_PATH}')

    # EXTRACT LINKS TO A set()
    extracted_links, links_new = ScraperVtacSpain.extract_all_links(ScraperVtacSpain.DRIVER, ScraperVtacSpain.CATEGORIES_LINKS, IF_UPDATE)

    Util.dump_to_json(list(extracted_links), ScraperVtacSpain.PRODUCTS_LINKS_PATH)
    if links_new:
        Util.dump_to_json(list(links_new),ScraperVtacSpain.NEW_PRODUCTS_LINKS_PATH)

    ScraperVtacSpain.logger.info(
        f'FINISHED LINK EXTRACTION TO {ScraperVtacSpain.PRODUCTS_LINKS_PATH}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    ScraperVtacSpain.instantiate_driver()
    ScraperVtacSpain.logger.info(
        f'BEGINNING PRODUCT INFO EXTRACTION TO {ScraperVtacSpain.PRODUCTS_INFO_PATH}')
    # EXTRACTION OF ITEMS INFO TO PRODUCT_INFO
    Util.begin_items_info_extraction(
        ScraperVtacSpain,
        ScraperVtacSpain.PRODUCTS_LINKS_PATH,
        ScraperVtacSpain.PRODUCTS_INFO_PATH,
        ScraperVtacSpain.PRODUCTS_MEDIA_PATH,
        ScraperVtacSpain.logger,
        ScraperVtacSpain.BEGIN_SCRAPE_FROM,
    )
    ScraperVtacSpain.logger.info(
        f'FINISHED PRODUCT INFO EXTRACTION TO {ScraperVtacSpain.PRODUCTS_INFO_PATH}')

# PDF DL
if IF_DL_ITEM_PDF:
    ScraperVtacSpain.instantiate_driver()
    ScraperVtacSpain.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {ScraperVtacSpain.PRODUCTS_PDF_PATH}')
    Util.begin_items_pdf_download(
        ScraperVtacSpain,
        ScraperVtacSpain.CATEGORIES_LINKS,
        ScraperVtacSpain.PRODUCTS_PDF_PATH,
        'ES',
        ScraperVtacSpain.logger
    )
    ScraperVtacSpain.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {ScraperVtacSpain.PRODUCTS_PDF_PATH}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    ScraperVtacSpain.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(ScraperVtacSpain.PRODUCTS_INFO_PATH, ScraperVtacSpain.PRODUCTS_FIELDS_JSON_PATH, ScraperVtacSpain.PRODUCTS_FIELDS_EXCEL_PATH)
    Util.extract_fields_example_to_excel(ScraperVtacSpain.PRODUCTS_INFO_PATH, ScraperVtacSpain.PRODUCTS_EXAMPLE_FIELDS_JSON_PATH, ScraperVtacSpain.PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH)
    ScraperVtacSpain.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

try:
    url = ScraperVtacSpain.DRIVER.current_url
    ScraperVtacSpain.DRIVER.quit()
except AttributeError:
    pass
