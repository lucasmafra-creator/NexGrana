FROM python:3.12-slim
WORKDIR /app
COPY gateway/requirements.txt /app/gateway/requirements.txt
RUN pip install --no-cache-dir -r /app/gateway/requirements.txt
COPY gateway /app/gateway
RUN useradd --create-home --uid 10001 nex
USER nex
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]
