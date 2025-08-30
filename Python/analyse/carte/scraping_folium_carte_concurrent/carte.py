import folium
import pandas as pd
from folium.plugins import MarkerCluster, MiniMap, Fullscreen
from branca.element import Element
import json
import logging as log
from supabase import create_client
import os
import uuid


SUPABASE_URL = "https://yqpsthbcpwfbrfpmxikn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxcHN0aGJjcHdmYnJmcG14aWtuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjEzNzI2OSwiZXhwIjoyMDcxNzEzMjY5fQ.u5dlFMKRqQcTKHo56bulL58oOs4hyWZKaDNRuFVwLak"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
# -------------------------------------------------------------------
# 1) Chargement des données depuis JSON
# -------------------------------------------------------------------
def load_dict_from_file(name, folder=".", ext=".json"):
    path = f"{folder}/{name}{ext}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

data_varonia     = load_dict_from_file("data_varonia")
data_zerolatency = load_dict_from_file("data_zerolatency")
data_eva         = load_dict_from_file("data_eva")
data_sandbox     = load_dict_from_file("data_sandbox")
data_vrcave      = load_dict_from_file("data_vrcave")
data_anvio       = load_dict_from_file("data_anvio")

# -------------------------------------------------------------------
# 2) Construction d’un DataFrame et export Excel
# -------------------------------------------------------------------
providers = {
    'Zerolatency': data_zerolatency,
    'Varonia':     data_varonia,
    'SandBox':     data_sandbox,
    'Eva':         data_eva,
    'VR Cave':     data_vrcave,
    'Anvio':       data_anvio
}

rows = []
for provider, dataset in providers.items():
    for key, infos in dataset.items():
        row = {
            'provider': provider,
            'key':      key,
            'phone':    None,
            'email':    None,
            'site':     None,
            'address':  None,
            'latitude': None,
            'longitude':None
        }
        if provider == 'Zerolatency':
            if len(infos) >= 1: row['phone']   = infos[0]
            if len(infos) >= 2: row['email']   = infos[1]
            if len(infos) >= 3: row['site']    = infos[2]
            if len(infos) >= 4: row['address'] = infos[3]
            if len(infos) >= 5 and isinstance(infos[4], (tuple, list)) and len(infos[4]) == 2:
                row['latitude'], row['longitude'] = infos[4]
        elif provider == 'Varonia':
            if len(infos) >= 1: row['address'] = infos[0]
            if len(infos) >= 2 and isinstance(infos[1], (tuple, list)) and len(infos[1]) == 2:
                row['latitude'], row['longitude'] = infos[1]
        elif provider == 'SandBox':
            if len(infos) >= 1: row['phone']   = infos[0]
            if len(infos) >= 2: row['address'] = infos[1]
            if len(infos) >= 3 and isinstance(infos[2], (tuple, list)) and len(infos[2]) == 2:
                row['latitude'], row['longitude'] = infos[2]
        elif provider == 'Eva':
            if len(infos) >= 1: row['phone'] = infos[0]
            row['address'] = key
            if len(infos) >= 2 and isinstance(infos[1], (tuple, list)) and len(infos[1]) == 2:
                row['latitude'], row['longitude'] = infos[1]
        elif provider == 'VR Cave':
            if len(infos) >= 1 and isinstance(infos[0], list) and infos[0]:
                row['address'] = infos[0][0]
            if len(infos) >= 2 and isinstance(infos[1], list) and infos[1]:
                row['phone'] = infos[1][0]
            if len(infos) >= 3: row['site'] = infos[2]
            if len(infos) >= 4 and isinstance(infos[3], (tuple, list)) and len(infos[3]) == 2:
                row['latitude'], row['longitude'] = infos[3]
        elif provider == 'Anvio':
            if infos and isinstance(infos[0], (tuple, list)) and len(infos[0]) == 2:
                row['latitude'], row['longitude'] = infos[0]
        rows.append(row)

df = pd.DataFrame(rows)
df.to_excel('emplacements_vr.xlsx', index=False)
print("✅ DataFrame et Excel générés.")

import folium
from folium.plugins import MarkerCluster, MiniMap, Fullscreen
from branca.element import Element
import json

