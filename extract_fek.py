from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
driver = webdriver.Chrome("C:/Users/30697/trialenviroment/chromedriver_win/chromedriver.exe")
driver.get("https://www.et.gr/SearchFekLektiko")
title = driver.title
print("title :",title)
driver.implicitly_wait(13)

dropdown= driver.find_element(By.CLASS_NAME, "dx-dropdowneditor-input-wrapper")
driver.implicitly_wait(10)
dropdown.click()

EmbeddedDataGridSingle = driver.find_element_by_id("EmbeddedDataGridSingle")

# Find the first row of the datagrid
rows = driver.find_elements(By.CLASS_NAME ,"dx-row")
for row in rows:
    if row.text=="2023 Α":
        row.click()

rows = driver.find_elements(By.CLASS_NAME ,"dx-texteditor-input")
for row in rows:
        if "30"==row.get_attribute('maxlength'):
            row.send_keys("ΑΣΕΠ")
            driver.implicitly_wait(1)
            row.send_keys(Keys.ENTER)
driver.implicitly_wait(5)
button = driver.find_element(By.CLASS_NAME ,"dx-button-content")
print(button.value_of_css_property())

"""
dx-texteditor-input

_id("dataGridContainer")
id="Search "
dx-scrollable-wrapper
dx-scrollable-container
dx-datagrid-content
dx-datagrid-table dx-datagrid-table-fixed
dx-texteditor-input-container
"""
