ARG PYTHON_VERSION
FROM python:$PYTHON_VERSION-alpine

RUN apk add bash
RUN pip install tox

WORKDIR /src
