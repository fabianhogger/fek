FROM python:3.8.10-slim

WORKDIR /FEK

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python","Fek_getter.py"]