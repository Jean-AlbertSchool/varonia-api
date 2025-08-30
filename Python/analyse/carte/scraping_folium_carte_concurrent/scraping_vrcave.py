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

## Optimisation du code :
    ### paramètre chrome ###
options = Options()
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


driver = webdriver.Chrome(options=options)
driver.maximize_window()
wait = WebDriverWait(driver, 5)

# -------------------- DÉMARRAGE --------------------
driver.get("https://www.google.com/maps/d/viewer?mid=196faVQzDC4n9NalqODJg0GKwbjuLgFzi&femb=1&ll=0.3997073559223759%2C137.695198897382&z=2")

menu_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.HzV7m-pbTTYe-KoToPc-ornU0b")))
menu_btn.click()

data_vrcave = {}
data_vide = {}

# -------------------- RÉCUPÉRER TOUTES LES SALLES --------------------
salles_lien = driver.find_elements(By.CSS_SELECTOR, "div.HzV7m-pbTTYe-JNdkSc-PntVL div.suEOdc")
salles = list(set(salle.get_attribute("aria-label") for salle in salles_lien))

# -------------------- TRAITEMENT DE CHAQUE SALLE --------------------
for salle in salles:
    data_vrcave[salle] = []
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.HzV7m-pbTTYe-JNdkSc-PntVL")))
        bouton = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'div[aria-label*="{salle}"]')))
        driver.execute_script("arguments[0].click();", bouton)
        time.sleep(0.5)
    except Exception as e:
        logging.error(f"❌ Erreur lors du clic sur la salle '{salle}' → {e}")
        data_vrcave[salle].append("Erreur au clic")
        continue

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.fO2voc-jRmmHf-MZArnb-Q7Zjwb")))

        adresses = [e.text for e in driver.find_elements(By.CSS_SELECTOR, "div.fO2voc-jRmmHf-MZArnb-Q7Zjwb")]
        tels = [e.text for e in driver.find_elements(By.CSS_SELECTOR, "div.fO2voc-jRmmHf-MZArnb-Q7Zjwb + div")]
        sites = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "div.qqvbed-VTkLkc.fO2voc-jRmmHf-LJTIlf div a[href]")]

        data_vrcave[salle].append(adresses if adresses else "Aucune adresse disponible.")
        data_vrcave[salle].append(tels if tels else "Pas de tel disponible.")
        data_vrcave[salle].append(sites[0] if sites else "Aucun site disponible.")

    except TimeoutException:
        data_vide.setdefault(salle, []).append("Timeout lors du chargement des infos")

    try:
        bouton_fermeture = driver.find_element(By.CSS_SELECTOR,
            'div.U26fgb.mUbCce.p9Nwte.HzV7m-tJHJj-LgbsSe.qqvbed-a4fUwd-LgbsSe.M9Bg4d')
        driver.execute_script("arguments[0].click();", bouton_fermeture)
        time.sleep(0.5)
    except:
        pass

# -------------------- GÉOCODAGE --------------------
API_KEY = "AIzaSyB--QHyl2kD0vmzwOUgx-rzuMQJ2GUFQDY"
geolocator = GoogleV3(api_key=API_KEY, timeout=10)

def geocode_address(address):
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        return None
    except GeocoderQuotaExceeded:
        logging.warning(f"Quota dépassé pour : {address}")
        return None
    except GeocoderTimedOut:
        logging.warning(f"Timeout pour : {address}")
        return None
    except Exception as e:
        logging.error(f"Erreur avec '{address}' : {e}")
        return None

for nom_salle, valeurs in data_vrcave.items():
    adresse = None
    if valeurs and isinstance(valeurs[0], list) and valeurs[0]:
        adresse = valeurs[0][0]

    if adresse:
        logging.info(f"→ Géocodage : {adresse}")
        coords = geocode_address(adresse)
        if coords:
            valeurs.append(coords)
            logging.info(f"   ✅ Coordonnées : {coords}")
        else:
            valeurs.append("Adresse introuvable ou timeout")
            logging.warning("   ❌ Adresse introuvable")
    else:
        valeurs.append("Adresse vide ou format invalide")
    logging.warning(f"   ⚠️ Adresse vide pour {nom_salle}")

    time.sleep(0.2)

# -------------------- RÉSUMÉ --------------------
logging.info("\n=== Résultat final ===")
for nom, infos in data_vrcave.items():
    logging.info(f"{nom} → {infos[-1]}")

logging.info(f"\nNombre de salles traitées : {len(salles)}")
logging.info(f"Nombre de clés dans data_vrcave : {len(data_vrcave)}")
logging.info(f'data_vrcave: {data_vrcave}')
dicts_to_export = {
  
    'data_vrcave': data_vrcave
    
}

# Exporter chacun vers un fichier JSON nommé <nom_du_dict>.json
for name, d in dicts_to_export.items():
    filename = f"{name}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    logging.info(f"✔️ Exporté {name} → {filename}")






