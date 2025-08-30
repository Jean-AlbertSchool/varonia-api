from pathlib import Path
import pandas as pd
import sys
import logging
import os

# chemin absolu du dossier où se trouve le script
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, "data_prep_hist.log")

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

try:
    base = Path(__file__).resolve().parents[2]  # Go up to project root
except NameError:
    base = Path.cwd()

data_path = (base / 'Data' / 'data_varonia_brut.parquet').resolve()

# Override seulement si l’argument semble être un fichier parquet
if len(sys.argv) > 1:
    arg1 = sys.argv[1]
    if arg1.lower().endswith(".parquet"):
        data_path = Path(arg1).resolve()

logging.info(f'Fichier utilisé : {data_path}')

df = pd.read_parquet(data_path, engine='pyarrow')
if df is not None:
    logging.info(f"✅ Chargement réussi : {data_path}")
else :
    logging.error(f"❌ Échec du chargement : {data_path}")


# =====================
# Nettoyage initial
# =====================
try:
    df.drop(columns=[col for col in df if col.startswith("EVA")], inplace=True)
    df = df[df['Location'] != 'VaroniaLab']
    df = df[df["Location"] != "Site Challenger"]
    df = df[df["Location"] != "3DS Cite Patrimoine"]
    df = df[df["Location"] != "RPIMA - Bayonne"]
    df = df[df["Location"] != "IRCGN - Cergy"]
    df = df[df["Location"] != "Cinema Dieppe"]
    df = df[df["Location"] != "Dreamworld"]
    df['Location'] = df['Location'].replace('B14 Str', 'B14 - Bondoufle')
    df.drop(columns='TimeZone_slloc', inplace=True)
    logging.info("✅ Nettoyage initial réussi")
except Exception as e:
    logging.error(f"❌ Erreur lors du nettoyage initial : {e}")

# =====================
# Renommage des colonnes
# =====================
desired_cols = [
    'id', 'id_party', 'id_device', 'party_source_db', 'start', 'end',
    'area', 'Server', 'game_value', 'game_mode_value', 'difficulty_value',
    'duration', 'state', 'player_count', 'player_name', 'player_email',
    'device', 'rel_party_source_db', 'location', 'common_score',
    'id_location', 'type_group', 'language_slloc', 'party_source_id',
    'RelPartySourceId'
]

def rename_columns_by_list(df, new_cols):
    n_df = len(df.columns)
    n_new = len(new_cols)
    if n_df == n_new:
        df.columns = new_cols
    elif n_df > n_new:
        df.columns = new_cols + list(df.columns[n_new:])
    else:
        raise ValueError(f"Le DataFrame a {n_df} colonnes, moins que la liste cible ({n_new}).")
    return df

try:
    df = rename_columns_by_list(df, desired_cols)
    logging.info("✅ Renommage des colonnes réussi")
except Exception as e:
    logging.error(f"❌ Erreur lors du renommage des colonnes : {e}")

# =====================
# Géocodage Google
# =====================
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderQuotaExceeded
import time

# Paramètres Google API
API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyB--QHyl2kD0vmzwOUgx-rzuMQJ2GUFQDY")
SLEEP_BETWEEN_CALLS = 1.0
MAX_RETRIES = 2
LANG = "fr"
REGION_BIAS = "fr"

# Source d'adresses
addr_col = "address" if "address" in df.columns else "location"
addresses = (
    df[addr_col]
    .astype(str)
    .str.strip()
    .replace({"": None})
    .dropna()
    .unique()
    .tolist()
)

# Geocoder
geolocator = GoogleV3(api_key=API_KEY, timeout=10)

def _sleep(attempt=0):
    time.sleep(SLEEP_BETWEEN_CALLS + attempt * 0.5)

def safe_geocode(q):
    for a in range(MAX_RETRIES + 1):
        try:
            return geolocator.geocode(q, exactly_one=True, language=LANG, region=REGION_BIAS)
        except (GeocoderTimedOut, GeocoderQuotaExceeded):
            _sleep(a)
        except Exception:
            break
    return None

def extract_component(components, type_name, key="long_name"):
    for c in components:
        if type_name in c.get("types", []):
            return c.get(key)
    return None

