FROM python:3.11
COPY . .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
CMD exec gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker  --threads 8 app:app

