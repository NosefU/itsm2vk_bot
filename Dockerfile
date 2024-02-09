FROM python:3.9-slim

RUN mkdir /app

COPY requirements.txt /app/

RUN python -m pip install -r /app/requirements.txt

COPY src/ /app

WORKDIR /app

ENTRYPOINT ["python", "main.py"]