from selenium.common import WebDriverException
from vtac_spain.scrapper_es import ScraperVtacSpain
from util import Util


# VTAC ES SCRAPER
# LINK EXTRACTION
if ScraperVtacSpain.IF_EXTRACT_ITEM_LINKS:
    ScraperVtacSpain.logger.info(
        f'BEGINNING LINK EXTRACTION TO {Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')

    if not ScraperVtacSpain.IF_UPDATE:
        # EXTRACT LINKS TO A set()
        extracted_links = ScraperVtacSpain.extract_all_links(ScraperVtacSpain.DRIVER, ScraperVtacSpain.CATEGORIES_LINKS)

        Util.dump_to_json(list(extracted_links),
                          f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')
    else:
        extracted_links, links_new = ScraperVtacSpain.extract_all_links(ScraperVtacSpain.DRIVER,
                                                                        ScraperVtacSpain.CATEGORIES_LINKS, update=True)

        Util.dump_to_json(list(extracted_links),
                          f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')
        if links_new:
            Util.dump_to_json(list(links_new),
                              f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.NEW_VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')

    ScraperVtacSpain.logger.info(
        f'FINISHED LINK EXTRACTION TO {Util.VTAC_PRODUCTS_LINKS_FILE[ScraperVtacSpain.COUNTRY]}')

# PRODUCTS INFO EXTRACTION
if ScraperVtacSpain.IF_EXTRACT_ITEM_INFO:
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
if ScraperVtacSpain.IF_DL_ITEM_PDF:
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
if ScraperVtacSpain.IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    ScraperVtacSpain.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(
        f'{Util.VTAC_COUNTRY_DIR[ScraperVtacSpain.COUNTRY]}/{Util.VTAC_PRODUCT_INFO_LITE_DIR}')
    ScraperVtacSpain.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

try:
    url = ScraperVtacSpain.DRIVER.current_url
    ScraperVtacSpain.DRIVER.quit()
except WebDriverException:
    pass
