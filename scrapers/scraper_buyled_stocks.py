import time
from datetime import datetime

from appium import webdriver
from appium.options.android import UiAutomator2Options

import utils.playground as playground
from utils.odoo_import import OdooImport
from utils.util import Util

# TODO - Implement the scraper for the BuyLed stocks
# The scraper should be able to:
# 1. Start the scraping process
# 2. Get the stock data for all SKUS present in ODOO16
# 3. Save the stock data to a json named 'buyled_stocks_{date}.json' in the output_dir_path
class ScraperBuyLedStocks():
    capabilities = dict(
        platformName='Android',
        automationName='UiAutomator2',
        deviceName='Medium_Phone_API_23',
        appPackage='es.buyled.buyledpro',
        appActivity='.MainActivity t24',
        language='en',
        locale='US',
        noReset=True
    )

    appium_server_url = 'http://localhost:4723'
    driver = webdriver.Remote(appium_server_url, options=UiAutomator2Options().load_capabilities(capabilities))

    edittext_field = '//android.widget.EditText[@text="Búsqueda SKU"]'
    search_btn = '//android.widget.EditText[@text="Búsqueda SKU"]/android.widget.Button'
    stock_ita_text = "(//android.view.View[@content-desc='0'])[2]"
    stock_buyled_text = "(//android.view.View[@content-desc='0'])[1]"

    @classmethod
    def start_scrape(cls, output_dir_path):
        products_odoo = OdooImport.browse_all_products_in_batches()
        stock_data = []

        for product in products_odoo:
            sku = product.default_code
            cls.search_sku(sku)
            time.sleep(1)
            stock_data.append(cls.get_stock_data(sku))

        Util.dump_to_json(stock_data, f'{output_dir_path}/buyled_stocks_{datetime.now().strftime("%m-%d-%Y, %Hh %Mmin %Ss")}.json')
        cls.end_scrape()
    @classmethod
    def end_scrape(cls):
        cls.driver.quit()

    @classmethod
    def get_stock_data(cls, sku):
        return {
            'sku': sku,
            'stock_buyled': 0,
            'stock_ita': 0
        }

    @classmethod
    def search_sku(cls, sku):
        pass
