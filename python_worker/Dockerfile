FROM python:3.9-slim
WORKDIR /app
COPY main.py .
RUN pip install fastapi uvicorn
CMD ["python", "main.py"]