from appium import webdriver


desired_caps = {
    "platformName": "Android",
    "deviceName": "Android Emulator",
    "app": "/path/to/the/app.apk",
    "appPackage": "com.example.android",
    "appActivity": ".MainActivity",
    "noReset": True
}

driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
