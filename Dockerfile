# Build command:
# docker build -t blk-hacking-ind-abhijit-dutta .

FROM python:3.14-slim-bookworm

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5477

CMD ["python", "app.py"]