import os.path
import time

from scrapers.scraper_vtac_ita import ScraperVtacItalia
from scrapers.scraper_vtac_es import ScraperVtacSpain
from utils.loggers import Loggers
from utils.util import Util
from scrapers.scraper_vtac_uk import ScraperVtacUk

# VTAC SCRAPER
# TODO reextract ITA & UK links to get categories (all UK products have just one categ.?)
country_scrapers = {
    'es': ScraperVtacSpain,
    'uk': ScraperVtacUk,
    'ita': ScraperVtacItalia
}

# Datos productos
# TODO TEST only new products extraction
IF_EXTRACT_ITEM_INFO, IF_ONLY_NEW_PRODUCTS = True, False

# PDFs productos
IF_DL_ITEM_PDF = False

# Enlaces productos en la página de origen
IF_EXTRACT_ITEM_LINKS, IF_UPDATE = True, False

# Todos los campos de los productos a implementar en ODOO
IF_EXTRACT_DISTINCT_ITEMS_FIELDS = False
# If False : only extracts CUSTOM fields present in ODOO
IF_ALL_FIELDS = False

chosen_country = Util.get_chosen_country_from_menu(country_scrapers, IF_EXTRACT_ITEM_LINKS, IF_UPDATE, IF_EXTRACT_ITEM_INFO, IF_ONLY_NEW_PRODUCTS, IF_DL_ITEM_PDF, IF_EXTRACT_DISTINCT_ITEMS_FIELDS)
scraper = country_scrapers[chosen_country]
scraper.logger = Loggers.setup_vtac_logger(chosen_country)

# LINK EXTRACTION
if IF_EXTRACT_ITEM_LINKS:
    scraper.instantiate_driver()
    start_time = time.time()

    scraper.logger.info(f'BEGINNING LINK EXTRACTION TO {scraper.PRODUCTS_LINKS_PATH}')

    # EXTRACT LINKS TO A set()
    extracted_links, links_new = scraper.extract_all_links(scraper.DRIVER, scraper.CATEGORIES_LINKS, IF_UPDATE)

    Util.dump_to_json(list(extracted_links), scraper.PRODUCTS_LINKS_PATH)
    if links_new:
        Util.dump_to_json(list(links_new), scraper.NEW_PRODUCTS_LINKS_PATH)

    elapsed_hours, elapsed_minutes, elapsed_seconds = Util.get_elapsed_time(start_time, time.time())
    scraper.logger.info(
        f'FINISHED LINK EXTRACTION TO {scraper.PRODUCTS_LINKS_PATH} in {elapsed_hours}h {elapsed_minutes}m {elapsed_seconds}s')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    scraper.instantiate_driver()
    start_time = time.time()

    scraper.logger.info(f'BEGINNING PRODUCT INFO EXTRACTION TO {scraper.PRODUCTS_INFO_PATH}')

    # Determine whether to extract to default or new products files
    if IF_ONLY_NEW_PRODUCTS:
        products_info_path = scraper.NEW_PRODUCTS_INFO_PATH
        products_media_path = scraper.NEW_PRODUCTS_MEDIA_PATH
        links_path = scraper.NEW_PRODUCTS_LINKS_PATH
    else:
        products_info_path = scraper.PRODUCTS_INFO_PATH
        products_media_path = scraper.PRODUCTS_MEDIA_PATH
        links_path = scraper.PRODUCTS_LINKS_PATH

    if not os.path.exists(links_path):
        scraper.logger.info(f'No links file found at {links_path}. Please extract links first.')
        exit()

    # EXTRACTION OF ITEMS INFO TO PRODUCT_INFO
    Util.begin_items_info_extraction(
        scraper,
        links_path,
        products_info_path,
        products_media_path,
        scraper.logger,
        scraper.BEGIN_SCRAPE_FROM
    )

    elapsed_hours, elapsed_minutes, elapsed_seconds = Util.get_elapsed_time(start_time, time.time())
    scraper.logger.info(
        f'FINISHED PRODUCT INFO EXTRACTION TO {scraper.PRODUCTS_INFO_PATH} IN {elapsed_hours}h {elapsed_minutes}m {elapsed_seconds}s')

# PDF DL
if IF_DL_ITEM_PDF:
    scraper.instantiate_driver()
    start_time = time.time()

    scraper.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {scraper.PRODUCTS_PDF_PATH}')
    Util.begin_items_pdf_download(
        scraper,
        scraper.PRODUCTS_LINKS_PATH,
        scraper.PRODUCTS_PDF_PATH,
        scraper.logger
    )

    elapsed_hours, elapsed_minutes, elapsed_seconds = Util.get_elapsed_time(start_time, time.time())
    scraper.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {scraper.PRODUCTS_PDF_PATH} IN {elapsed_hours}h {elapsed_minutes}m {elapsed_seconds}s')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    scraper.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(scraper.PRODUCTS_INFO_PATH, scraper.PRODUCTS_FIELDS_JSON_PATH, scraper.PRODUCTS_FIELDS_EXCEL_PATH, extract_all=IF_ALL_FIELDS)
    Util.extract_fields_example_to_excel(scraper.PRODUCTS_INFO_PATH, scraper.PRODUCTS_EXAMPLE_FIELDS_JSON_PATH, scraper.PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH)
    scraper.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

try:
    url = scraper.DRIVER.current_url
    scraper.DRIVER.quit()
except AttributeError:
    pass
