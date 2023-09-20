from vtac_italia.scraper_ita import ScraperVtacItalia
from utils.util import Util


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
    ScraperVtacItalia.logger.info(f'BEGINNING LINK EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')

    # EXTRACT LINKS TO A set()
    extracted_links, links_new = ScraperVtacItalia.extract_all_links(ScraperVtacItalia.DRIVER, ScraperVtacItalia.CATEGORIES_LINKS, IF_UPDATE)

    Util.dump_to_json(list(extracted_links),
                      f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')
    if links_new:
        Util.dump_to_json(list(links_new),f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.NEW_PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')

    ScraperVtacItalia.logger.info(f'FINISHED LINK EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    ScraperVtacItalia.instantiate_driver()
    ScraperVtacItalia.logger.info(f'BEGINNING PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCT_DIR["info"]}')
    # EXTRACTION OF ITEMS INFO TO PRODUCT_INFO
    Util.begin_items_info_extraction(
        ScraperVtacItalia,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCT_DIR["info"]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCT_DIR["media"]}',
        ScraperVtacItalia.logger,
        ScraperVtacItalia.BEGIN_SCRAPE_FROM
    )
    ScraperVtacItalia.logger.info(f'FINISHED PRODUCT INFO EXTRACTION TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCT_DIR["info"]}')

# PDF DL
if IF_DL_ITEM_PDF:
    ScraperVtacItalia.instantiate_driver()
    ScraperVtacItalia.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCT_DIR["pdf"]}')
    Util.begin_items_PDF_download(
        ScraperVtacItalia,
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCTS_LINKS_FILE[ScraperVtacItalia.COUNTRY]}',
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCT_DIR["pdf"]}',
        'ITA',
        ScraperVtacItalia.logger
    )
    ScraperVtacItalia.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}/{Util.PRODUCT_DIR["pdf"]}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    ScraperVtacItalia.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}')
    Util.extract_fields_example_to_excel(f'{Util.VTAC_COUNTRY_DIR[ScraperVtacItalia.COUNTRY]}')
    ScraperVtacItalia.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')


try:
    url = ScraperVtacItalia.DRIVER.current_url
    ScraperVtacItalia.DRIVER.quit()
except AttributeError:
    pass