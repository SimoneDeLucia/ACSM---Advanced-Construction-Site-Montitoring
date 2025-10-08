from merakiSensors import sensors
from crane_movement_recognition import image_detection 
from datetime import datetime
import json
import sys
import os
import csv
import shutil

RETI = {
    "THU": {"network_id": "L_575897802350018094", "weatherstation_id": 266643},
    "B12": {"network_id": "L_575897802350020686", "weatherstation_id": 266643},
    "HOM_BIS": {"network_id": "L_575897802350019550", "weatherstation_id": 266643},
}

def salva_risultato(nome, dati):
    os.makedirs("dati_giornata", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    path = f"dati_giornata/{nome}_{timestamp}.json"
    with open(path, "w") as f:
        json.dump(dati, f, indent=2)
    print(f"Dati salvati in: {path}")

def leggi_foto_locali(base_folder):
    """
    Scansiona la cartella camera_snapshot e ritorna tutte le foto disponibili
    organizzate per rete e camera.
    """
    foto = {}
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.endswith(".jpg"):
                path = os.path.join(root, file)
                parts = path.split(os.sep)

                # Estraggo rete e camera dal path: es. camera_snapshot/THU/camera_0/...
                if len(parts) >= 3:
                    rete = parts[1]   # THU
                    camera = parts[2] # camera_0
                    foto.setdefault(rete, {}).setdefault(camera, []).append(path)

    # Ordino le foto per timestamp nel nome file
    for rete in foto:
        for camera in foto[rete]:
            foto[rete][camera].sort()

    print(f"📸 Foto trovate: {sum(len(c) for r in foto.values() for c in r.values())}")
    return foto

def genera_csv_gru(day, rete, camera="camera_0"):
    """
    Genera un CSV di analisi gru per la rete indicata usando image_detection.
    Restituisce la lista di righe lette dal CSV generato.
    """
    os.makedirs("csv", exist_ok=True)

    image_detection(day, "camera_snapshot", rete, camera)

    csv_filename = os.path.join("csv", f"image_analysis_{rete}_{camera}_{day}.csv")

    if not os.path.exists(csv_filename):
        print(f"Nessun CSV generato per {rete}")
        return []

    with open(csv_filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=" ")
        return [row for row in reader]
    
def calcolo_giornata_csv():
    print("Calcolo giornata CSV...")

    #Contiamo il numero totale di foto per rete
    foto = leggi_foto_locali("camera_snapshot")

    #Dati dai sensori e dalla gru
    s = sensors()
    # generazione CSV gru
    giorno_corrente = datetime.now().date()

    """
    for rete, ids in RETI.items():
        image_detection(giorno_corrente, "camera_snapshot", rete, "camera_0")

    # poi leggi i csv generati dalla cartella csv/
    dati_gru = []
    for rete in RETI.keys():
        csv_folder = "csv"
        for file in os.listdir(csv_folder):
            if file.startswith(f"image_analysis_{rete}_camera_0_{giorno_corrente}"):
                with open(os.path.join(csv_folder, file), newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter=" ")
                    dati_gru.extend([row for row in reader])
    """

    for rete, ids in RETI.items():
        print(f"Rete: {rete}")

        dati_gru = genera_csv_gru(giorno_corrente, rete) or []

        dati_wifi = s.SENSE_calculate_connections(network_id=ids["network_id"]) or []
        dati_meteo = s.SENSE_calculate_weather_conditions(
            network_id=ids["network_id"],
            weatherstation_id=ids["weatherstation_id"]
        ) or []

        #Lista dei timeslot
        if hasattr(s, 'slot_timestamps'):
            slots = s.slot_timestamps
        else:
            print("⚠️ slot_timestamps non trovato, uso un unico slot di default")
            now = datetime.now()
            slots = [{"date": now.strftime("%Y-%m-%d"), "timeslot": "00:00:00-23:59:59"}]

        os.makedirs("dati_giornata", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        csv_path = f"dati_giornata/{rete}_giornata_{timestamp}.csv"

        fieldnames = [
            "Date", "Timeslot", "Crane_Moves", "Wireless_Devices",
            "App_Temp", "Dew_Point", "Feels_Like", "Humidity", "Temperature", "Photos"
        ]

        with open(csv_path, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for slot in slots:
                date = slot["date"]
                timeslot = slot["timeslot"]

                # Gru
                gru_row = next((g for g in dati_gru if g.get("Day") == date and g.get("Timeframe") == timeslot), {})
                crane_moves = int(gru_row.get("NumberOfMoves", 0)) if gru_row else 0

                # Wireless
                wifi_row = next((w for w in dati_wifi if w.get("Date") == date and w.get("Timeslot") == timeslot), {})
                wifi_devices = int(wifi_row.get("device_connected", 0)) if wifi_row else 0

                # Meteo
                meteo_row = next((m for m in dati_meteo if m.get("date") == date and m.get("timeslot") == timeslot), {})
                app_temp = meteo_row.get("app_temp(℃)")
                dew_point = meteo_row.get("dew_point(℃)")
                feels_like = meteo_row.get("feels_like(℃)")
                humidity = meteo_row.get("humidity(%)")
                temperature = meteo_row.get("temperature(℃)")

                # Foto → conteggio totale per rete
                photos_count = sum(len(c) for r in foto.values() for c in r.values())

                row = {
                    "Date": date,
                    "Timeslot": timeslot,
                    "Crane_Moves": crane_moves,
                    "Wireless_Devices": wifi_devices,
                    "App_Temp": app_temp,
                    "Dew_Point": dew_point,
                    "Feels_Like": feels_like,
                    "Humidity": humidity,
                    "Temperature": temperature,
                    "Photos": photos_count
                }

                writer.writerow(row)

        print(f"CSV giornata creato: {csv_path}")
        cancella_snapshot("camera_snapshot")

def cancella_snapshot(dir_name):
    abs_dir = os.path.abspath(dir_name)
    cwd = os.path.abspath(os.getcwd())

    if not os.path.exists(abs_dir):
        print(f"Directory not found: {abs_dir}")
    else:
        # safety: only remove if the directory is inside the current working directory
        if os.path.commonpath([cwd, abs_dir]) != cwd:
            print(f"Refusing to delete directory outside the current working directory: {abs_dir}")
        else:
            try:
                shutil.rmtree(abs_dir)
                print(f"Deleted directory and all contents: {abs_dir}")
            except Exception as e:
                print(f"Error while deleting {abs_dir}: {e}")

if __name__ == "__main__":
    calcolo_giornata_csv()
