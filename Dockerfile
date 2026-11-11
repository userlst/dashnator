# Dashnator (Streamlit). Para Render, Railway, Fly.io, Hugging Face Spaces (Docker) ou servidor próprio.
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dashnator ./dashnator
COPY niches ./niches
COPY .streamlit/config.toml ./.streamlit/config.toml
COPY streamlit_app.py .

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
