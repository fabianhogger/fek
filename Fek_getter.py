import requests
from PDF_text import PDF_text
from PyPDF2 import PdfWriter
import io
from collections import deque
import json

from orologia import Teuxos

class Fek_getter:
    def __init__(self, cache_memory: str = 'cache.json'):
        pass

    @staticmethod
    def get_fek(year: int = 2024, teuxos: int = 2, fullo: int = 2730) -> PDF_text:
        url = f'https://www.et.gr/api/DownloadFeksApi/?fek_pdf={year}{teuxos:02}{fullo:05}'
        res = requests.get(url)
        if res.status_code == 200: #gets pdf into bytes object, saves it locally and opens in with the PDF_text class
            pdf_writer = PdfWriter()
            pdf_file = io.BytesIO(res.content)
            pdf_writer.append(pdf_file)
            output_path = "PDFS/TEST.pdf"
            with open(output_path, "wb") as output_pdf:
                pdf_writer.write(output_pdf)
            return PDF_text(output_path)     
        else:
            return None
        
    @staticmethod
    def get_latest_fek(give_teuxos = Teuxos.ΠΡΑΔΙΤ) -> int:
        last_fullo = Fek_getter.fetch_cache(teuxos = give_teuxos)
        print(give_teuxos.value,last_fullo)
        try_last = last_fullo
        try:
            last_fek = Fek_getter.get_fek(year = 2024,teuxos=give_teuxos.value ,fullo=try_last)
            if last_fek:
                a= Fek_getter.update_cache(teuxos = give_teuxos, last_fullo = try_last)
                print(a)
                return last_fek
        except:
            raise RuntimeError


    @staticmethod
    def update_cache(memory = 'cache.json',teuxos: int = Teuxos.ΑΣΕΠ ,last_fullo : int = 15):
        with open(memory, 'r+',encoding = 'utf-8') as file:
            data = json.load(file)
            data[teuxos.name][1] = last_fullo
            file.seek(0)
            json.dump(data, file, indent=4, ensure_ascii=False)
            file.truncate()
            return (f'cache updated {teuxos} to {last_fullo}')

    @staticmethod
    def fetch_cache(memory='cache.json', teuxos=Teuxos.ΠΡΩΤΟ):
        with open(memory, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data[teuxos.name][1]

    def get_fek_by_date():
        pass   

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
        if pdf:
            with open('PDFS/all_pdfs.txt','w',encoding='utf-8') as file:
                file.write(f'ΦΕΚ: Ημ/νια: {pdf.date}, Τεύχος: {pdf.teyxos}, Φύλλο: {fullo_num}, Σελίδες: {pdf.len}')
                print(f'ΦΕΚ: Ημ/νια: {pdf.date}, Τεύχος: {pdf.teyxos}, Φύλλο: {fullo_num}, Σελίδες: {pdf.len}')

#test()
