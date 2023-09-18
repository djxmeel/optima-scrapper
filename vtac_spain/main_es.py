from selenium.common import WebDriverException
from vtac_spain.scrapper_es import ScraperVtacSpain
from util import Util


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
    ScraperVtacSpain.logger.info(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')

    # EXTRACT LINKS TO A set()
    extracted_links, links_new = ScraperVtacSpain.extract_all_links(ScraperVtacSpain.DRIVER, ScraperVtacSpain.CATEGORIES_LINKS, IF_UPDATE)

    Util.dump_to_json(list(extracted_links),
                      f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')
    if links_new:
        Util.dump_to_json(list(links_new),
                          f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.NEW_VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')

    ScraperVtacSpain.logger.info(
        f'FINISHED LINK EXTRACTION TO {Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    ScraperVtacSpain.instantiate_driver()
    ScraperVtacSpain.logger.info(
        f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}')
    # EXTRACTION OF ITEMS INFO TO VTAC_PRODUCT_INFO
    Util.begin_items_info_extraction(
        ScraperVtacSpain,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}',
        ScraperVtacSpain.logger,
        ScraperVtacSpain.BEGIN_SCRAPE_FROM,
    )
    ScraperVtacSpain.logger.info(
        f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}')

# PDF DL
if IF_DL_ITEM_PDF:
    ScraperVtacSpain.instantiate_driver()
    ScraperVtacSpain.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_PRODUCT_PDF_DIR}')
    Util.begin_items_PDF_download(
        ScraperVtacSpain,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}',
        'ES',
        ScraperVtacSpain.logger
    )
    ScraperVtacSpain.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_PRODUCT_PDF_DIR}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    ScraperVtacSpain.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}')
    # Util.extract_fields_example_to_excel(f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}')
    ScraperVtacSpain.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

try:
    url = ScraperVtacSpain.DRIVER.current_url
    ScraperVtacSpain.DRIVER.quit()
except AttributeError:
    pass
