# ETAPES DE PREPARATION DOCKER - DETAILS COMPLETS

## OUVERTURE VS CODE
`ash
cd "g:\Varonia\Projet_clean"
code .
code "reminders\DOCKER_CHECKLIST_AVANT_LANCEMENT.md"
code "reminders\FICHIERS_A_MODIFIER_DETAILS.md"
`

## IMPORTANT : AVANT DE COMMENCER
- OUVRIR VS CODE : Executer les commandes ci-dessus dans le terminal
- Creer le fichier .env avec toutes les variables d'environnement
- Sauvegarder vos fichiers actuels avant modifications

## 1. CREER LE FICHIER .env (RACINE DU PROJET)
`env
GOOGLE_MAPS_API_KEY=votre_cle_api_google_maps_ici
GEONAMES_USERNAME=votre_username_geonames_ici
ENVIRONMENT=production
`

## 2. CORRECTIONS DE CHEMINS DE LOGS (2 FICHIERS)

### A. Python/data_prep/data_prep.py
LIGNES A MODIFIER : 8-9
PROBLEME : Logs crees dans le dossier local au lieu de /app/logs/

ACTUEL :
`python
log_filename = f"logs/data_prep_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
`

REMPLACER PAR :
`python
log_filename = f"/app/logs/data_prep_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
`

### B. Python/data_prep_temp.py
LIGNES A MODIFIER : 8-9
PROBLEME : Meme probleme que ci-dessus
SOLUTION : Appliquer la meme correction

## 3. SECURISER LES CLES API (4+ FICHIERS)

### A. Python/cartes_scraping_a2/main.py
PROBLEME : Cle API hardcodee
AJOUTER EN HAUT :
`python
import os
`
MODIFIER :
`python
# REMPLACER : API_KEY = "votre_cle_ici"
# PAR :
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
`

### B. Python/cartes_scraping_a2/scraper_final.py
PROBLEME : Cle API hardcodee (ligne contenant API_KEY = "AIza...")
AJOUTER EN HAUT :
`python
import os
`
MODIFIER :
`python
# REMPLACER la ligne avec AIza...
# PAR :
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
`

### C. Python/cartes_scraping_a2/test.py
PROBLEME : Cle API hardcodee
SOLUTION : Meme correction que ci-dessus

### D. Python/cartes_scraping_bio/main.py
PROBLEME : Cle API hardcodee
SOLUTION : Meme correction que ci-dessus

## 4. CORRIGER LES CHEMINS D'EXPORT JSON (6+ FICHIERS)

### A. Python/cartes_scraping_a2/main.py
PROBLEME : Export vers chemin local
CHERCHER : "assets/carte_data_scraping_concurrent/a2_locations.json"
REMPLACER PAR : "/app/assets/carte_data_scraping_concurrent/a2_locations.json"

### B. Python/cartes_scraping_a2/scraper_final.py
PROBLEME : Export vers chemin local
CHERCHER : "assets/carte_data_scraping_concurrent/a2_locations_final.json"
REMPLACER PAR : "/app/assets/carte_data_scraping_concurrent/a2_locations_final.json"

### C. Python/cartes_scraping_bio/main.py
PROBLEME : Export vers chemin local
CHERCHER : "assets/carte_data_scraping_concurrent/bio_locations.json"
REMPLACER PAR : "/app/assets/carte_data_scraping_concurrent/bio_locations.json"

### D. Autres fichiers de scraping a verifier :
- Python/cartes_scraping_a2/*.py - Tous les fichiers avec .json
- Python/cartes_scraping_bio/*.py - Tous les fichiers avec .json
- Python/analyse/carte/scraping_folium_carte_concurrent/*.py

REGLE GENERALE : Tous les chemins commencant par assets/ doivent devenir /app/assets/

## 5. VARIABLES D'ENVIRONNEMENT A VERIFIER

### GEONAMES_USERNAME
FICHIERS CONCERNES : Fichiers utilisant l'API GeoNames
VERIFIER LA PRESENCE DE :
`python
username = os.getenv('GEONAMES_USERNAME')
`

### Autres variables potentielles :
- Verifier tous les os.getenv() existants
- S'assurer que toutes les variables sont dans le fichier .env

## 6. VERIFICATION FINALE - CHECKLIST

### Fichiers de logs :
- [ ] Python/data_prep/data_prep.py - lignes 8-9 modifiees
- [ ] Python/data_prep_temp.py - lignes 8-9 modifiees

### Securisation API :
- [ ] Python/cartes_scraping_a2/main.py - import os + os.getenv
- [ ] Python/cartes_scraping_a2/scraper_final.py - import os + os.getenv
- [ ] Python/cartes_scraping_a2/test.py - import os + os.getenv
- [ ] Python/cartes_scraping_bio/main.py - import os + os.getenv

### Chemins JSON :
- [ ] Tous les chemins assets/ remplaces par /app/assets/
- [ ] Verification manuelle de tous les fichiers .py pour exports

### Configuration :
- [ ] Fichier .env cree a la racine
- [ ] Variables GOOGLE_MAPS_API_KEY et GEONAMES_USERNAME definies
- [ ] Test local avant Docker

## 7. COMMANDES DE TEST AVANT DOCKER

`ash
# Test de configuration
python -c "import os; print('API Key:', 'OK' if os.getenv('GOOGLE_MAPS_API_KEY') else 'MANQUANT')"
python -c "import os; print('GeoNames:', 'OK' if os.getenv('GEONAMES_USERNAME') else 'MANQUANT')"
`

## UNE FOIS TOUT CA FAIT, VOTRE PROJET SERA PRET POUR DOCKER !

### Commandes Docker finales :
`ash
docker build -t varonia-pipeline .
docker run -d --name varonia-container -v varonia_logs:/app/logs -v varonia_output:/app/output varonia-pipeline
`

---
NOTE : Cette analyse a ete faite sur 32 fichiers Python. Verifiez manuellement les autres fichiers si necessaire.
