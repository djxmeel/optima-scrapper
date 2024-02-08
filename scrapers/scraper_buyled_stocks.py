import time
from datetime import datetime

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common import NoSuchElementException

from utils.odoo_import import OdooImport
from utils.util import Util


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
        newCommandTimeout=600,
        noReset=False
    )

    appium_server_url = 'http://localhost:4723'
    driver = None

    search_field_locator = 'className("android.widget.EditText")'
    btn_locator = 'className("android.widget.Button")'

    # Buy led stock index = 0 ; ITA stock index = 1
    stock_buyled_locator = 'className("android.view.View").index(7)'
    stock_ita_locator = 'className("android.view.View").index(9)'
    price_locator = 'className("android.view.View").index(11)'
    date_locator = 'className("android.view.View").index(13)'

    login_fields_locator = 'className("android.widget.EditText")'
    email_field_index = 0
    password_field_index = 1

    @classmethod
    def start_scrape(cls, output_dir_path):
        products_odoo = OdooImport.browse_all_products_in_batches('product_brand_id', '=', OdooImport.VTAC_BRAND_ID)
        stock_data = []

        cls.driver = webdriver.Remote(cls.appium_server_url, options=UiAutomator2Options().load_capabilities(cls.capabilities))

        cls.login()

        for index, product in enumerate(products_odoo):
            sku = product.default_code
            if not sku:
                continue
            cls.search_sku(sku)
            fetched_data = cls.get_stock_data(sku)

            if fetched_data:
                print(f'{index+1}. {fetched_data}')
                stock_data.append(fetched_data)
            if index % 50 == 0 and index != 0 or index == len(products_odoo) - 1:
                Util.dump_to_json(stock_data, f'{output_dir_path}/buyled_stocks_{index+1}.json')
                stock_data = []
        cls.end_scrape()
    @classmethod
    def end_scrape(cls):
        cls.driver.quit()

    @classmethod
    def get_stock_data(cls, sku):
        try:
            stock_buyled_text = cls.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, cls.stock_buyled_locator).get_attribute('content-desc')
            stock_ita_text = cls.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, cls.stock_ita_locator).get_attribute('content-desc')
            price_text = cls.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, cls.price_locator).get_attribute('content-desc')

            try:
                date_text = cls.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, cls.date_locator).get_attribute('content-desc')
            except NoSuchElementException:
                date_text = None

            return {
                'sku': sku,
                'stock_buyled': int(stock_buyled_text),
                'stock_ita': int(stock_ita_text),
                'price': price_text,
                'date': date_text
            }
        except NoSuchElementException:
            print(f'No stock data found for SKU: {sku}')
            return None

    @classmethod
    def search_sku(cls, sku):
        search_field_element = cls.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, cls.search_field_locator)
        search_field_element.click()
        search_field_element.send_keys(sku)
        cls.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, cls.btn_locator)[2].click()
        time.sleep(1)

    @classmethod
    def login(cls):
        login_fields_elements = cls.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, cls.login_fields_locator)
        email_login_element = login_fields_elements[cls.email_field_index]
        password_login_element = login_fields_elements[cls.password_field_index]

        email_login_element.click()
        email_login_element.send_keys('compras@optimaluz.com')

        password_login_element.click()
        password_login_element.send_keys('compras@optimaluz.com')

        cls.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, f'{cls.btn_locator}.description("Entrar")').click()
        print('Logged in BuyLed app')
        time.sleep(5)

ScraperBuyLedStocks.start_scrape('data/buyled_stocks')