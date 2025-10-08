#Integra dati Meraki + analisi gru -> salva su SQLite per day/timeframe.
import os
import re
import json
import sqlite3
import csv
from datetime import datetime, date, time
from typing import List, Tuple, Dict, Optional
from merakiSensors import sensors  

REAL_TIMEFRAMES = [
    (time(6,0,0), time(7,59,59)),
    (time(8,0,0), time(9,59,59)),
    (time(10,0,0), time(11,59,59)),
    (time(12,0,0), time(13,59,59)),
    (time(14,0,0), time(15,59,59)),
    (time(16,0,0), time(17,59,59)),
    (time(18,0,0), time(20,0,0)),
]

IMAGES_DIR = "camera_snapshot"
CRANE_CSV = "test_case_response.csv"
DB_PATH = "cantiere.db"

def create_database(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cantiere_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network TEXT NOT NULL,
            day TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            photo_paths TEXT,
            wireless_clients INTEGER,
            crane_used TEXT,
            crane_moves INTEGER,
            weather TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(network, day, timeframe)
        )
    ''')
    conn.commit()
    conn.close()


def insert_or_replace_record(db_path: str, network: str, day: str, timeframe: str, photo_paths: List[str], wireless_clients: int,
                             crane_used: str, crane_moves: int, weather: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO cantiere_records (network, day, timeframe, photo_paths, wireless_clients, crane_used, crane_moves, weather)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(network, day, timeframe) DO UPDATE SET
            photo_paths=excluded.photo_paths,
            wireless_clients=excluded.wireless_clients,
            crane_used=excluded.crane_used,
            crane_moves=excluded.crane_moves,
            weather=excluded.weather,
            created_at = datetime('now')
    ''', (network, day, timeframe, json.dumps(photo_paths, ensure_ascii=False), wireless_clients, crane_used, crane_moves, weather))
    conn.commit()
    conn.close()


# ---------- parsing immagini ----------
def _label_from_tf(tf: Tuple[time, time]) -> str:
    return f"{tf[0].strftime('%H:%M')}-{tf[1].strftime('%H:%M')}"

def extract_date_time_from_filename(filename: str) -> Optional[Tuple[date, time]]:
    
    #Prova a estrarre una coppia (YYYY-MM-DD, HH:MM:SS) dal nome file.
    
    name = os.path.basename(filename)
    name_no_ext = os.path.splitext(name)[0]
    tokens = re.split(r'[_\-.]', name_no_ext)

    date_token = None
    time_token = None

    # cerca pattern YYYYMMDD e subito dopo HHMMSS
    for i, tok in enumerate(tokens):
        if re.fullmatch(r'\d{8}', tok):
            date_token = tok
            if i + 1 < len(tokens) and re.fullmatch(r'\d{6}', tokens[i+1]):
                time_token = tokens[i+1]
            break
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', tok):
            date_token = tok
            if i + 1 < len(tokens) and re.fullmatch(r'\d{6}', tokens[i+1]):
                time_token = tokens[i+1]
            break

    if not date_token:
        return None

    # parsedate
    try:
        if re.fullmatch(r'\d{8}', date_token):
            d = date(int(date_token[0:4]), int(date_token[4:6]), int(date_token[6:8]))
        else:
            # YYYY-MM-DD
            parts = date_token.split('-')
            d = date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None

    if time_token:
        try:
            hh = int(time_token[0:2])
            mm = int(time_token[2:4])
            ss = int(time_token[4:6])
            t = time(hh, mm, ss)
        except Exception:
            t = time(0, 0, 0)
    else:
        t = time(0, 0, 0)

    return d, t

