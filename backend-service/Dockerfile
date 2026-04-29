FROM python:3.10

WORKDIR /code

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
	PIP_DEFAULT_TIMEOUT=180 \
	PIP_RETRIES=12

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
