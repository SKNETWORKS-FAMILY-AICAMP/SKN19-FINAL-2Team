FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy CSV dictionaries from project root
COPY accord_desc_dictionary.csv /app/accord_desc_dictionary.csv
COPY note_desc_dictionary.csv /app/note_desc_dictionary.csv

COPY backend/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]