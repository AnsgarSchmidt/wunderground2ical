FROM python:latest

RUN pip install icalendar requests Flask oauth2client google-api-python-client

ADD Exporter.py      Exporter.py
ADD credentials.json credentials.json
ADD token.json       token.json

EXPOSE 80

CMD python /Exporter.py
