from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

def search():
    #find dropdown and select by clicking it
    dropdown= driver.find_element(By.CLASS_NAME, "dx-dropdowneditor-input-wrapper")
    driver.implicitly_wait(10)
    dropdown.click()
    EmbeddedDataGridSingle = driver.find_element_by_id("EmbeddedDataGridSingle")
    # Find all rows
    rows = driver.find_elements(By.CLASS_NAME ,"dx-row")
    for row in rows:
        # find row of dropdown
        if row.text=="2023 Α":
            row.click()
    #find all list of elements to narrow down to input field
    rows = driver.find_elements(By.CLASS_NAME ,"dx-texteditor-input")
    for row in rows:
            if "30"==row.get_attribute('maxlength'):
                #write to input
                row.send_keys("ΑΣΕΠ")
                driver.implicitly_wait(1)
                #press enter for website to pull the results
                row.send_keys(Keys.ENTER)
    driver.implicitly_wait(5)

def select_pdf():
    time.sleep(15)
    set_date()
    rows = driver.find_elements_by_tag_name("td")
    print(len(rows))
    for row in rows:
        if(row.get_attribute("aria-describedby")=="dx-col-11"):
            time.sleep(1)
            row.click()
            time.sleep(10)
            break
def set_date():
    rows = driver.find_elements_by_tag_name("input")
    print("set")
    for row in rows:
        if(row.get_attribute("aria-describedby")=="dx-col-9" and row.get_attribute("type")=="text"):
                #time.sleep(5)
                #row.click()
                #time.sleep(5)
                #row.send_keys("04/04/2023")
                #row.send_keys(Keys.ENTER)
                print(row)
                break


#load Driver
driver = webdriver.Chrome("C:/Users/30697/trialenviroment/chromedriver_win/chromedriver.exe")
#give link to detailed search
driver.get("https://www.et.gr/SearchFekLektiko")
#wait for website to load
driver.implicitly_wait(13)
search()
select_pdf()
