from pdf_to_text import PDF_text

pdf_object=PDF_text()
text=pdf_object.read_text()


def vres_ipourgeia(text):
    ypourgeia=["ΑΓΡΟΤΙΚΉΣ ΑΝΆΠΤΥΞΗΣ ΚΑΙ ΤΡΟΦΊΜΩΝ","ΑΝΆΠΤΥΞΗΣ ΚΑΙ ΕΠΕΝΔΎΣΕΩΝ","ΔΙΚΑΙΟΣΎΝΗΣ","ΕΘΝΙΚΉΣ ΆΜΥΝΑΣ","ΕΞΩΤΕΡΙΚΏΝ","ΕΡΓΑΣΊΑΣ ΚΑΙ ΚΟΙΝΩΝΙΚΏΝ ΥΠΟΘΈΣΕΩΝ","ΕΣΩΤΕΡΙΚΏΝ",
    "ΜΕΤΑΝΆΣΤΕΥΣΗΣ ΚΑΙ ΑΣΎΛΟΥ","ΝΑΥΤΙΛΊΑΣ ΚΑΙ ΝΗΣΙΩΤΙΚΉΣ ΠΟΛΙΤΙΚΉΣ","ΟΙΚΟΝΟΜΙΚΏΝ","ΠΑΙΔΕΊΑΣ ΚΑΙ ΘΡΗΣΚΕΥΜΆΤΩΝ","ΠΕΡΙΒΆΛΛΟΝΤΟΣ ΚΑΙ ΕΝΈΡΓΕΙΑΣ","ΠΟΛΙΤΙΣΜΟΎ ΚΑΙ ΑΘΛΗΤΙΣΜΟΎ",
    "ΠΡΟΣΤΑΣΊΑΣ ΤΟΥ ΠΟΛΊΤΗ","ΤΟΥΡΙΣΜΟΎ","ΥΓΕΊΑΣ","ΥΠΟΔΟΜΏΝ ΚΑΙ ΜΕΤΑΦΟΡΏΝ","ΨΗΦΙΑΚΉΣ ΔΙΑΚΥΒΈΡΝΗΣΗΣ"]
    text=text.upper()
    #print(text)
    ypourgeia_found=[]
    for yp in ypourgeia:
        if (yp in text.upper()):
            ypourgeia_found.append(yp)
    return ",".join(ypourgeia_found)
def vres_apofasi(text):
    text=text.split("\n")
    apofasi=[]
    #find apofasi
    found_apofasi=False
    for i in range(2,len(text)):
        if("Έχοντας υπόψη"  in text[i]):
            found_apofasi=True
            break
        apofasi.append(text[i])
    #format apofasi
    if(found_apofasi):
        for i in range(len(apofasi)):
            if("Αριθμ." in apofasi[i] or "Αριθ" in apofasi[i]):
                break
        apofasi="".join(apofasi[i+1:])
        return apofasi
    else:
        return "NOTFOUND"
#print(vres_apofasi(text))

def vres_teyxos(text):
    text=text.split("\n")
    return text[-1:][0]


def produce_tweet(text):
    tweet=vres_apofasi(text)+"\n"+vres_ipourgeia(text)+"\n"+vres_teyxos(text)
    return tweet
print(produce_tweet(text))
