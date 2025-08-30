# CHECKLIST DOCKER - AVANT LANCEMENT

## OUVERTURE VS CODE
`ash
cd "g:\Varonia\Projet_clean"
code .
code "reminders\FICHIERS_A_MODIFIER_DETAILS.md"
`

## CHECKLIST COMPLETE

### 1. CREER LE FICHIER .env
`ash
GOOGLE_MAPS_API_KEY=votre_cle_api_google_maps
GEONAMES_USERNAME=votre_username_geonames
`

### 2. FICHIERS AVEC CHEMINS DE LOGS A CORRIGER (2 fichiers)
- [ ] Python/data_prep/data_prep.py - ligne 8-9
- [ ] Python/data_prep_temp.py - ligne 8-9
Remplacer: logs/ par: /app/logs/

### 3. FICHIERS AVEC CLES API A SECURISER (4+ fichiers)
- [ ] Python/cartes_scraping_a2/main.py
- [ ] Python/cartes_scraping_a2/scraper_final.py
- [ ] Python/cartes_scraping_a2/test.py
- [ ] Python/cartes_scraping_bio/main.py
Remplacer: API_KEY = "AIza..." par: API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

### 4. FICHIERS AVEC CHEMINS JSON A CORRIGER (6+ fichiers)
- [ ] Python/cartes_scraping_a2/main.py
- [ ] Python/cartes_scraping_a2/scraper_final.py
- [ ] Python/cartes_scraping_bio/main.py
- [ ] Et tous les autres fichiers de scraping...
Remplacer: assets/ par: /app/assets/

### 5. AJOUTER IMPORTS MANQUANTS
- [ ] Ajouter import os dans tous les fichiers utilisant os.getenv()

### 6. TESTER LA CONFIGURATION
- [ ] Verifier que tous les chemins sont corrects
- [ ] Verifier que toutes les variables d'environnement sont definies
- [ ] Tester une execution locale avant Docker

## COMMANDES DOCKER FINALES
`ash
docker build -t varonia-pipeline .
docker run -d --name varonia-container -v varonia_logs:/app/logs -v varonia_output:/app/output varonia-pipeline
`

## UNE FOIS TOUT VALIDE
Votre pipeline de donnees sera pret pour le deploiement cloud !
