# Pipeline de données Varonia

Pipeline de traitement et d'analyse des données Varonia pour le Dashboard.

## 🎯 Objectif

Ce projet traite les données Varonia en 3 étapes :
1. **Préparation** : Nettoyage, géocodage, enrichissement (vacances, etc.)
2. **Analyse** : Génération d'insights et tendances  
3. **Export** : Préparation pour Supabase/Lovable

## 🚀 Utilisation rapide

### Configuration
`ash
# 1. Copier le fichier de configuration
copy .env.example .env

# 2. Éditer .env avec vos clés API
GOOGLE_API_KEY=votre_cle_google
GEONAMES_USER=jean_lec  
PREDICTHQ_TOKEN=votre_token_predicthq
`

### Lancement
`ash
# Pipeline complet
docker-compose up

# Script spécifique
docker-compose run varonia python Python/data_prep/script.py
`

## 📁 Structure

`
Projet_clean/
├── Data/                     # Données sources (.parquet)
├── Python/
│   ├── data_prep/           # Scripts de préparation
│   └── analyse/             # Scripts d'analyse
├── output/                  # Résultats temporaires
├── logs/                    # Logs du pipeline
├── Dockerfile               # Image de production
└── docker-compose.yml       # Configuration locale
`

## 🔧 Déploiement cloud

`ash
# Construire l'image
docker build -t varonia-pipeline .

# Lancer sur AWS/Azure
docker run varonia-pipeline python Python/data_prep/clean_data.py
docker run varonia-pipeline python Python/analyse/insights.py
`

## 📊 Pipeline de données

1. **data_prep/** : Nettoyage et enrichissement des données
2. **analyse/** : Génération d'insights et visualisations
3. **output/** : Données transformées prêtes pour Supabase

Environnement stable et reproductible grâce à Docker.
