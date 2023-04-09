from pdf_to_text import PDF_text

pdf_object=PDF_text()
text=pdf_object.read_text()
ypourgeia=["ΑΓΡΟΤΙΚΉΣ ΑΝΆΠΤΥΞΗΣ ΚΑΙ ΤΡΟΦΊΜΩΝ",
"ΑΝΆΠΤΥΞΗΣ ΚΑΙ ΕΠΕΝΔΎΣΕΩΝ",
"ΔΙΚΑΙΟΣΎΝΗΣ",
"ΕΘΝΙΚΉΣ ΆΜΥΝΑΣ",
"ΕΞΩΤΕΡΙΚΏΝ",
"ΕΡΓΑΣΊΑΣ ΚΑΙ ΚΟΙΝΩΝΙΚΏΝ ΥΠΟΘΈΣΕΩΝ",
"ΕΣΩΤΕΡΙΚΏΝ",
"ΜΕΤΑΝΆΣΤΕΥΣΗΣ ΚΑΙ ΑΣΎΛΟΥ",
"ΝΑΥΤΙΛΊΑΣ ΚΑΙ ΝΗΣΙΩΤΙΚΉΣ ΠΟΛΙΤΙΚΉΣ",
"ΟΙΚΟΝΟΜΙΚΏΝ",
"ΠΑΙΔΕΊΑΣ ΚΑΙ ΘΡΗΣΚΕΥΜΆΤΩΝ",
"ΠΕΡΙΒΆΛΛΟΝΤΟΣ ΚΑΙ ΕΝΈΡΓΕΙΑΣ",
"ΠΟΛΙΤΙΣΜΟΎ ΚΑΙ ΑΘΛΗΤΙΣΜΟΎ",
"ΠΡΟΣΤΑΣΊΑΣ ΤΟΥ ΠΟΛΊΤΗ",
"ΤΟΥΡΙΣΜΟΎ",
"ΥΓΕΊΑΣ",
"ΥΠΟΔΟΜΏΝ ΚΑΙ ΜΕΤΑΦΟΡΏΝ",
"ΨΗΦΙΑΚΉΣ ΔΙΑΚΥΒΈΡΝΗΣΗΣ"]

def vres_ipourgeia(text):
    text=text.upper()
    #print(text)
    ypourgeia_found=[]
    for yp in ypourgeia:
        if (yp in text.upper()):
            ypourgeia_found.append(yp)
    return ypourgeia_found
#vres_ipourgeia(text)


def apofasi(text):
    text=text.split("\n")
    apofasi=[]
    #find apofasi
    for i in range(2,len(text)):
        if("Έχοντας υπόψη"  in text[i]):
            break
        apofasi.append(text[i])
    #format apofasi
    apofasi="".join(apofasi)
    #apofasi=apofasi.split(".")
    print(apofasi)


apofasi(text)
