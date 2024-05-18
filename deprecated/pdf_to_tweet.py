from pdf_to_text import PDF_text, Twitter
from orologia import YPOURGEIA_2024 as ypourgeia
import re


def kefalaio(text):
    matches = re.search(r'(ΚΕΦΑΛΑΙΟ?)', text)
    return matches

def arthra(pdf: PDF_text, art = 'Άρθρο') -> list:
    text = pdf.text
    arthra = re.split(art,text)
    for arthro in arthra:
        title_end = arthro.find('1.')
        title = art+arthro[:title_end]
        if len(title) <200:

            print(title)    


def paravaseis(pdf: PDF_text, mer = 'Η παράβαση') -> list:
    text = pdf.text
    merh = re.split(mer,text)
    
    for meros in merh:
        print(mer+meros[:100])
    print(len(merh))

if __name__ == '__main__':
    pdf = r'C:/Users/Aster/Downloads/FEK-2024-Tefxos A-00012-downloaded -09_05_2024.pdf'
    pdf= PDF_text(pdf)
    print(pdf.date)
    print(pdf.teyxos)
#    for page in range(pdf.len):
    
    meros(pdf)