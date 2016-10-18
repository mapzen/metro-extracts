FROM rcarmo/alpine-python:3.5
RUN apk add --update postgresql-dev

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY App ./
COPY docs ./
COPY cities.json ./
COPY create.pgsql ./
COPY run-debug.py ./
COPY test.py ./

CMD gunicorn -b 0.0.0.0:80 --workers 2 App.web:app
