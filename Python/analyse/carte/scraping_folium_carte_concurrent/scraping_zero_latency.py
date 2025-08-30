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


####ZERO LATENCY####
driver = webdriver.Chrome(options=options)
driver.get("https://zerolatencyvr.com/en/locations")
wait = WebDriverWait(driver,15)
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"div[data-descripton='SEO List Venue Context Hard links']")))
html = driver.page_source
soup = BeautifulSoup(html, "lxml")

links = soup.select('div[data-descripton = "SEO List Venue Context Hard links"] a')
villes = [a.get('href')for a in links]
villes = [url.replace('/en/', '/en/locations/') for url in villes]
logging.info(f'URLs modifiées : {villes}')
driver.quit()
data = {}
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)
logging.info(f'Liste des villes à scraper : {villes}')
for i in villes :
    

    data[i] = []

    driver.get("about:blank")
    driver.get(i)
    
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "h1.MuiTypography-root.MuiTypography-h1.css-312tlf-MuiTypography-root")
            ))
    except TimeoutException:
        data[i] = ["Pas d'information disponible !"]
        continue
    
    
    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")
    # Numéro Téléphone
    lien_tel = soup.select_one("a[href^='tel:']")
    if lien_tel:
        numero_href = lien_tel.get("href")
    else:
        numero_href = "Pas de numéro spécifié" 
    data[i].append(numero_href)
    
    # Email
    
    email = soup.select_one("a[href^='mailto:']")
   
    if email:
        ad_email = email.get("href")
        ad_email = ad_email.replace('mailto:','')
    else:
        ad_email = "Pas d'adresse mail spécifié" 

    data[i].append(ad_email)
    

    #WEBSITE
    website = soup.select_one("a.MuiTypography-root.MuiTypography-link1.css-1i9wcz-MuiTypography-root[href^=\"http\"]")
   
    if website : 
        site = website.get("href")
        
    else:
        site = "Pas de site spécifié" 

    data[i].append(site)
  
    # Adresse

    adress = soup.select_one('p.MuiTypography-root.MuiTypography-body1.css-z643mw-MuiTypography-root')
    if adress:
        adresse = adress.get_text(separator="\n", strip=True)
        adresse = adresse.replace('\n',' ')
        data[i].append(adresse)
    else : 
        adresse = "Pas d'adresse spécifié"
        data[i].append(adresse)
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
#    On suppose que 'data' est votre dict où data[ville][3] == adresse brute
# -------------------------------------------------------------------
for ville, infos in data.items():
    # Vérifier que la liste infos a au moins 4 éléments
    if len(infos) > 3:
        adresse = infos[3]  # l'adresse brute extraite
        if adresse:
            logging.info(f"→ Géocodage pour '{ville}' : '{adresse}'")
            coords = geocode_address(adresse)
            if coords:
                data[ville].append(coords)
                logging.info(f"   (lat, lon) = {coords}")
            else:
                data[ville].append("Adresse introuvable ou timeout")
                logging.warning("   → Adresse introuvable ou timeout")
        else:
            data[ville].append("Adresse vide")
            logging.warning(f"   → Pas d'adresse pour '{ville}'")
    else:
        data[ville].append("Pas d'adresse disponible")
    logging.warning(f"   → La liste pour '{ville}' ne contient pas d'adresse")

    # Google tolère plus de requêtes par seconde que Nominatim,
    # mais on laisse un petit délai pour ne pas dépasser le quota.
    time.sleep(0.2)

# -------------------------------------------------------------------
# 4) AFFICHER LES RÉSULTATS
# -------------------------------------------------------------------
logging.info("\n=== Résultats finaux ===")
for ville, infos in data.items():
    resultat = infos[-1]  # le tuple (lat, lon) ou le message d'erreur
    logging.info(f"{ville} → {resultat}")

data_zerolatency = data
logging.info(f'data_zerolatency: {data_zerolatency}')

dicts_to_export = {
    
    'data_zerolatency': data_zerolatency
}

# Exporter chacun vers un fichier JSON nommé <nom_du_dict>.json
for name, d in dicts_to_export.items():
    filename = f"{name}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    logging.info(f"✔️ Exporté {name} → {filename}")


