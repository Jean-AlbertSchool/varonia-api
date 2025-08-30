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
                time.sleep(2)
            except:
                pass

        

           
        # Récupérer le HTML complet après avoir ouvert les boutons
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Parcourir les sections ouvertes et extraire les données avec BeautifulSoup
        sections = soup.select("div.Accordion_accordionItem__yHniH")
        for section in sections:
            # Vérifier si la section est ouverte
            is_open = section.select_one("button[aria-expanded='true']")
            if is_open:
                # Récupérer le nom de la ville
                city_element = section.select_one("h2.Heading_heading__sAiRe")
                city_name = city_element.text.strip() if city_element else "Ville inconnue"

                # Récupérer l'adresse
                address_element = section.select_one("span.Text_text__BjKLk.Text_text--variant-body-sm__WheiX.Text_text--color-textContrast__vPFLP")
                address = address_element.text.strip() if address_element else "Adresse inconnue"

                # Récupérer le téléphone
                phone_element = section.select_one("a[href^='tel']")
                phone = phone_element.text.strip() if phone_element else "Pas de téléphone"

                # Ajouter les données dans le dictionnaire
                data_eva[city_name] = [address, phone]

                # Afficher les données extraites pour chaque section ouverte
                print(f"Ville : {city_name}, Adresse : {address}, Téléphone : {phone}")

        # Afficher le dictionnaire final
        print(data_eva)

# Compter les entrées valides dans data_eva
valid_entries = {k: v for k, v in data_eva.items() if v[0] != "Adresse inconnue" and v[1] != "Pas de téléphone"}
print(f"Nombre d'entrées valides (avec adresse et téléphone) : {len(valid_entries)}")


# 1) DÉCLARER VOTRE CLÉ API GOOGLE MAPS GEOCODING
# -------------------------------------------------------------------
API_KEY = "AIzaSyB--QHyl2kD0vmzwOUgx-rzuMQJ2GUFQDY"  # Remplacez par votre clé réelle

# -------------------------------------------------------------------
# 2) INITIALISER LE GÉOLOCALISATEUR GOOGLE
# -------------------------------------------------------------------
geolocator = GoogleV3(api_key=API_KEY, timeout=15)  # Timeout augmenté à 15 secondes

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
# 4) BOUCLE DE GÉOCODAGE EN PRENANT L'ADRESSE COMME ENTRÉE
# -------------------------------------------------------------------
for ville, infos in data_eva.items():
    if len(infos) >= 1:  # Vérifie si l'adresse est présente
        adresse = infos[0]  # Utilise l'adresse pour le géocodage
        logging.info(f"→ Géocodage pour l'adresse : '{adresse}'")
        coords = geocode_address(adresse)
        if coords:
            infos.append(coords)  # Ajoute les coordonnées à la liste
            logging.info(f"   (lat, lon) = {coords}")
        else:
            infos.append("Adresse introuvable ou timeout")
            logging.warning("   → Adresse introuvable ou timeout")
    else:
        infos.append("Adresse vide")
        logging.warning(f"   → Pas d'adresse valide pour la ville : '{ville}'")

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

dicts_to_export = {

    'data_eva': data_eva
}

# Exporter chacun vers un fichier JSON nommé <nom_du_dict>.json
for name, d in dicts_to_export.items():
    filename = f"{name}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    logging.info(f"✔️ Exporté {name} → {filename}")