def parse_google_result(g):
    raw = getattr(g, "raw", {}) or {}
    comps = raw.get("address_components", [])
    return {
        "adresse": getattr(g, "address", None),
        "latitude": getattr(g, "latitude", None),
        "longitude": getattr(g, "longitude", None),
        "postal_code": extract_component(comps, "postal_code"),
        "city": extract_component(comps, "locality"),
        "departement": extract_component(comps, "administrative_area_level_2"),
        "region": extract_component(comps, "administrative_area_level_1"),
        "country": extract_component(comps, "country"),
    }

# Géocodage des adresses
logging.info("🔄 Début du géocodage...")
records = []
for i, a in enumerate(addresses):
    g = safe_geocode(a)
    if g:
        rec = {"source_address": a}
        rec.update(parse_google_result(g))
    else:
        rec = {
            "source_address": a, "adresse": None,
            "latitude": None, "longitude": None, "postal_code": None,
            "city": None, "departement": None, "region": None, "country": None
        }
    records.append(rec)
    _sleep()
    if (i + 1) % 10 == 0 and i < len(addresses) - 1:  # Éviter le doublon sur le dernier
        logging.info(f"  Géocodé {i + 1}/{len(addresses)} adresses")

mapping_df = pd.DataFrame(records).rename(columns={"source_address": addr_col})
df_enriched = df.merge(mapping_df, on=addr_col, how="left")
logging.info(f"✅ Géocodage terminé : {len(addresses)} adresses traitées")

# =====================
# DEBUG - Analyse des coordonnées
# =====================
logging.info(f"\n🔍 DEBUG - Analyse des coordonnées:")
logging.info(f"  Locations uniques dans df: {df['location'].nunique()}")
logging.info(f"  Addresses géocodées: {len(addresses)}")
logging.info(f"  Lignes avec lat/lng non-null: {df_enriched[['latitude', 'longitude']].dropna().shape[0]}")
logging.info(f"  Coordonnées uniques: {df_enriched[['latitude', 'longitude']].dropna().drop_duplicates().shape[0]}")

# Identifier les doublons de coordonnées
coords_counts = df_enriched[['location', 'latitude', 'longitude']].dropna().groupby(['latitude', 'longitude'])['location'].apply(list).reset_index()
duplicates = coords_counts[coords_counts['location'].str.len() > 1]
if not duplicates.empty:
    logging.info(f"  ⚠️ Coordonnées en doublon:")
    for _, row in duplicates.iterrows():
        logging.info(f"    {row['latitude']}, {row['longitude']} -> {row['location']}")

# =====================
# Enrichissement GeoNames
# =====================
import requests

# Configuration GeoNames avec ton username
os.environ["GEONAMES_USER"] = "jean_lec"  # Ton username GeoNames
GEONAMES_USER = os.getenv("GEONAMES_USER")
GN_TIMEOUT = 10
GN_RETRIES = 3
GN_BACKOFF = 0.7
GN_RATE_SLEEP = 0.6

logging.info(f"\n🔄 Début enrichissement GeoNames avec user: {GEONAMES_USER}")

if not GEONAMES_USER:
    logging.info("❌ GeoNames: username manquant")
