FROM dacshpi/deepac:0.13.5

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install deepaclive==0.3.2 --no-deps

WORKDIR /deepac

ENV PYTHONUNBUFFERED 1

CMD ["deepac-live"]

