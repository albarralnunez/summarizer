FROM continuumio/miniconda3:latest

WORKDIR /app

COPY environment.yml /app/environment.yml

# Create the conda environment
RUN conda env create -f environment.yml && \
    echo "conda activate summarizer" >> ~/.bashrc

# Make RUN commands use the new environment
SHELL ["/bin/bash", "--login", "-c"]

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

COPY src /app/src

RUN python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "src.main:app", "-b", "0.0.0.0:8888"]