# -------------------------------------------------------------------
# Vos dicts doivent être préalablement chargés :
# data_zerolatency, data_varonia, data_sandbox, data_eva, data_vrcave, data_anvio
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# 1) Variables de comptage pour chaque entreprise
# -------------------------------------------------------------------
count_zerolatency = 0
count_varonia     = 0
count_sandbox     = 0
count_eva         = 0
count_vrcave      = 0
count_anvio       = 0

# -------------------------------------------------------------------
# 2) Création de la carte sombre
# -------------------------------------------------------------------
m = folium.Map(
    location=[48.8566, 2.3522],
    zoom_start=4,
    tiles="CartoDB dark_matter",
    attr="CartoDB Dark Matter"
)

# -------------------------------------------------------------------
# 3) Configurations des couches
# -------------------------------------------------------------------
color_hex_map = {
    "blue":   "#42A5F5",
    "red":    "#FF0000",
    "green":  "#00FF00",
    "orange": "#FFA500",
    "purple": "#800080",
    "teal":   "#008080"
}

configs = [
    {"dict_name": "data_zerolatency", "display_name": "Zerolatency", "color": "blue"},
    {"dict_name": "data_varonia",    "display_name": "Varonia",    "color": "red"},
    {"dict_name": "data_sandbox",    "display_name": "SandBox",    "color": "green"},
    {"dict_name": "data_eva",        "display_name": "Eva",        "color": "orange"},
    {"dict_name": "data_vrcave",     "display_name": "VR Cave",    "color": "purple"},
    {"dict_name": "data_anvio",      "display_name": "Anvio",      "color": "teal"}
]

offsets = [
    (-30,  0),
    ( 30,  0),
    (  0,-30),
    (  0, 30),
    ( 30, 30),
    (-30,-30)
]

# -------------------------------------------------------------------
# 4) Ajout des points et clusters
# -------------------------------------------------------------------
for idx, cfg in enumerate(configs):
    name_layer = cfg["display_name"]
    hex_code   = color_hex_map[cfg["color"]]
    dataset    = globals().get(cfg["dict_name"], {})
    dx, dy     = offsets[idx]

    fg = folium.FeatureGroup(name=name_layer, show=True)

    icon_create = f"""
    function(cluster) {{
      var count = cluster.getChildCount();
      return L.divIcon({{
        html: '<div style="background-color:{hex_code};border-radius:50%;width:30px;height:30px;'
             + 'display:flex;align-items:center;justify-content:center;font-size:14px;color:white;">'
             + count + '</div>',
        className: 'marker-cluster',
        iconSize: new L.Point(30, 30),
        iconAnchor: new L.Point({dx}, {dy})
      }});
    }}
    """
    cluster = MarkerCluster(icon_create_function=icon_create, maxClusterRadius=40)
    fg.add_child(cluster)

    for cle, infos in dataset.items():
        coords = None
        popup_html = ""

        if cfg["dict_name"] == "data_zerolatency":
            if len(infos) >= 5 and isinstance(infos[4], (tuple, list)) and len(infos[4]) == 2:
                phone, email, site, adresse_val = infos[:4]
                coords = infos[4]
                popup_html = f"""
                <div style="font-size:14px;color:#000;">
                  <b>Clé :</b> {cle}<br>
                  <b>Adresse :</b> {adresse_val}<br>
                  <b>Tél :</b> {phone}<br>
                  <b>Email :</b> {email}<br>
                  <b>Site :</b> <a href="{site}" target="_blank">{site}</a>
                </div>"""
                count_zerolatency += 1

        elif cfg["dict_name"] == "data_varonia":
            if len(infos) >= 2 and isinstance(infos[1], (tuple, list)) and len(infos[1]) == 2:
                adresse_val = infos[0]
                coords = infos[1]
                popup_html = f"""
                <div style="font-size:14px;color:#000;">
                  <b>Clé :</b> {cle}<br>
                  <b>Adresse :</b> {adresse_val}
                </div>"""
                count_varonia += 1

        elif cfg["dict_name"] == "data_sandbox":
            if len(infos) >= 3 and isinstance(infos[2], (tuple, list)) and len(infos[2]) == 2:
                phone, adresse_val = infos[:2]
                coords = infos[2]
                popup_html = f"""
                <div style="font-size:14px;color:#000;">
                  <b>Clé :</b> {cle}<br>
                  <b>Adresse :</b> {adresse_val}<br>
                  <b>Tél :</b> {phone}
                </div>"""
                count_sandbox += 1
        elif cfg["dict_name"] == "data_eva":
          if len(infos) >= 3 and isinstance(infos[2], (tuple, list)) and len(infos[2]) == 2:
              adresse_val = infos[0]
              phone = infos[1]
              coords = infos[2]
              popup_html = f"""
              <div style="font-size:14px;color:#000;">
                <b>Ville :</b> {cle}<br>
                <b>Adresse :</b> {adresse_val}<br>
                <b>Tél :</b> {phone}
              </div>"""
              count_eva += 1


        elif cfg["dict_name"] == "data_vrcave":
            if len(infos) >= 4 and isinstance(infos[3], (tuple, list)) and len(infos[3]) == 2:
                adrs, tels, site_val = infos[:3]
                coords = infos[3]
                adresse_val = adrs[0] if isinstance(adrs, list) and adrs else "N/A"
                phone_val   = tels[0] if isinstance(tels, list) and tels else "N/A"
                popup_html = f"""
                <div style="font-size:14px;color:#000;">
                  <b>Clé :</b> {cle}<br>
                  <b>Adresse :</b> {adresse_val}<br>
                  <b>Tél :</b> {phone_val}<br>
                  <b>Site :</b> <a href="{site_val}" target="_blank">{site_val}</a>
                </div>"""
                count_vrcave += 1

        elif cfg["dict_name"] == "data_anvio":
            if infos and isinstance(infos[0], (tuple, list)) and len(infos[0]) == 2:
                coords = infos[0]
                popup_html = f"""
                <div style="font-size:14px;color:#000;">
                  <b>Ville :</b> {cle}
                </div>"""
                count_anvio += 1

        if coords:
            folium.CircleMarker(
                location=coords,
                radius=5,
                color=hex_code,
                weight=1,
                fill=True,
                fill_color=hex_code,
                fill_opacity=0.9,
                popup=folium.Popup(popup_html, max_width=300, min_width=180),
                tooltip=name_layer
            ).add_to(cluster)

    fg.add_to(m)

