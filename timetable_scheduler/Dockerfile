FROM python:3.10-slim

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=12

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . /app

EXPOSE 8501

CMD ["sh", "-c", "python -c 'from db.init_db import init_database; init_database()' && streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true"]