import requests
from pdf_to_text import PDF_text
from PyPDF2 import PdfWriter
import io

class Fek_getter:
    def __init__(self):
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

    def get_latest_fek():
        pass

    def get_fek_by_date():
        pass   

#api = r'https://www.et.gr/api/DownloadFeksApi/?fek_pdf=20240202730'

def test():
    for i in range(60):
        fullo=i
        pdf = Fek_getter().get_fek(year=2024,teuxos=1,fullo=fullo)
        if pdf:
            with open('PDFS/all_pdfs.txt','w',encoding='utf-8') as file:
                file.write(f'ΦΕΚ: Ημ/νια: {pdf.date}, Τεύχος: {pdf.teyxos}, Φύλλο: {fullo}, Σελίδες: {pdf.len}')
                print(f'ΦΕΚ: Ημ/νια: {pdf.date}, Τεύχος: {pdf.teyxos}, Φύλλο: {fullo}, Σελίδες: {pdf.len}')