# -------------------------------------------------------------------
# 5) Contrôles et mini-carte
# -------------------------------------------------------------------
folium.LayerControl(collapsed=False).add_to(m)
Fullscreen(position="topright").add_to(m)
m.add_child(MiniMap(toggle_display=True, position="bottomright"))

# -------------------------------------------------------------------
# 6) Colorer les labels du LayerControl
# -------------------------------------------------------------------
layer_colors = {cfg["display_name"]: color_hex_map[cfg["color"]] for cfg in configs}
colors_json = json.dumps(layer_colors)

js_colors = f"""
<script>
  var layerColors = {colors_json};
  setTimeout(function() {{
    var container = document.querySelector('.leaflet-control-layers-overlays');
    if (!container) return;
    container.querySelectorAll('label').forEach(function(label) {{
      var span = label.querySelector('span');
      if (!span) return;
      var name = span.innerText.trim();
      var color = layerColors[name] || '#000';
      var box = document.createElement('span');
      box.style.display = 'inline-block';
      box.style.width = '12px';
      box.style.height = '12px';
      box.style.backgroundColor = color;
      box.style.marginRight = '6px';
      box.style.verticalAlign = 'middle';
      label.insertBefore(box, label.firstChild);
    }});
  }}, 500);
</script>
"""
m.get_root().html.add_child(Element(js_colors))

# -------------------------------------------------------------------
# 7) Bouton « Classement » dynamique avec liens “Site web”
# -------------------------------------------------------------------
js_counters = {
    "Zerolatency": count_zerolatency,
    "Varonia":     count_varonia,
    "SandBox":     count_sandbox,
    "Eva":         count_eva,
    "VR Cave":     count_vrcave,
    "Anvio":       count_anvio
}
js_site_urls = {
    "Zerolatency": "https://zerolatencyvr.com/en",
    "Varonia":     "https://www.virtual-games-park.fr/",
    "SandBox":     "https://sandboxvr.com/cerritos/",
    "Eva":         "https://www.eva.gg/en-FR",
    "VR Cave":     "https://vrcave.io/",
    "Anvio":       "https://anvio.com/"
}
counters_json = json.dumps(js_counters)
urls_json     = json.dumps(js_site_urls)

