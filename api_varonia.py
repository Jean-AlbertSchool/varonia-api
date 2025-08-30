from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
from pathlib import Path

app = FastAPI(title="Varonia API", version="1.0.0")

# Configuration CORS pour Lovable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chemin vers la base de données
BASE_PATH = Path(__file__).parent
DB_PATH = BASE_PATH / "database" / "varonia.db"

@app.get("/")
def read_root():
    return {"message": "API Varonia - Données des salles"}

@app.get("/stats/salles")
def get_stats_salles():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM stats_salles ORDER BY annee, nb_joueurs DESC", conn)
        conn.close()
        
        data = df.to_dict('records')
        return {
            "success": True,
            "data": data,
            "total": len(data)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
