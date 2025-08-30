from selenium import webdriver
from bs4 import BeautifulSoup
import time
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderQuotaExceeded
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------------ CONFIGURATION SELENIUM ------------------------
options = Options()
Options.headless = True

prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.stylesheets": 2,
    "profile.managed_default_content_settings.fonts": 2
}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-extensions")
options.add_argument("--disable-popup-blocking")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)
driver.get("https://www.virtual-games-park.fr/")

wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.flex.flex-col.space-y-1\\.5.p-6.pb-2.border-b.border-gray-800 h3")))
driver.maximize_window()

# Cliquer sur le bouton 'Toutes les salles'
button_xpath = "//button[normalize-space(text())='Toutes les salles']"
button_click = wait.until(EC.presence_of_element_located((By.XPATH, button_xpath)))
driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_click)
time.sleep(0.5)
button_click.click()

# ------------------------ EXTRACTION AVEC BEAUTIFULSOUP ------------------------
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.p-6.py-4")))
html = driver.page_source
soup = BeautifulSoup(html, "lxml")
time.sleep(3)

data_varonia = {}

parent = soup.find("div", class_=[
    "rounded-lg", "text-card-foreground", "shadow-sm", "hover:shadow-lg", "transition-all",
    "bg-white/5", "dark:bg-black/40", "backdrop-blur-sm", "border", "border-white/10"
]).select("div.flex.flex-col.space-y-1\\.5.p-6.pb-2.border-b.border-gray-800")

for p in parent:
    salle = p.select_one('h3')
    data_varonia[salle.get_text()] = []

liste_temp = []
children = soup.find("div", class_=[
    "rounded-lg", "text-card-foreground", "shadow-sm", "hover:shadow-lg", "transition-all",
    "bg-white/5", "dark:bg-black/40", "backdrop-blur-sm", "border", "border-white/10"
]).select("div.p-6.py-4")

for child in children:
    adresse = child.select_one('p')
    liste_temp.append(adresse.get_text())

for ville, adresse in zip(data_varonia.keys(), liste_temp):
    data_varonia[ville] = [adresse]

driver.quit()

# ------------------------ GÉOCODAGE GOOGLE ------------------------
API_KEY = "AIzaSyB--QHyl2kD0vmzwOUgx-rzuMQJ2GUFQDY"
geolocator = GoogleV3(api_key=API_KEY, timeout=10)

def geocode_address(address):
    try:
        location = geolocator.geocode(address)
        if location:
            country = None
            for comp in location.raw.get('address_components', []):
                if 'country' in comp.get('types', []):
                    country = comp.get('long_name')
                    break
            return (location.latitude, location.longitude, country)
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

# ------------------------ BOUCLE DE GÉOCODAGE ------------------------
for ville, infos in data_varonia.items():
    if len(infos) > 0:
        adresse = infos[0]
        if adresse:
            print(f"→ Géocodage pour '{ville}' : '{adresse}'")
            coords = geocode_address(adresse)
            if coords:
                lat, lon, country = coords
                data_varonia[ville].extend([(lat, lon), country])
                print(f"   (lat, lon) = ({lat}, {lon}), pays = {country}")
            else:
                data_varonia[ville].append("Adresse introuvable ou timeout")
                print("   → Adresse introuvable ou timeout")
        else:
            data_varonia[ville].append("Adresse vide")
            print(f"   → Pas d'adresse pour '{ville}'")
    else:
        data_varonia[ville].append("Pas d'adresse disponible")
        print(f"   → La liste pour '{ville}' ne contient pas d'adresse")
    time.sleep(0.2)

# ------------------------ STATISTIQUES FINALES ------------------------
print("\n---------------- RÉSUMÉ ----------------")

nb_salles = len(data_varonia)
print(f"Nombre total de salles : {nb_salles}")

pays = [infos[2] for infos in data_varonia.values() if len(infos) >= 3 and isinstance(infos[2], str)]
pays_uniques = set(pays)
nb_pays = len(pays_uniques)
print(f"Nombre de pays différents : {nb_pays}")
print("Pays présents :", pays_uniques)

with open("data/stats_varonia.py","w") as f : 
    f.write(f'nb_salles = {nb_salles}\n')
    f.write(f'nb_pays = {nb_pays}\n')
    
    