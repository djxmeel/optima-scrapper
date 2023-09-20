from scrapers.scraper_ita import ScraperVtacItalia
from scrapers.scrapper_es import ScraperVtacSpain
from utils.util import Util
from scrapers.scraper_uk import ScraperVtacUk

# VTAC SCRAPER

country_scrapers = {
    'es' : ScraperVtacSpain,
    'uk' : ScraperVtacItalia,
    'ita' : ScraperVtacUk
}

# Prompt user to choose country
while True:
    chosen_country = input(f'ELEGIR PAÍS PARA EL SCRAPING ({country_scrapers.keys()}) :')
    if chosen_country.strip().lower() in country_scrapers:
        break
    print("País no válido, inténtelo de nuevo")

scraper = country_scrapers[chosen_country]

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
    scraper.instantiate_driver()
    scraper.logger.info(f'BEGINNING LINK EXTRACTION TO {scraper.PRODUCTS_LINKS_PATH}')

    # EXTRACT LINKS TO A set()
    extracted_links, links_new = scraper.extract_all_links(scraper.DRIVER, scraper.CATEGORIES_LINKS, IF_UPDATE)

    Util.dump_to_json(list(extracted_links), scraper.PRODUCTS_LINKS_PATH)
    if links_new:
        Util.dump_to_json(list(links_new),scraper.NEW_PRODUCTS_LINKS_PATH)

    scraper.logger.info(
        f'FINISHED LINK EXTRACTION TO {scraper.PRODUCTS_LINKS_PATH}')

# PRODUCTS INFO EXTRACTION
if IF_EXTRACT_ITEM_INFO:
    scraper.instantiate_driver()
    scraper.logger.info(
        f'BEGINNING PRODUCT INFO EXTRACTION TO {scraper.PRODUCTS_INFO_PATH}')
    # EXTRACTION OF ITEMS INFO TO PRODUCT_INFO
    Util.begin_items_info_extraction(
        scraper,
        scraper.PRODUCTS_LINKS_PATH,
        scraper.PRODUCTS_INFO_PATH,
        scraper.PRODUCTS_MEDIA_PATH,
        scraper.logger,
        scraper.BEGIN_SCRAPE_FROM,
    )
    scraper.logger.info(
        f'FINISHED PRODUCT INFO EXTRACTION TO {scraper.PRODUCTS_INFO_PATH}')

# PDF DL
if IF_DL_ITEM_PDF:
    scraper.instantiate_driver()
    scraper.logger.info(f'BEGINNING PRODUCT PDFs DOWNLOAD TO {scraper.PRODUCTS_PDF_PATH}')
    Util.begin_items_pdf_download(
        scraper,
        scraper.CATEGORIES_LINKS,
        scraper.PRODUCTS_PDF_PATH,
        scraper.logger
    )
    scraper.logger.info(f'FINISHED PRODUCT PDFs DOWNLOAD TO {scraper.PRODUCTS_PDF_PATH}')

# DISTINCT FIELDS EXTRACTION TO JSON THEN CONVERT TO EXCEL
if IF_EXTRACT_DISTINCT_ITEMS_FIELDS:
    scraper.logger.info(f'BEGINNING DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')
    Util.extract_distinct_fields_to_excel(scraper.PRODUCTS_INFO_PATH, scraper.PRODUCTS_FIELDS_JSON_PATH, scraper.PRODUCTS_FIELDS_EXCEL_PATH)
    Util.extract_fields_example_to_excel(scraper.PRODUCTS_INFO_PATH, scraper.PRODUCTS_EXAMPLE_FIELDS_JSON_PATH, scraper.PRODUCTS_EXAMPLE_FIELDS_EXCEL_PATH)
    scraper.logger.info(f'FINISHED DISTINCT FIELDS EXTRACTION TO JSON THEN EXCEL')

try:
    url = scraper.DRIVER.current_url
    scraper.DRIVER.quit()
except AttributeError:
    pass
