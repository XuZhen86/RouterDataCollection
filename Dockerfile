FROM python:3.11.7

WORKDIR /app
ADD . /app
RUN pip3 install --use-pep517 .
