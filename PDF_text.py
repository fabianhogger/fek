
from PyPDF2 import PdfReader
from datetime import date
import regex as re
import os

def get_date(): #xazos kwdikas
    # Returns the current local date in desired dd_mm_yyyy format
    today = str(date.today())
    today=today.split("-")
    today.reverse()
    today="_".join(today)
    today=".+"+today+".pdf"
    return today

def setter(func):
    def wrapper(self, value):
        func(self, value)
    return wrapper
class PDF_text():
    def __init__(self,path = None):
        if path:
            self.path = path
            self._reader = PdfReader(self.path)

    def __repr__(self):
        return f'ΦΕΚ,{self.teyxos}/{self.date}'
    
    def __getitem__(self,page: int):
        return self._reader.pages[page].extract_text()

    @property
    def len(self) -> int:
        return len(self._reader.pages)
    
    @property
    def text(self) -> str:
        return "".join([self[page] for page in range(self.len)])

    @property
    def date(self) -> str:
        page = self[1]
        date_pattern = r'\b\d{2}\.\d{2}\.\d{4}\b'
        try:
            date = re.search(date_pattern,page)
            return date.group()
        except:
            print('date not found')
            return None
        
    @property    
    def teyxos(self) -> str:
        page = self[0]


        pattern = r'ΤΕΥΧΟΣ.*?(\b[Α-ΩΔ\.]+\b)'
        try:
            teuxos = re.search(pattern,page)
            words = teuxos.group().split(' ')
            return words[2]
        except:
            print('teuxos not found')
            return 'teuxos not found'
    
    @teyxos.setter
    def teyxos(self,teuxos)-> None:
        if teuxos!=None:
            self._teyxos=teuxos
        

    @property
    def fullo(self) -> str:
        page = self[0]
        #print(page)
        pattern = r'Αρ\.\s+Φύλλου\s+(\d+)\s+'

        try:
            match = re.search(pattern, page)
            if match:
                return match.group()
            else:
                print('Αρ. Φύλλου not found')
                return None
        except Exception as e:
            print('Error extracting Αρ. Φύλλου:', e)
            return None
    @fullo.setter
    def fullo(self,leaf)-> None:
        if leaf!=None:
            self._fullo=leaf
                    

    
    def __gt__(self,other) -> bool: #compare FEKS by date GREATER = OLDER
        return date.strptime(self.date, "%d.%m.%Y").date() > date.strptime(other.date, "%d.%m.%Y").date()



    
class Twitter:
    def __init__(self, credentials: dict, *args, **kwargs ):
        self.credentials = credentials

    @staticmethod
    def construct_tweet(pdf: PDF_text, post: bool = False):
        pass
        # PARSE IMPORTANT INFO,using regex, GPT and a DICT OF LAW TERMS

