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
wait = WebDriverWait(driver, 15)
driver.get("https://www.virtual-games-park.fr/")

wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"div.flex.flex-col.space-y-1\\.5.p-6.pb-2.border-b.border-gray-800 h3")))  

driver.maximize_window()

button_xpath = "//button[normalize-space(text())='Toutes les salles']"
button_click = wait.until(EC.presence_of_element_located((By.XPATH, button_xpath)))

# Scroller et cliquer via JS (plus fiable que .click() direct)
driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_click)
time.sleep(0.5)  # petite pause
button_click.click()
data_varonia = {}

wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"div.p-6.py-4")))
html = driver.page_source
soup = BeautifulSoup(html, "lxml")

time.sleep(3)
parent = soup.find("div", class_  = ["rounded-lg", "text-card-foreground", "shadow-sm", "hover:shadow-lg", "transition-all", "bg-white/5", "dark:bg-black/40", "backdrop-blur-sm", "border", "border-white/10"]).select("div.flex.flex-col.space-y-1\\.5.p-6.pb-2.border-b.border-gray-800")
logging.info(f'Parent divs: {parent}')
for p in parent :
    
    salles = p.select_one('h3')
    data_varonia[salles.get_text()] = []

liste_temp = []

children = soup.find("div", class_  = ["rounded-lg", "text-card-foreground", "shadow-sm", "hover:shadow-lg", "transition-all", "bg-white/5", "dark:bg-black/40", "backdrop-blur-sm", "border", "border-white/10"]).select("div.p-6.py-4")
for child in children :
    
    salles = child.select_one('p')
    liste_temp.append(salles.get_text())

cles = list(data_varonia.keys())

for ville, nouvelle_val in zip(cles, liste_temp):
    data_varonia[ville] = [nouvelle_val]
driver.quit()


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
        # Si vous dépassez votre quota mensuel, vous recevrez cette exception
        print(f"Quota Google dépassé pour l'adresse : '{address}'")
        return None
    except GeocoderTimedOut:
        # Si Google met trop de temps à répondre
        print(f"Timeout lors du géocodage de : '{address}'")
        return None
    except Exception as e:
        # Toute autre erreur imprévue
        print(f"Erreur inattendue pour '{address}' : {e}")
        return None

# -------------------------------------------------------------------
# 3) BOUCLE DE GÉOCODAGE
#    On suppose que 'data_varonia' est votre dict où data_varonia[ville][3] == adresse brute
# -------------------------------------------------------------------
for ville, infos in data_varonia.items():
    # Vérifier que la liste infos a au moins 4 éléments
    if len(infos) > 0:
        adresse = infos[0]  # l'adresse brute extraite
        if adresse:
            logging.info(f"→ Géocodage pour '{ville}' : '{adresse}'")
            coords = geocode_address(adresse)
            if coords:
                data_varonia[ville].append(coords)
                logging.info(f"   (lat, lon) = {coords}")
            else:
                data_varonia[ville].append("Adresse introuvable ou timeout")
                logging.warning("   → Adresse introuvable ou timeout")
        else:
            data_varonia[ville].append("Adresse vide")
            logging.warning(f"   → Pas d'adresse pour '{ville}'")
    else:
        data_varonia[ville].append("Pas d'adresse disponible")
    logging.warning(f"   → La liste pour '{ville}' ne contient pas d'adresse")

    # Google tolère plus de requêtes par seconde que Nominatim,
    # mais on laisse un petit délai pour ne pas dépasser le quota.
    time.sleep(0.2)
logging.info(f'data_varonia: {data_varonia}')


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
        # Si vous dépassez votre quota mensuel, vous recevrez cette exception
        print(f"Quota Google dépassé pour l'adresse : '{address}'")
        return None
    except GeocoderTimedOut:
        # Si Google met trop de temps à répondre
        print(f"Timeout lors du géocodage de : '{address}'")
        return None
    except Exception as e:
        # Toute autre erreur imprévue
        print(f"Erreur inattendue pour '{address}' : {e}")
        return None

# -------------------------------------------------------------------
# 3) BOUCLE DE GÉOCODAGE
#    On suppose que 'data_varonia' est votre dict où data_varonia[ville][3] == adresse brute
# -------------------------------------------------------------------
for ville, infos in data_varonia.items():
    # Vérifier que la liste infos a au moins 4 éléments
    if len(infos) > 0:
        adresse = infos[0]  # l'adresse brute extraite
        if adresse:
            logging.info(f"→ Géocodage pour '{ville}' : '{adresse}'")
            coords = geocode_address(adresse)
            if coords:
                data_varonia[ville].append(coords)
                logging.info(f"   (lat, lon) = {coords}")
            else:
                data_varonia[ville].append("Adresse introuvable ou timeout")
                logging.warning("   → Adresse introuvable ou timeout")
        else:
            data_varonia[ville].append("Adresse vide")
            logging.warning(f"   → Pas d'adresse pour '{ville}'")
    else:
        data_varonia[ville].append("Pas d'adresse disponible")
    logging.warning(f"   → La liste pour '{ville}' ne contient pas d'adresse")

    # Google tolère plus de requêtes par seconde que Nominatim,
    # mais on laisse un petit délai pour ne pas dépasser le quota.
    time.sleep(0.2)
print(data_varonia)
# -------------------------------------------------------------------
# 4) AFFICHER LES RÉSULTATS
# -------------------------------------------------------------------
print("\n=== Résultats finaux ===")
for ville, infos in data_varonia.items():
    resultat = infos[-1]  # le tuple (lat, lon) ou le message d'erreur
    print(f"{ville} → {resultat}")


dicts_to_export = {
    'data_varonia': data_varonia
}

# Exporter chacun vers un fichier JSON nommé <nom_du_dict>.json
for name, d in dicts_to_export.items():
    filename = f"{name}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    logging.info(f"✔️ Exporté {name} → {filename}")


