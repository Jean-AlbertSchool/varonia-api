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

options = Options()
options.headless = True

## Empêcher le chargement des images / CSS 
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.stylesheets": 2,
    "profile.managed_default_content_settings.fonts": 2,
}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-extensions")
options.add_argument("--disable-popup-blocking")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")


data_sandbox_aucun_resultat = {}

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)
driver.get("https://sandboxvr.com/cerritos")



html = driver.page_source

soup = BeautifulSoup(html, "lxml")
try :
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'button#onetrust-accept-btn-handler'))).click()
    
except :
    logging.info("Le bouton pour accepter les cookies n'a pas été trouvé ou cliqué.")
try :
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'button.sc-fAUdSK.cMDAqw.MuiButtonBase-root.MuiButton-root.MuiButton-tonal.MuiButton-tonalSecondary.MuiButton-sizeSmall.MuiButton-tonalSizeSmall.MuiButton-colorSecondary.sc-ghWlax.fGfdIo.MuiButton-root.MuiButton-tonal.MuiButton-tonalSecondary.MuiButton-sizeSmall.MuiButton-tonalSizeSmall.MuiButton-colorSecondary.sc-dgjgUn.cDKCZl'))).click()
   

except TimeoutException:
    logging.info("Le bouton pour ouvrir le popup des salles n'a pas été trouvé ou cliqué.")
try : 
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'a.sc-diYFot.izWQIG.MuiTypography-root.MuiTypography-span.sc-gQkENW.gBSurk.MuiLink-root.MuiLink-underlineAlways.sc-gcfzXs.EJoyC.sc-kEsJEW.ggJbjZ')))
except TimeoutException:
    print("Le sélecteur pour les villes n'a pas été trouvé.")
soup = BeautifulSoup(driver.page_source, "lxml")
villes = soup.select('a.sc-diYFot.izWQIG.MuiTypography-root.MuiTypography-span.sc-gQkENW.gBSurk.MuiLink-root.MuiLink-underlineAlways.sc-gcfzXs.EJoyC.sc-kEsJEW.ggJbjZ')

liens = [ville.get("href") for ville in villes]
# use get_text to extract visible text; .get('text') returns an attribute named 'text' (usually None)
salles = [ville.get_text(strip=True) for ville in villes]
driver.quit()
data_sandbox = {}
print(salles)
print(liens)
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 8)
for i, lien in enumerate(liens) : 
    data_sandbox[salles[i]] = []
    
    driver.get("about:blank")
    driver.get(f"https://sandboxvr.com{lien}/location")
    if i == 0 :
        try :
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'button#onetrust-accept-btn-handler'))).click()
    
        except :
            logging.info("Le bouton pour accepter les cookies n'a pas été trouvé ou cliqué.")
    pass
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "a.sc-diYFot.jNmrny.MuiTypography-root.MuiTypography-span.sc-gQkENW.cFlKOr.MuiLink-root.MuiLink-underlineNone.sc-gcfzXs.gJPvhG")
            ))
    except TimeoutException:
        data_sandbox_aucun_resultat[salles[i]] = ["Pas d'information disponible !"]
        pass
    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")
    el = soup.select_one('a.sc-diYFot.jNmrny.MuiTypography-root.MuiTypography-span.sc-gQkENW.cFlKOr.MuiLink-root.MuiLink-underlineNone.sc-gcfzXs.gJPvhG')
    if el:
        adresse = el.get_text(strip=True)
        adresse = adresse.replace('\n', ' ').replace('\r', ' ').strip()
    else:
        adresse = None  # ou gérer l'absence
    
    
    data_sandbox[salles[i]].append(adresse)
    
    try:
        # Wait for the page body to ensure the page loaded; don't abort extraction on a selector-specific timeout.
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        logging.info(f"Timeout waiting for page body for {salles[i]} — will still attempt extraction via fallback strategies.")
    
    # refresh DOM/html because the phone block may have been added after earlier parse
    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    tel = None
    # Strategy A: look for a tel: link anywhere on the page
    try:
        tel_link = soup.select_one('a[href^="tel:"]')
    except Exception:
        tel_link = None

    if tel_link:
        tel = tel_link.get_text(strip=True) or tel_link.get('href').replace('tel:', '').strip()
        logging.debug(f"Found phone via tel: link for {salles[i]} -> {tel}")
    else:
        # Strategy B: try the known wrapper selectors (primary then fallback)
        el = soup.select_one('div.sc-cJjvBx.gnlIqj a.sc-diYFot.jNmrny.MuiTypography-root.MuiTypography-span.sc-gQkENW.cFlKOr.MuiLink-root.MuiLink-underlineNone.sc-gcfzXs.gJPvhG')
        if not el:
            el = soup.select_one('div.sc-StzaE.bLawtd a.sc-diYFot.jNmrny.MuiTypography-root.MuiTypography-span.sc-gQkENW.cFlKOr.MuiLink-root.MuiLink-underlineNone.sc-gcfzXs.gJPvhG')
        if el:
            tel = el.get_text(strip=True)
            logging.debug(f"Found phone via selector for {salles[i]} -> {tel}")
        else:
            # Strategy C: regex search in page text for a phone-like pattern
            page_text = soup.get_text(separator=' ', strip=True)
            m = re.search(r"(\+?\d[\d\s().-]{6,}\d)", page_text)
            if m:
                tel = m.group(1).strip()
                logging.debug(f"Found phone via regex for {salles[i]} -> {tel}")
            else:
                tel = None
                # debug: dump a small html fragment to help troubleshooting
                snippet = html[:2000]
                logging.debug(f"Phone element not found for {salles[i]} — tried tel:, selectors, regex; page snippet: {snippet}")
    data_sandbox[salles[i]].append(tel)
    
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
        print(f"Quota Google dépassé pour l'adresse : '{address}'")
        return None
    except GeocoderTimedOut:
        print(f"Timeout lors du géocodage de : '{address}'")
        return None
    except Exception as e:
        print(f"Erreur inattendue pour '{address}' : {e}")
        return None

