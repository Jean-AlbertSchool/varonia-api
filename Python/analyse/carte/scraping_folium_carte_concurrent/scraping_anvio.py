import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from selenium import webdriver
from selenium.webdriver import ActionChains
from bs4 import BeautifulSoup
import requests
import time
import random
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderQuotaExceeded
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re
import json 
import os

# Helper: hide common OneTrust / cookie overlays that intercept clicks
def remove_onetrust_overlays(driver):
    try:
        driver.execute_script("""
        // hide onetrust dark filter and panels
        var s = ['.onetrust-pc-dark-filter', '.onetrust-pc-sdk', '#onetrust-consent-sdk', '.onetrust-banner-sdk'];
        s.forEach(function(sel){
            var el = document.querySelector(sel);
            if(el){ el.style.pointerEvents='none'; el.style.display='none'; el.style.visibility='hidden'; }
        });
        // reduce any extremely large z-index containers
        var all = document.querySelectorAll('div');
        all.forEach(function(d){ try{ var z = window.getComputedStyle(d).zIndex; if(z && parseInt(z) > 1000000){ d.style.zIndex='0'; } }catch(e){} });
        """)
    except Exception:
        # fail silently — function is best-effort
        pass
options = Options()

driver = webdriver.Chrome()
Options.headless = True

## Empêcher le chargement des images / CSS 
prefs = {"profile.managed_default_content_settings.images":2,
         "profile.managed_default_content_settings.stylesheets" : 2,
         "profile.managed_default_content_settings.fonts" : 2 
         
        }
options.add_experimental_option('prefs',prefs)
options.add_argument("--disable-extensions")
options.add_argument("--disable-popup-blocking")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
wait = WebDriverWait(driver,6)
driver.get("https://anvio.com/#locations")

wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"div.col-lg-12.col-md-12.col-sm-14.col-xs-14.col-lg-offset-1.col-md-offset-1")))
salles_get_liens = driver.find_elements(By.CSS_SELECTOR,'div.col-lg-12.col-md-12.col-sm-14.col-xs-14.col-lg-offset-1.col-md-offset-1  a' )
salles_liens = [salle.get_attribute("href") for salle in salles_get_liens]
salle_txt = [salle.get_attribute("textContent")for salle in salles_get_liens]
data_anvio = {}
for salle in salle_txt :
    if "Coming soon" not in salle:
        data_anvio[salle] = []
driver.quit()



import time
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderQuotaExceeded

# -------------------------------------------------------------------
# 1) DÉCLARER VOTRE CLÉ API GOOGLE MAPS GEOCODING
# -------------------------------------------------------------------
API_KEY = "AIzaSyB--QHyl2kD0vmzwOUgx-rzuMQJ2GUFQDY"  # Remplacez par votre clé réelle

# -------------------------------------------------------------------
# 2) INITIALISER LE GÉOLOCALISATEUR GOOGLE
# -------------------------------------------------------------------
geolocator = GoogleV3(api_key=API_KEY, timeout=10)

def geocode_address(address):
    """
    Tente de géocoder 'address' via GoogleV3.
    Renvoie (latitude, longitude) ou None si échec / timeout / quota dépassé.
    """
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        return None
    except GeocoderQuotaExceeded:
        print(f"Quota Google dépassé pour l'adresse : '{address}'")
        return None
    except GeocoderTimedOut:
        print(f"Timeout lors du géocodage de : '{address}'")
        return None
    except Exception as e:
        print(f"Erreur inattendue pour '{address}' : {e}")
        return None

# -------------------------------------------------------------------
# 3) S'ASSURER QUE CHAQUE VALEUR DANS 'data_anvio' EST BIEN UNE LISTE
#    (Si certaines valeurs ne sont pas des listes, on les transforme)
# -------------------------------------------------------------------
for ville, valeur in list(data_anvio.items()):
    if not isinstance(valeur, list):
        data_anvio[ville] = [valeur]

# -------------------------------------------------------------------
# 4) BOUCLE DE GÉOCODAGE : pour chaque ville (clé), on ajoute (lat, lon)
#    ou un message d'erreur à la liste associée
# -------------------------------------------------------------------
for ville, infos in data_anvio.items():
    if ville:
        logging.info(f"→ Géocodage pour '{ville}'")
        coords = geocode_address(ville)
        if coords:
            infos.append(coords)
            logging.info(f"   (lat, lon) = {coords}")
        else:
            infos.append("Adresse introuvable ou timeout")
            logging.warning("   → Adresse introuvable ou timeout")
    else:
        infos.append("Ville vide")
        logging.warning(f"   → Clé vide pour data_anvio")

    # Petite pause pour ne pas dépasser le quota Google
    time.sleep(0.2)

# -------------------------------------------------------------------
# 5) AFFICHER LES RÉSULTATS FINAUX
# -------------------------------------------------------------------
logging.info("\n=== Résultats finaux pour data_anvio ===")
for ville, infos in data_anvio.items():
    # Le dernier élément de la liste est soit le tuple (lat, lon) soit un message d'erreur
    resultat = infos[-1]
    logging.info(f"{ville} → {resultat}")
logging.info(f'data_anvio: {data_anvio}')

dicts_to_export = {
    
    'data_anvio': data_anvio,
}

# Exporter chacun vers un fichier JSON nommé <nom_du_dict>.json
for name, d in dicts_to_export.items():
    filename = f"{name}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    logging.info(f"✔️ Exporté {name} → {filename}")






