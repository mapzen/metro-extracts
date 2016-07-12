FROM python:3.3

COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt

CMD honcho start