html_panel = f"""
<div id="ranking-container" style="
  position:absolute; top:10px; left:10px; z-index:9999; font-family:Arial,sans-serif;">
  <button id="ranking-btn" style="
    background:#333; color:#fff; border:none; padding:6px 12px;
    border-radius:4px; cursor:pointer; font-size:14px;">
    Classement
  </button>
  <div id="ranking-list" style="
    display:none; margin-top:6px; background:rgba(0,0,0,0.8);
    color:#fff; padding:10px; border-radius:4px;
    box-shadow:0 0 6px rgba(0,0,0,0.5); font-size:13px;">
    <strong>Classement des entreprises</strong>
    <ol id="ranking-items" style="padding-left:18px; margin:6px 0 0 0;"></ol>
  </div>
</div>
<script>
  var counters = {counters_json};
  var siteUrls = {urls_json};
  function renderRanking() {{
    var active = [];
    document.querySelectorAll('.leaflet-control-layers-overlays input[type=checkbox]')
      .forEach(function(input) {{
        if (input.checked) {{
          var label = input.parentElement.querySelector('span').innerText.trim();
          active.push(label);
        }}
      }});
    active.sort(function(a,b) {{ return (counters[b]||0) - (counters[a]||0); }});
    var html = '';
    active.forEach(function(name) {{
      var cnt = counters[name]||0;
      var url = siteUrls[name]||'#';
      html += '<li style="margin:4px 0;">'
            + name + ' : ' + cnt
            + ' <a href="' + url
            + '" target="_blank" style="color:#0bf;margin-left:8px;text-decoration:underline;">'
            + 'Site web</a></li>';
    }});
    document.getElementById('ranking-items').innerHTML = html;
  }}
  var btn = document.getElementById('ranking-btn'),
      list = document.getElementById('ranking-list');
  btn.onclick = function() {{
    if (list.style.display==='none') {{
      list.style.display='block';
      renderRanking();
    }} else {{
      list.style.display='none';
    }}
  }};
  document.querySelectorAll('.leaflet-control-layers-overlays input[type=checkbox]')
    .forEach(function(input) {{
      input.addEventListener('change', function() {{
        if (list.style.display==='block') renderRanking();
      }});
    }});
</script>
"""
carte_filename = "carte_loc_concurrent.html"
m.save(carte_filename)

with open(carte_filename, "rb") as f:
    supabase.storage.from_("carte_loc_concurrent").update(carte_filename, f)

# === 3. URL publique
url_publique = supabase.storage.from_("carte_loc_concurrent").get_public_url(carte_filename)
print("📍 URL publique de la carte :", url_publique)
# -------------------------------------------------------------------
# 8) Sauvegarde finale
# -------------------------------------------------------------------
dictionnaires = {
    "data_zerolatency": data_zerolatency,
    "data_varonia":     data_varonia,
    "data_sandbox":     data_sandbox,
    "data_eva":         data_eva,
    "data_vrcave":      data_vrcave,
    "data_anvio":       data_anvio
}

for nom_fichier, contenu in dictionnaires.items():
    json_path = f"{nom_fichier}.json"
    
    # Sauvegarde locale (optionnelle mais utile pour vérif)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(contenu, f, ensure_ascii=False, indent=2)
    
    # Envoi dans Supabase
    with open(json_path, "rb") as f:
        try:
            supabase.storage.from_("carte_loc_concurrent").update(json_path, f)
            print(f"✅ Upload réussi : {json_path}")
        except Exception as e:
            print(f"⚠️ Erreur update {json_path} :", e)

csv_filename = "emplacements_vr.xlsx"
df.to_excel(csv_filename, index=False, engine='openpyxl')

with open(csv_filename, "rb") as f:
    try:
        supabase.storage.from_("carte_loc_concurrent").update(csv_filename, f)
        print(f"✅ Excel uploadé avec succès : {csv_filename}")
    except Exception as e:
        print(f"⚠️ Erreur update CSV :", e)
log.info("carte_loc_concurrent.html")
log.info("✅ Carte générée dans 'carte_localisation_classement.html' !")
log.info(f"Zerolatency: {count_zerolatency}")
log.info(f"Varonia    : {count_varonia}")
log.info(f"SandBox    : {count_sandbox}")
log.info(f"Eva        : {count_eva}")
log.info(f"VR Cave    : {count_vrcave}")
log.info(f"Anvio      : {count_anvio}")
