# Pipeline de données Varonia - Image de production
FROM python:3.11-slim

# Répertoire de travail
WORKDIR /app

# Dépendances système pour compilation
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Installation des packages Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de tout le code du pipeline
COPY Python/ ./Python/
COPY Data/ ./Data/

# Dossiers pour les résultats
RUN mkdir -p /app/logs /app/output

# Variables d'environnement pour le pipeline
ENV PYTHONPATH=/app
ENV VARONIA_ENV=production

# Point d'entrée flexible pour différents scripts
# Usage: docker run varonia-pipeline python Python/data_prep/script.py
CMD ["python", "Python/data_prep/data_prep.py"]