else:
    session = requests.Session()

    def gn_get(url, params, retries=GN_RETRIES):
        """GET avec gestion d'erreurs, retries + backoff, parsing JSON sécurisé."""
        last_err = None
        for i in range(retries):
            try:
                r = session.get(url, params=params, timeout=GN_TIMEOUT)
                if r.status_code >= 500 or r.status_code == 429:
                    last_err = f"HTTP {r.status_code}"
                    time.sleep(GN_BACKOFF * (i + 1))
                    continue
                if r.status_code >= 400:
                    return None, f"HTTP {r.status_code}: {r.text[:200]}"
                data = r.json()
                # Erreurs signalées par GeoNames dans 'status'
                if isinstance(data, dict) and "status" in data:
                    val = data["status"].get("value")
                    msg = data["status"].get("message", "")
                    if val in (18, 19):  # quotas horaires/journaliers dépassés
                        last_err = f"GeoNames {val}: {msg}"
                        time.sleep(GN_BACKOFF * (i + 1))
                        continue
                    return None, f"GeoNames {val}: {msg}"
                return data, None
            except requests.Timeout:
                last_err = "timeout"
                time.sleep(GN_BACKOFF * (i + 1))
            except Exception as e:
                return None, f"Exception: {e}"
        return None, (last_err or "unknown error")

    # Extraire les coordonnées uniques
    unique_coords = (
        df_enriched[["latitude", "longitude"]]
        .dropna()
        .drop_duplicates()
    )
    
    logging.info(f"  {len(unique_coords)} coordonnées uniques à enrichir")

    # Appeler GeoNames pour chaque paire unique
    rows = []
    for i, (lat, lng) in enumerate(unique_coords.itertuples(index=False)):
        cc = iso2 = adm1 = None

        # 1) Récupérer le pays et la subdivision
        d1, e1 = gn_get(
            "http://api.geonames.org/countrySubdivisionJSON",
            {"lat": lat, "lng": lng, "username": GEONAMES_USER}
        )
        
        if e1 or not isinstance(d1, dict):
            logging.info(f"    ⚠️ Échec countrySubdivision ({lat},{lng}): {e1}")
        else:
            cc = d1.get("countryCode")
            adm1 = d1.get("adminName1")

            # 2) Si on a pays + région, récupérer le code ISO
            if cc and adm1:
                d2, e2 = gn_get(
                    "http://api.geonames.org/searchJSON",
                    {
                        "name_equals": adm1,
                        "country": cc,
                        "featureCode": "ADM1",
                        "style": "FULL",
                        "maxRows": 1,
                        "username": GEONAMES_USER,
                    }
                )
                if e2:
                    logging.info(f"    ⚠️ Échec search ADM1 ({lat},{lng}) {adm1}/{cc}: {e2}")
                else:
                    geos = (d2 or {}).get("geonames") or []
                    if geos:
                        iso2 = (geos[0].get("adminCodes1") or {}).get("ISO3166_2")

        rows.append({
            "latitude": lat,
            "longitude": lng,
            "country_iso2": cc,
            "iso_3166_2": iso2,
            "admin1_name": adm1
        })

        time.sleep(GN_RATE_SLEEP)
        
        if (i + 1) % 10 == 0 and i < len(unique_coords) - 1:  # Éviter le doublon sur le dernier
            logging.info(f"    Enrichi {i + 1}/{len(unique_coords)} coordonnées")

    # Créer le DataFrame de mapping ISO
    iso_map = pd.DataFrame(rows)
    
    # Merger avec le DataFrame enrichi
    df_enriched = df_enriched.merge(
        iso_map, on=["latitude", "longitude"], how="left"
    )
    
    # Statistiques finales
    logging.info("✅ Enrichissement GeoNames terminé")
    logging.info(f"  Colonnes ajoutées: country_iso2, iso_3166_2, admin1_name")
    logging.info(f"  Lignes avec code ISO: {df_enriched['iso_3166_2'].notna().sum()}")
    logging.info(f"  Pays uniques: {df_enriched['country_iso2'].dropna().nunique()}")

logging.info("\n📊 Aperçu du DataFrame enrichi:")
logging.info(df_enriched[[addr_col, "latitude", "longitude", "country", "country_iso2", "iso_3166_2"]].head())

# Extraire l'année, le jour de la semaine et l'heure
df_enriched["year"] = df_enriched["end"].dt.year
df_enriched["weekday"] = df_enriched["end"].dt.day_name()
df_enriched["hour"] = df_enriched["end"].dt.strftime('%H:00')
# create a date column from the datetime 'end'
df_enriched['date'] = df_enriched['end'].dt.date

# =====================
# Détection des jours fériés
# =====================
import holidays
from datetime import date
import logging

def is_public_holiday(date_obj: date, country_iso2: str, subdiv_iso2: str | None = None) -> bool:
    """
    Vérifie si une date est un jour férié officiel dans un pays/région.
    
    date_obj: objet date Python
    country_iso2: ex 'FR', 'ES', 'AU'
    subdiv_iso2: ex 'FR-HDF' -> on utilise juste 'HDF' pour holidays
    """
    try:
        year = date_obj.year
        subdiv = None
        if subdiv_iso2 and "-" in subdiv_iso2:
            subdiv = subdiv_iso2.split("-", 1)[1]  # ex. 'FR-HDF' -> 'HDF'

        cal = holidays.country_holidays(country_iso2, subdiv=subdiv, years=[year])
        return date_obj in cal
    except Exception as e:
        # En cas d'erreur (pays non supporté, etc.), retourner False
        logging.warning(f"Erreur détection jour férié pour {country_iso2}/{subdiv_iso2}: {e}")
        return False

