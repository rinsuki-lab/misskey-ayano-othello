FROM python:3.6

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY ./othello ./othello

CMD ["python", "/app/othello/main.py"]