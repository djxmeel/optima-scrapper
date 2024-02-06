from appium import webdriver
from appium.options.android import UiAutomator2Options

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

    @classmethod
    def start_scrape(self, output_dir_path):
        pass

    @classmethod
    def get_stock_data(self, sku):
        return {
            'sku': sku,
            'stock_buyled': 0,
            'stock_ita': 0
        }

    @classmethod
    def search_sku(self, sku):
        pass