logging.info("🔄 Début détection des jours fériés...")

# Initialiser la colonne
df_enriched["jour_ferie"] = "Non"

# Compter les différents cas
total_rows = len(df_enriched)
with_coords = df_enriched[['country_iso2', 'iso_3166_2', 'date']].dropna().shape[0]
without_coords = total_rows - with_coords

logging.info(f"  Total de lignes: {total_rows}")
logging.info(f"  Avec coordonnées/codes ISO: {with_coords}")
logging.info(f"  Sans coordonnées/codes ISO: {without_coords}")

# Traiter les lignes avec codes ISO
success_count = 0
error_count = 0

for idx, row in df_enriched.iterrows():
    if pd.notna(row['country_iso2']) and pd.notna(row['date']):
        country = row['country_iso2']
        subdiv = row['iso_3166_2']
        date_val = row['date']
        
        if is_public_holiday(date_val, country, subdiv):
            df_enriched.at[idx, "jour_ferie"] = "Oui"
            success_count += 1
    else:
        error_count += 1

logging.info(f"✅ Détection des jours fériés terminée")
logging.info(f"  Jours fériés détectés: {(df_enriched['jour_ferie'] == 'Oui').sum()}")
logging.info(f"  Lignes traitées avec succès: {success_count}")
logging.info(f"  Lignes non traitées (données manquantes): {error_count}")

# Statistiques par pays
jours_feries_by_country = df_enriched[df_enriched['jour_ferie'] == 'Oui'].groupby(['country_iso2', 'country']).size().reset_index(name='count')
if not jours_feries_by_country.empty:
    logging.info(f"\n📊 Jours fériés par pays:")
    for _, row in jours_feries_by_country.iterrows():
        logging.info(f"  {row['country']} ({row['country_iso2']}): {row['count']} jours fériés")

# Exemples de jours fériés détectés
exemples_feries = df_enriched[df_enriched['jour_ferie'] == 'Oui'][['location', 'date', 'country', 'country_iso2', 'iso_3166_2']].head(5)
if not exemples_feries.empty:
    logging.info(f"\n🎉 Exemples de jours fériés détectés:")
    for _, row in exemples_feries.iterrows():
        logging.info(f"  {row['date']} - {row['location']} ({row['country']})")

logging.info(f"\n📈 Résumé:")
logging.info(f"  Jours normaux: {(df_enriched['jour_ferie'] == 'Non').sum()}")
logging.info(f"  Jours fériés: {(df_enriched['jour_ferie'] == 'Oui').sum()}")
logging.info(f"  Total: {len(df_enriched)}")

# Sauvegarde du DataFrame enrichi à la toute fin
df_without_errors = df_enriched[df_enriched['state'] != 25]
df_without_errors = df_enriched[df_enriched['state'] != 15]
df_without_errors = df_enriched[
    (df_enriched["start"] != pd.Timestamp("1900-01-01 00:00:00")) &
    (df_enriched["end"]   != pd.Timestamp("1900-01-01 00:00:00"))
]

df_without_errors = df_enriched[df_enriched['duration'] < 3600]
df_without_errors = df_enriched[df_enriched['duration'] > 0]

try:
    base = Path(__file__).resolve().parents[2]
except NameError:
    base = Path.cwd()

output_path = (base / 'Data' / 'data_varonia_without_errors.parquet').resolve()

logging.info(f'Sauvegarde du DataFrame sans erreurs dans : {output_path}')
try:
    df_without_errors.to_parquet(output_path, engine='pyarrow')
    logging.info('Sauvegarde réussie.')
except Exception as e:
    logging.error(f'Erreur lors de la sauvegarde du DataFrame sans erreurs : {e}')

# Enregistre dans G:\Varonia\Projet_clean\Data
try:
    base = Path(__file__).resolve().parents[2]
except NameError:
    base = Path.cwd()

output_path = (base / 'Data' / 'data_varonia_clean.parquet').resolve()

logging.info(f'Sauvegarde du DataFrame enrichi dans : {output_path}')
try:
    df_enriched.to_parquet(output_path, engine='pyarrow')
    logging.info('Sauvegarde réussie.')
except Exception as e:
    logging.error(f'Erreur lors de la sauvegarde du DataFrame enrichi : {e}')
