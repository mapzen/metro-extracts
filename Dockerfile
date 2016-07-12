FROM python:3.3
COPY . .

WORKDIR .

RUN pip3 install -r requirements.txt

CMD honcho start

