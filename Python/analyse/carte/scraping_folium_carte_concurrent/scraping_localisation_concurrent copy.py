## (See <attachments> above for file contents. You may not need to search or read the file again.)
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


### Varonia ###






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



### SANDBOX ###

## (See <attachments> above for file contents. You may not need to search or read the file again.)
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
    print(data_sandbox)
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



### EVA ##


## Optimisation du code :
    ### paramètre chrome ###
options = Options()
options.headless = False
# Hide automation flags commonly used for bot detection
options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)

## Empêcher le chargement des images / CSS
prefs = {"profile.managed_default_content_settings.images": 2,
         "profile.managed_default_content_settings.stylesheets": 2,
         "profile.managed_default_content_settings.fonts": 2
         
        }
options.add_experimental_option('prefs',prefs)
options.add_argument("--disable-extensions")
options.add_argument("--disable-popup-blocking")
USER_AGENTS = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.187 Safari/537.36",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/116.0.1938.81 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
]
USER_AGENT = random.choice(USER_AGENTS)
options.add_argument(f"user-agent={USER_AGENT}")
print(f"Using User-Agent: {USER_AGENT}")


data_eva = {}

driver = webdriver.Chrome(options=options)
# Inject small script to hide navigator.webdriver and similar fingerprints
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': '''
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = window.chrome || {};
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
    '''
})
wait = WebDriverWait(driver,30)
driver.get("https://www.eva.gg/en-FR/locations")

button_click = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"div.gr-select.gr-select--size-md")))
button_click.click()
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"div.gr-select__dropdown")))
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")
select_countries = soup.select("div.gr-select__dropdown  div.gr-select-option" )
liste = [countrie.get('data-cy') for countrie in select_countries]
driver.quit()
driver = webdriver.Chrome(options=options)
# same CDP injection for the new driver instance
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': '''
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = window.chrome || {};
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
    '''
})
wait = WebDriverWait(driver,30)
accept_cookies = True
for i in liste :
    driver.get("about:blank")
    driver.get(f"https://www.eva.gg/en-{i}/locations")
    # try to remove any blocking cookie/privacy overlays right after load
    try:
        remove_onetrust_overlays(driver)
    except Exception:
        pass

    if accept_cookies:
        try:
            cookies_click = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.sc-gKseQn.gtafJz")))
            print("Bouton cookies affiché:", cookies_click.is_displayed(), "enabled:", cookies_click.is_enabled())
            # human-like move + pause then try normal click, fallback to JS
            try:
                ActionChains(driver).move_to_element(cookies_click).pause(random.uniform(0.2, 0.6)).click(cookies_click).perform()
            except Exception:
                time.sleep(random.uniform(0.2, 0.6))
                driver.execute_script("arguments[0].click();", cookies_click)
            accept_cookies = False
        except TimeoutException:
            pass
    try : 
            button_click = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button.Accordion_accordionControl__woFwO.LocationDetailAccordion_locationDetailAccordion__control__e37f4")))
    
    except TimeoutException : 
            pass 
    
   
  

    # 4. Récupérer tous les boutons d’accordéon et ne cliquer que si aria-expanded="false"
    buttons = driver.find_elements(By.CSS_SELECTOR, "button.Accordion_accordionControl__woFwO.LocationDetailAccordion_locationDetailAccordion__control__e37f4")
    for btn in buttons:
        # Si le bouton est déjà ouvert (aria-expanded="true"), on ne touche pas
        is_open = btn.get_attribute("aria-expanded") == "true"
        if not is_open:
            try:
                # Faire défiler jusqu’au bouton pour être sûr qu’il est dans le viewport
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                btn.click()
                # Petit délai pour que le panel se déploie
                
            except:
                pass

    # 5. À ce stade, tous les panneaux dont aria-expanded passait de "false" à "true" sont restés ouverts.
    #    On récupère le HTML final et on l’imprime.
    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"span.Text_text__BjKLk.Text_text--variant-body-sm__WheiX.Text_text--color-textContrast__vPFLP")))

   

    adresse = []
    liens = soup.select("span.Text_text__BjKLk.Text_text--variant-body-sm__WheiX.Text_text--color-textContrast__vPFLP")
    for lien in liens : 
        if lien : 
            adresse.append(lien.get_text())
        else :
            adresse.append("Pas d'adresse !")
    filtered = []
    for i in adresse:
        # On vérifie que i n'est pas l'un des trois mots à supprimer
        if i not in ('arenas', 'targets', 'POD area','arena','Accès par le parking Fitness Park','Bat E Porte 3 '):
            filtered.append(i)

    tel = []
    liens_tel = soup.select("a[href]")
    for lien in liens_tel :
        if lien :  
            tel.append(lien.get_text())
        else :
            tel.append('Pas de Télephone')
    tel_clean = []
    for i in tel:
        
        if i.startswith('0'):
            tel_clean.append(i)
        elif i.startswith('+'):
            tel_clean.append(i)
        elif i.startswith('Pas de Télephone'):
            tel_clean.append(i)
    for i,a in zip(filtered,tel_clean) : 
        data_eva[i] = [a]
        accept_cookies = False
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
# 3) S'ASSURER QUE CHAQUE VALEUR DANS 'data_eva' EST BIEN UNE LISTE
#    (data_eva existe déjà dans votre environnement)
# -------------------------------------------------------------------
for adresse, valeur in list(data_eva.items()):
    if not isinstance(valeur, list):
        data_eva[adresse] = [valeur]

# -------------------------------------------------------------------
# 4) BOUCLE DE GÉOCODAGE EN PRENANT LA CLÉ COMME ADRESSE
#    On parcourt chaque paire (adresse, liste_de_téléphones), on géocode la clé
#    et on append le résultat (tuple (lat, lon) ou message d'erreur) à la liste existante.
# -------------------------------------------------------------------
for adresse, telephone_list in data_eva.items():
    if adresse:
        logging.info(f"→ Géocodage pour '{adresse}'")
        coords = geocode_address(adresse)
        if coords:
            telephone_list.append(coords)
            logging.info(f"   (lat, lon) = {coords}")
        else:
            telephone_list.append("Adresse introuvable ou timeout")
            logging.warning("   → Adresse introuvable ou timeout")
    else:
        # Clé vide (pas d'adresse valide)
        telephone_list.append("Adresse vide")
        logging.warning(f"   → Pas d'adresse valide pour la clé : '{adresse}'")

    # Petite pause pour ne pas dépasser le quota Google
    time.sleep(0.2)

# -------------------------------------------------------------------
# 5) AFFICHER LES RÉSULTATS FINAUX
# -------------------------------------------------------------------
logging.info("\n=== Résultats finaux ===")
for adresse, infos in data_eva.items():
    # Le dernier élément de la liste est soit le tuple (lat, lon) soit un message d'erreur
    resultat = infos[-1]
    logging.info(f"{adresse} → {resultat}")
logging.info(f'data_eva: {data_eva}')



### VR cave ####

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
 
### VR anvio ###


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
    'data_varonia': data_varonia,
    'data_zerolatency': data_zerolatency,
    'data_eva': data_eva,
    'data_sandbox': data_sandbox,
    'data_vrcave': data_vrcave,
    'data_anvio': data_anvio,
}

# Exporter chacun vers un fichier JSON nommé <nom_du_dict>.json
for name, d in dicts_to_export.items():
    filename = f"{name}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    logging.info(f"✔️ Exporté {name} → {filename}")







