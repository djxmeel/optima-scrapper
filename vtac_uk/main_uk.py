from selenium.common import WebDriverException
from vtac_uk.scraper_uk import ScraperVtacUk
from util import Util


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
    ScraperVtacUk.logger.info(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacUk.COUNTRY]}')

    if not IF_UPDATE:
        # EXTRACT LINKS TO A set()
        extracted_links = ScraperVtacUk.extract_all_links(ScraperVtacUk.DRIVER, ScraperVtacUk.CATEGORIES_LINKS)

        Util.dump_to_json(list(extracted_links),f'{Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacUk.COUNTRY]}')
    else:
        extracted_links, links_new = ScraperVtacUk.extract_all_links(ScraperVtacUk.DRIVER, ScraperVtacUk.CATEGORIES_LINKS, update=True)

        Util.dump_to_json(list(extracted_links),
                          f'{Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacUk.COUNTRY]}')
        if links_new:
            Util.dump_to_json(list(links_new),f'{Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.NEW_VTAC_PRODUCTS_LINKS_FILE[ScraperVtacUk.COUNTRY]}')

    ScraperVtacUk.logger.info(f'FINISHED LINK EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacUk.COUNTRY]}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    ScraperVtacUk.instantiate_driver()
    ScraperVtacUk.logger.info(f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}')
    # EXTRACTION OF ITEMS INFO TO VTAC_PRODUCT_INFO
    Util.begin_items_info_extraction(
        ScraperVtacUk,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacUk.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}',
        ScraperVtacUk.logger,
        ScraperVtacUk.BEGIN_SCRAPE_FROM
    )
    ScraperVtacUk.logger.info(f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}')

# PDF DL
if IF_DL_ITEM_PDF:
    ScraperVtacUk.instantiate_driver()
    ScraperVtacUk.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}')
    Util.begin_items_PDF_download(
        ScraperVtacUk,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacUk.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}',
        'UK',
        ScraperVtacUk.logger
    )
    ScraperVtacUk.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    ScraperVtacUk.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(f'{Util.VTAC_COUNTRY_DIR[ScraperVtacUk.COUNTRY]}')
    ScraperVtacUk.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

try:
    url = ScraperVtacUk.DRIVER.current_url
    ScraperVtacUk.DRIVER.quit()
except AttributeError:
    pass
