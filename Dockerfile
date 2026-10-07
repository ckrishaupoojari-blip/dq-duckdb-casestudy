FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
RUN mkdir -p data results
CMD ["sh", "-c", "python src/01_generate_data.py && python src/03_quality_checks.py"]