# -------------------------------------------------------------------
# 3) BOUCLE DE GÉOCODAGE SUR data_sandbox
#    On suppose que data_sandbox[ville] == [<numéro>, <adresse>, …]
#    Si plusieurs paires existent (ex. "Atlanta_1": [tel, adresse]), on prend infos[1] comme adresse.
# -------------------------------------------------------------------
        
for ville, infos in data_sandbox.items() :
    # Dans data_sandbox nous ajoutons d'abord l'adresse puis le téléphone.
    # L'adresse se trouve donc en position 0 si elle existe.
    if len(infos) >= 1:
        adresse = infos[0]
        if adresse and adresse != "Pas d'information disponible !":
            print(f"→ Géocodage pour '{ville}' : '{adresse}'")
            coords = geocode_address(adresse)
            if coords:
                data_sandbox[ville].append(coords)
                print(f"   (lat, lon) = {coords}")
            else:
                data_sandbox[ville].append("Adresse introuvable ou timeout")
                print("   → Adresse introuvable ou timeout")
        else:
            data_sandbox[ville].append("Adresse vide")
            print(f"   → Pas d'adresse pour '{ville}'")
    else:
        # Si la liste n'a pas assez d'éléments pour contenir une adresse
        data_sandbox[ville].append("Pas d'adresse disponible")
        print(f"   → La liste pour '{ville}' ne contient pas d'adresse")

    # Petite pause pour éviter de dépasser le quota
    time.sleep(0.2)

# -------------------------------------------------------------------
# 4) AFFICHER LES RÉSULTATS
# -------------------------------------------------------------------
print("\n=== Résultats finaux ===")
for ville, infos in data_sandbox.items():
    # Le dernier élément ajouté est soit le tuple (lat, lon) soit un message d'erreur
    resultat = infos[-1]
    print(f"{ville} → {resultat}")
logging.info(f'data_sandbox: {data_sandbox}')

print(data_sandbox)

dicts_to_export = {
    
    'data_sandbox': data_sandbox
}

# Exporter chacun vers un fichier JSON nommé <nom_du_dict>.json
for name, d in dicts_to_export.items():
    filename = f"{name}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    logging.info(f"✔️ Exporté {name} → {filename}")


# Export simplifié vers assets/carte_data_scraping_concurrent
import os
os.makedirs("assets/carte_data_scraping_concurrent", exist_ok=True)
json.dump(data_sandbox, open("assets/carte_data_scraping_concurrent/data_sandbox.json", 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
logging.info(f"✔️ Exporté data_sandbox → assets/carte_data_scraping_concurrent/data_sandbox.json")