def build_timeframes_from_images(images_dir: str, timeframes: List[Tuple[time, time]]) -> Dict[Tuple[str,str,str], List[str]]:
    
    #Restituisce dizionario: (network_name, date_str, timeframe_label) -> [full_image_path, ...]
    
    mapping: Dict[Tuple[str,str,str], List[str]] = {}

    if not os.path.isdir(images_dir):
        print(f"[warn] images dir {images_dir} non trovata.")
        return mapping

    for network in os.listdir(images_dir):
        network_dir = os.path.join(images_dir, network)
        if not os.path.isdir(network_dir):
            continue

        for root, dirs, files in os.walk(network_dir):
            for fname in sorted(files):
                if not fname.lower().endswith(".jpg"):
                    continue
                fpath = os.path.join(root, fname)
                parsed = extract_date_time_from_filename(fname)
                if not parsed:
                    continue
                d_obj, t_obj = parsed
                date_str = d_obj.isoformat()

                for tf in timeframes:
                    if tf[0] <= t_obj <= tf[1]:
                        tf_label = _label_from_tf(tf)
                        mapping.setdefault((network, date_str, tf_label), []).append(fpath)
                        break

    return mapping

def parse_crane_csv(csv_path: str = CRANE_CSV) -> Dict[Tuple[str, str], Dict]:
    
    #Legge response.csv e crea mappa (date_str, timeframe_label) -> {'used': 'Yes'|'No'|'Unknown', 'moves': int, 'weather': str}
   
    if not os.path.exists(csv_path):
        print(f"[info] {csv_path} non trovato: nessun dato gru disponibile.")
        return {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    # trova header (riga che contiene 'Day' e 'Timeframe' oppure la prima riga)
    header_idx = None
    for i, ln in enumerate(lines):
        if 'Day' in ln and 'Timeframe' in ln:
            header_idx = i
            break
    if header_idx is None:
        header_idx = 0

    header = lines[header_idx]
    data_lines = lines[header_idx+1:]

    # prova CSV comma
    parsed = {}
    if ',' in header:
        reader = csv.DictReader([header] + data_lines, delimiter=',')
        for row in reader:
            # normalizza nomi colonne possibili
            date_field = next((k for k in row.keys() if 'Day' in k or 'day' in k or 'DATE' in k), None)
            tf_field = next((k for k in row.keys() if 'Timeframe' in k or 'TimeFrame' in k or 'FRAME' in k), None)
            used_field = next((k for k in row.keys() if 'Was' in k or 'Used' in k or 'WasCraneUsed' in k), None)
            moves_field = next((k for k in row.keys() if 'Move' in k or 'NumberOfMoves' in k), None)
            weather_field = next((k for k in row.keys() if 'Weather' in k or 'CONDITION' in k), None)

            if not date_field or not tf_field:
                continue

            date_str = row[date_field].strip()
            tf_str = row[tf_field].strip()
            used = row.get(used_field, '').strip() if used_field else ''
            moves = row.get(moves_field, '').strip() if moves_field else '0'
            weather = row.get(weather_field, '').strip() if weather_field else ''

            try:
                moves_int = int(moves)
            except:
                moves_int = 0

            parsed[(date_str, tf_str)] = {
                'used': used if used else 'Unknown',
                'moves': moves_int,
                'weather': weather if weather else 'Unknown'
            }
        return parsed

    # altrimenti split per whitespace (tollerante)
    header_cols = re.split(r'\s+', header)
    for ln in data_lines:
        parts = re.split(r'\s+', ln)
        if len(parts) < 2:
            continue
        # se ci sono tanti campi li zip con header_cols
        row = dict(zip(header_cols, parts))
        # trova mapping come sopra
        date_field = next((k for k in row.keys() if 'Day' in k or 'day' in k or 'DATE' in k), header_cols[0])
        tf_field = next((k for k in row.keys() if 'Timeframe' in k or 'TimeFrame' in k or 'FRAME' in k), header_cols[1])
        used_field = next((k for k in row.keys() if 'Was' in k or 'Used' in k or 'WasCraneUsed' in k), None)
        moves_field = next((k for k in row.keys() if 'Move' in k or 'NumberOfMoves' in k or 'MOVE' in k), None)
        weather_field = next((k for k in row.keys() if 'Weather' in k or 'CONDITION' in k), None)

        date_str = row.get(date_field, '')
        tf_str = row.get(tf_field, '')
        used = row.get(used_field, '') if used_field else ''
        moves = row.get(moves_field, '0') if moves_field else '0'
        weather = row.get(weather_field, '') if weather_field else ''

        try:
            moves_int = int(moves)
        except:
            moves_int = 0

        parsed[(date_str, tf_str)] = {
            'used': used if used else 'Unknown',
            'moves': moves_int,
            'weather': weather if weather else 'Unknown'
        }

    return parsed

def get_wireless_clients_for_network(s_obj: 'sensors', network_id: str, date_str: str, tf_label: str,
                                     label_to_tf: Dict[str, Tuple[time, time]]) -> int:
    
    #Restituisce il numero di dispositivi wireless rilevati in un singolo network
    #per un determinato timeslot (date_str, tf_label)
    tf = label_to_tf.get(tf_label)
    if tf is None or network_id is None:
        return 0

    # costruisci t0,t1 in formato ISO
    t0 = f"{date_str}T{tf[0].strftime('%H:%M:%S')}Z"
    t1 = f"{date_str}T{tf[1].strftime('%H:%M:%S')}Z"

    try:
        # numero di mac rilevati utili
        num_macs = s_obj.filter_macs_in_net(network_id)
        clients = s_obj.get_connections_in_timeslot(network_id, t0, t1, num_macs)
        if clients is None:
            clients = 0
    except Exception as e:
        print(f"[warn] errore calcolo wireless per network {network_id}: {e}")
        clients = 0

    return int(clients)

def run_ingest(images_dir: str = IMAGES_DIR, csv_path: str = CRANE_CSV, db_path: str = DB_PATH):
    timeframes = REAL_TIMEFRAMES
    label_to_tf = { _label_from_tf(tf): tf for tf in timeframes }

    create_database(db_path)

    #mappa immagini per network
    images_map = build_timeframes_from_images(images_dir, timeframes)

    #parse csv gru
    crane_map = parse_crane_csv(csv_path)

    #inizializza sensors Meraki
    print("inizializzo Meraki sensors")
    s = sensors()
    print("sensors inizializzato.")

    #unione delle chiavi (network, date, slot trovati)
    networks = [net.get('name') for net in getattr(s, "NETWORK_ID", [])]
    all_keys = set(images_map.keys()) | set(
        (net, date, tf) for (date, tf) in crane_map.keys() for net in networks
    )

    if not all_keys:
        print("[info] nessun dato (immagini o csv gru) trovato per l'elaborazione.")
        return

    for network, date_str, tf_label in sorted(all_keys):
        photo_paths = images_map.get((network, date_str, tf_label), [])
        crane_info = crane_map.get((date_str, tf_label), {'used': 'Unknown', 'moves': 0, 'weather': 'Unknown'})

        # Calcola wireless clients per rete specifica
        try:
            network_id = next((net['id'] for net in getattr(s, "NETWORK_ID", []) if net['name']==network), None)
            if network_id:
                wireless_clients = get_wireless_clients_for_network(s, network_id, date_str, tf_label, label_to_tf)   
            else:
                wireless_clients = 0
        except Exception as e:
            print(f"[warn] errore ottenimento wireless clients per {network} {date_str} {tf_label}: {e}")
            wireless_clients = 0

        insert_or_replace_record(
            db_path=db_path,
            network=network,
            day=date_str,
            timeframe=tf_label,
            photo_paths=photo_paths,  #solo le foto del network
            wireless_clients=wireless_clients,
            crane_used=crane_info.get('used', 'Unknown'),
            crane_moves=int(crane_info.get('moves', 0)),
            weather=crane_info.get('weather', 'Unknown')
        )

        print(f"[ok] salvato {network} {date_str} {tf_label} | photos={len(photo_paths)} wireless={wireless_clients} crane_used={crane_info.get('used')} moves={crane_info.get('moves')} weather={crane_info.get('weather')}")

if __name__ == "__main__":
    run_ingest()
