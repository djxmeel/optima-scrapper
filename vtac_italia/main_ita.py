from selenium.common import WebDriverException
from vtac_italia.scraper_ita import ScraperVtacItalia
from util import Util


# VTAC ITA SCRAPER

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
    ScraperVtacItalia.instantiate_driver()
    ScraperVtacItalia.logger.info(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')

    if not IF_UPDATE:
        # EXTRACT LINKS TO A set()
        extracted_links = ScraperVtacItalia.extract_all_links(ScraperVtacItalia.DRIVER, ScraperVtacItalia.CATEGORIES_LINKS)

        Util.dump_to_json(list(extracted_links),
                          f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')
    else:
        extracted_links, links_new = ScraperVtacItalia.extract_all_links(ScraperVtacItalia.DRIVER,
                                                                     ScraperVtacItalia.CATEGORIES_LINKS, update=True)

        Util.dump_to_json(list(extracted_links),
                          f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')
        if links_new:
            Util.dump_to_json(list(links_new),f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.NEW_VTAC_PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')

    ScraperVtacItalia.logger.info(f'FINISHED LINK EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    ScraperVtacItalia.instantiate_driver()
    ScraperVtacItalia.logger.info(f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}')
    # EXTRACTION OF ITEMS INFO TO VTAC_PRODUCT_INFO
    Util.begin_items_info_extraction(
        ScraperVtacItalia,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}',
        ScraperVtacItalia.logger,
        ScraperVtacItalia.BEGIN_SCRAPE_FROM
    )
    ScraperVtacItalia.logger.info(f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_INFO_DIR}')

# PDF DL
if IF_DL_ITEM_PDF:
    ScraperVtacItalia.instantiate_driver()
    ScraperVtacItalia.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}')
    Util.begin_items_PDF_download(
        ScraperVtacItalia,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}',
        'ITA',
        ScraperVtacItalia.logger
    )
    ScraperVtacItalia.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.VTAC_PRODUCT_PDF_DIR}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    ScraperVtacItalia.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}')
    ScraperVtacItalia.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')


try:
    url = ScraperVtacItalia.DRIVER.current_url
    ScraperVtacItalia.DRIVER.quit()
except AttributeError:
    pass