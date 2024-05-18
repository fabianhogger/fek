import requests
from PDF_text import PDF_text
from PyPDF2 import PdfWriter
import io
from collections import deque
import json

from orologia import Teuxos

class Fek_getter:
    def __init__(self, cache_memory: str = 'cache.json'):
        self.memory = cache_memory

    @staticmethod
    def get_fek(year: int = 2024, teuxos: int = 2, fullo: int = 2730) -> str:
        url = f'https://www.et.gr/api/DownloadFeksApi/?fek_pdf={year}{teuxos:02}{fullo:05}'
        res = requests.get(url)
        if res.status_code == 200: #gets pdf into bytes object, saves it locally and opens in with the PDF_text class
            pdf_writer = PdfWriter()
            pdf_file = io.BytesIO(res.content)
            pdf_writer.append(pdf_file)
            output_path = "PDFS/TEST.pdf"
            with open(output_path, "wb") as output_pdf:
                pdf_writer.write(output_pdf)
            if PDF_text(output_path):
                return output_path     
        else:
            return False
        
    
    def get_latest_fek(self,give_teuxos = Teuxos.ΔΕΥΤΕΡΟ, update_cache = False) -> int:
        last_fullo = self.fetch_cache(teuxos = give_teuxos)
        #print(give_teuxos.value,last_fullo)
        try_last = last_fullo+1
        for i in range(3):
            try:
                last_fek = self.get_fek(year = 2024,teuxos=give_teuxos.value ,fullo=try_last)
                if last_fek and update_cache==True:
                    self.update_cache(teuxos = give_teuxos, last_fullo = try_last)
                    return last_fek
                elif last_fek:
                    return last_fek
                else:    
                    try_last+=1
            except:
                raise RuntimeError
        print(f'No FEKS today for {give_teuxos}')


    def update_cache(self,teuxos: int = Teuxos.ΔΕΥΤΕΡΟ ,last_fullo : int = 15):
        with open(self.memory, 'r+',encoding = 'utf-8') as file:
            data = json.load(file)
            data[teuxos.name][1] = last_fullo
            file.seek(0)
            json.dump(data, file, indent=4, ensure_ascii=False)
            file.truncate()
            return (f'cache updated {teuxos} to {last_fullo}')

    def fetch_cache(self, teuxos=Teuxos.ΠΡΩΤΟ):
        with open(self.memory, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data[teuxos.name][1]

    def get_fek_by_date():
        pass
"""if __name__ == "__main__":
    #api = r'https://www.et.gr/api/DownloadFeksApi/?fek_pdf=20240202730'
    a = Fek_getter()
    b= a.fetch_cache()
    pdf = a.get_latest_fek()
    if pdf:
        print(b)
        print(f'ΦΕΚ: Ημ/νια: {pdf.date}, Τεύχος: {pdf.teyxos}, Φύλλο: {1}, Σελίδες: {pdf.len}')
        print(pdf[0])


    def test():
        for i in range(60):
            fullo_num=i
            pdf = Fek_getter().get_fek(year=2024,teuxos=10,fullo=fullo_num)
            print(pdf)
            if pdf:
                with open('PDFS/all_pdfs.txt','a',encoding='utf-8') as file:
                    file.write(f'ΦΕΚ: Ημ/νια: {pdf.date}, Τεύχος: {pdf.teyxos}, Φύλλο: {fullo_num}, Σελίδες: {pdf.len}')
                    print(f'ΦΕΚ: Ημ/νια: {pdf.date}, Τεύχος: {pdf.teyxos}, Φύλλο: {fullo_num}, Σελίδες: {pdf.len}')

#api = r'https://www.et.gr/api/DownloadFeksApi/?fek_pdf=20240202730'"""

def main(update_cache = True):
    getter = Fek_getter()
    for teuxos in Teuxos:
        fek_path = getter.get_latest_fek(give_teuxos = teuxos, update_cache=update_cache)
        if fek_path:
            pdf = PDF_text(fek_path)
            print(f'ΦΕΚ: Ημ/νια: {pdf.date}, Τεύχος: {pdf.teyxos}, Σελίδες: {pdf.len}')
        #print(teuxos)
if __name__ == "__main__":
    main()


