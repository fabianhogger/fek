from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
driver = webdriver.Chrome("C:/Users/30697/trialenviroment/chromedriver_win/chromedriver.exe")
driver.get("https://www.et.gr/SearchFekLektiko")
title = driver.title
print("title :",title)
driver.implicitly_wait(3)
#element.send_keys("Α.Σ.Ε.Π")

#search = driver.find_element(By.ID, "Search")
#search.click()
driver.implicitly_wait(10)
#search.click()
#teyxos_input = driver.find_element(By.CLASS_NAME, "dx-texteditor-input-container")
#teyxos_input.click()

dropdown= driver.find_element(By.CLASS_NAME, "dx-dropdowneditor-input-wrapper")
driver.implicitly_wait(10)

dropdown.click()
table = driver.find_element(By.CLASS_NAME, "dx-scrollable-wrapper")
print(table)
table = driver.find_element(By.CLASS_NAME, "dx-scrollable-container")
print(table)
table = driver.find_element(By.ID, "EtiTeyxiLekt")
print(table)
locator = (By.ID, "popup")
#search = driver.find_element_by_xpath("//*[@id='Search']/div/div[2]/div")
#search.click()

EmbeddedDataGridSingle = driver.find_element_by_id("EmbeddedDataGridSingle")

# Find the first row of the datagrid
rows = driver.find_elements(By.CLASS_NAME ,"dx-row")
for row in rows:
    if row.text=="2023 Α":
        row.click()

#first_row=first_row[0]
# Scroll the row into view
#driver.execute_script("arguments[0].scrollIntoView(true);", first_row)

#data_grid_container = driver.find_element_by_id("dataGridContainer")


"""
dx-scrollable-wrapper
dx-scrollable-container
dx-datagrid-content
dx-datagrid-table dx-datagrid-table-fixed
"""
