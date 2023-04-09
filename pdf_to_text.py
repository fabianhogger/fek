
from PyPDF2 import PdfReader
from datetime import date
import regex as re
import os
def get_date():
    # Returns the current local date in desired dd_mm_yyyy format
    today = str(date.today())
    today=today.split("-")
    today.reverse()
    today="_".join(today)
    today=".+"+today+".pdf"
    return today
def find_file():
    path = "C:/Users/30697/Downloads/"
    #scan downloads folder for file
    dir_list = os.listdir(path)
    dir_list=[filename for filename in dir_list if filename[-3:]=="pdf"]
    #match file with todays date in fileme
    today=get_date()
    file_to_extract=""
    for filename in dir_list:
        if( re.match(today,filename)):
            file_to_extract=filename
    full_path=path+file_to_extract
    return full_path
class PDF_text():
    def __init__(self):
        pass

    def read_text(self):
        full_path=find_file()
        # creating a pdf reader object
        reader = PdfReader(full_path)

        # printing number of pages in pdf file
        print(len(reader.pages))
        # getting a specific page from the pdf file
        page = reader.pages[0]
        # extracting text from page
        text = page.extract_text()
        print(text)
        return text
