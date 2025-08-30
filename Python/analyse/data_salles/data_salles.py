from pathlib import Path
import sys
import logging
import pandas as pd

# --- Logging visible à l'écran
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# --- Où suis-je ?
try:
    script_path = Path(__file__).resolve()
except NameError:
    script_path = Path.cwd().resolve()  # cas interactif / notebook
logging.info(f"Script: {script_path}")

# On vise .../Python comme base (puis /Data/...)
# data_salles.py est censé être .../Python/analyse/data_salles/data_salles.py
# parents: [data_salles, analyse, Python, Projet_clean, Varonia, G:\]
# => parents[2] == .../Python
base = script_path.parents[2]
logging.info(f"Base attendue (../..): {base}")

FILENAME = "data_varonia_without_errors.parquet"

# Candidats prioritaires
candidates = [
    base / "Data" / FILENAME,                       # G:\Varonia\Projet_clean\Python\Data\...
    Path.cwd() / "Data" / FILENAME,                 # si lancé d'ailleurs mais Data/ présent
]

# Argument CLI .parquet prioritaire
if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".parquet"):
    arg_path = Path(sys.argv[1]).resolve()
    candidates.insert(0, arg_path)
    logging.info(f"Argument .parquet détecté: {arg_path}")

# Choix du premier chemin existant
data_path = next((p for p in candidates if p.exists()), None)

# Si toujours pas trouvé, on scanne récursivement sous .../Python pour aider au debug
if data_path is None:
    search_root = base  # .../Python
    logging.warning(f"Fichier non trouvé dans candidats. Scan sous: {search_root}")
    found = list(search_root.rglob(FILENAME))
    if found:
        # Prend le premier match et informe
        data_path = found[0].resolve()
        logging.info(f"Trouvé via scan: {data_path}")
    else:
        # Diagnostic enrichi
        logging.error("Introuvable. Vérifie l’un des points suivants : "
                      "1) Nom exact du fichier, 2) Emplacement réel, 3) Droits/accès.")
        logging.error("Candidats testés :")
        for p in candidates:
            logging.error(f" - {p}")
        raise FileNotFoundError(
            f"Impossible de localiser {FILENAME} sous {search_root} ou candidats listés."
        )

logging.info(f"Fichier utilisé : {data_path}")

# Lecture parquet
df = pd.read_parquet(data_path, engine="pyarrow")
logging.info(f"✅ Chargement réussi ({len(df):,} lignes)")

# Exemple post-traitement
pd.set_option("display.max_columns", None)

salles_existantes = set()

for year in range(2018, 2026):
    df_year = df[df["date"].astype(str).str.startswith(str(year))]

    # On ne garde que les salles déjà connues (existantes avant cette année)
    df_year_filtré = df_year[df_year["location"].isin(salles_existantes)]

    # On groupe par salle et on trie
    globals()[f"nb_joueur_par_salle_{year}"] = (
        df_year_filtré.groupby("location")
        .size()
        .to_frame(name="nb_de_joueur")
        .reset_index()
        .sort_values(by="nb_de_joueur", ascending=False)  # <- TRI ICI
    )

    # On ajoute les salles de cette année à la mémoire des salles existantes
    salles_existantes.update(df_year["location"].unique())

   
# construction fiable de data_by_year (utilise les globals si déjà calculés sinon recalcul)
data_by_year = {}
for year in range(2019, 2026):
    key = f"nb_joueur_par_salle_{year}"
    if key in globals():
        data_by_year[year] = globals()[key]
    else:
        df_year = df[df["date"].dt.year == year]
        data_by_year[year] = (
            df_year.groupby("location")
            .size()
            .to_frame(name="nb_de_joueur")
            .reset_index()
            .sort_values(by="nb_de_joueur", ascending=False)
        )
stat_joueurs_par_salle_an = []
# Insérer les données de tous les années
for year, df_year in data_by_year.items():
    for _, row in df_year.iterrows():
        record = {
            "annee": year,
            "salle": row["location"],
            "nb_joueurs": int(row["nb_de_joueur"])
        }
        stat_joueurs_par_salle_an.append(record)   
        # --- Sauvegarde SQL simple ---
import sqlite3
db_folder = base / "database"  # = g:\Varonia\Projet_clean\Python\database
conn = sqlite3.connect(db_folder / "varonia.db")
pd.DataFrame(stat_joueurs_par_salle_an).to_sql('stats_salles', conn, if_exists='replace', index=False)
conn.close()
logging.info(f"✅ Données sauvées en SQL dans {db_folder / 'stat_joueurs_par_salle_an.db'}")