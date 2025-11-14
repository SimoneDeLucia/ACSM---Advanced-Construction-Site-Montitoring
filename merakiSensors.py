import requests
import meraki
import credentials as cr
from pprint import pprint
import datetime
from datetime import datetime, timedelta
import time
import os
from boxsdk import Client, OAuth2
import paho.mqtt.client as mqtt
import threading
import csv
import pytz


#Prima classe dove vengono raggruppati tutti i sensori all'interno di un'organizzazione e di una rete. 
#Poi ciò dovrebbbe andare a svilupparsi in una classe per ciascuna dispositivo(camera, appliance, access-point, ecc...)
class sensors:
    ### VARIABILI GLOBALI ###

    # API

    #API Key e Base URL
    API_KEY_Meraki = cr.MERAKI_KEY
    API_KEY_Box = None #TODO: da aggiungere
    API_KEY_Centralina = cr.METEO_STATION_API_KEY
    APPLICATON_KEY_Centralina = cr.METEO_STATION_APP_KEY
    BASE_URL_Meraki = "https://api.meraki.com/api/v1/"
    BASE_URL_Centralina = "https://api.ecowitt.net/api/v3/device/"

    #Inizializzazione dashboard
    dashboard = None
    #Organizzazione e Network
    ORG_ID = None
    NETWORK_ID = []
    
    # TIMESTAMP

    #Locazione dove inserire i timestamp per suddividere la giornata
    slot_timestamps = []

    #DISPOSITIVI

    #Variabili per gestire i dispositivi della rete 
    DEVICES = {} # raggruppamento generale
    UPLINK_DEVICES = {} # raggruppamento per uplink 
    NETWORK_DEVICES = [] # raggruppamento per reti di appartenenza

    #Raggruppamenti per tipologia di dispositivo
    NET_CAMERAS = {}
    NET_ACCESS_POINTS = {}
    NET_SENSORS = {}
    NET_WEATHERSTATION = {}

    excluded_macs = {} #usata dalle chiamate di connettività per raccogliere i mac address dei dispositivi già registrati come monitoraggio

    # THREAD MQTT 
    mqtt_threads = []

    ### FUNZIONI ###

    # INIZIALIZZAZIONE

    def __init__(self):
        
        #Inizializzazione dashboard, per ottenere ID organizzazione, Rete e seriali
        os.makedirs('logs', exist_ok=True)
        self.dashboard = meraki.DashboardAPI(api_key=self.API_KEY_Meraki, output_log=True, print_console=True, log_path='logs/')
        self._init_organization()
        self._process_networks()
        self._process_devices()
        self._process_timestamps()
        #self._init_mqtt() #TODO da finalizzare



    ### FUNZIONI DI INIZIALIZZAZIONE ### 


    def _init_organization(self):
        organizations = self.dashboard.organizations.getOrganizations()
        self.ORG_ID = organizations[0]['id']
        
    def _process_networks(self):

        response_netID = self.dashboard.organizations.getOrganizationNetworks(self.ORG_ID)  
        for net in response_netID:
            self.NETWORK_ID.append({
                "name": net['name'],
                "id": net['id']
            })
        
    def _process_devices(self):
        #Vengono prelevati i seriali dei dispositivi Meraki e
        response_serial = self.dashboard.organizations.getOrganizationDevices(self.ORG_ID)
        
        #Vengono raggruppati i seriali all'interno della rete
        i = 0
        for device in response_serial:
            self.DEVICES[i] = {
                "NUMBER": i,
                "SERIAL": device['serial'],
                "DEVICE_MODEL": device['model'],
                "DEVICE_PRODUCT": device['productType'],
                "MAC_ADDRESS" : device['mac'],
                "NETWORK_ID": device.get('networkId'),
                "HAS_A_UPLINK" : None,
                "DEVICE_UPLINK" : None
                
            }
            i = i+1

        #Vengono prelevate le centraline meteo

        #Vengono individuati i dispositivi attivi e vengono ripartiti all'interno delle reti. 
        #Le stazioni meteo le assumo sempre attive con uplink dato dal seriale (la chiamata API non restituisce un uplink dettagliato come quello meraki)
        self.process_weatherstation_devices()
        self.process_uplink_devices()
        self.process_network_devices()
        

        #Applico una suddivisione in base alla tipologia dei dispositivi
        self.NET_CAMERAS = self.get_device_info("camera")
        self.NET_ACCESS_POINTS = self.get_device_info("wireless")
        self.NET_SENSORS = self.get_device_info("sensor")
        self.NET_WEATHERSTATION = self.get_device_info("weatherstation")

        self.excluded_macs = {device["MAC_ADDRESS"].lower() for device in self.DEVICES.values()}
        
    
    def _process_timestamps(self):
        #Crea slot di massimo 2h
        self.slot_timestamps = []

        now = datetime.now(pytz.utc)
        start_of_day = now.replace(hour=6, minute=0, second=0, microsecond=0)  # esempio: dalle 6 UTC
        slot_duration = timedelta(hours=2)

        slot_start = start_of_day
        while slot_start < now:
            slot_end = slot_start + slot_duration - timedelta(seconds=1)  # 🔧 max 1s meno
            if slot_end > now:
                slot_end = now

            self.slot_timestamps.append({
                "date": slot_start.strftime("%Y-%m-%d"),
                "timeslot": f"{slot_start.strftime('%H:%M:%S')}-{slot_end.strftime('%H:%M:%S')}",
                "start": slot_start.isoformat().replace("+00:00", "Z"),
                "end": slot_end.isoformat().replace("+00:00", "Z")
            })

            slot_start += slot_duration


    # Inizializza il client MQTT, raccoglie informazioni dal broker
    # va terminata

    def _init_mqtt(self):

        #TODO Ciclo per ogni camera presente all'interno dell'organizzazione, inoltre va rifinito mqtt


        def _start_mqtt_client(SERIAL_CAMERA):
    
            # Build the topic using the first camera serial
            topic = f"/merakimv/{SERIAL_CAMERA}/0"

            # Define the MQTT broker and port
            broker = "mqtt.merakiabitarein.app"
            port = 80

            # Define the callback for when a message is received
            def on_message(client, userdata, msg):
                print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")

            # Create MQTT client and set callback
            client = mqtt.Client()
            client.on_message = on_message

            # Connect to the broker
            client.connect(broker, port, 60)

            # Subscribe to the topic
            client.subscribe(topic)

            print(f"Subscribed to topic: {topic}")

            # Start the loop to process received messages
            client.loop_start()

            print("MQTT client started.")

        self.mqtt_threads[0] = threading.Thread(target=_start_mqtt_client, args=(self.SERIAL_CAMERA[0],), daemon=True)
        self.mqtt_threads[0].start()

    
    ### FUNZIONI SENSORI ###

    #Funzione per scattare fotografie con le camere all'interno di una singola rete

    def SENSE_photo_single_net(self, network_id):
        """
        **Scatta la fotografia all'interno di una singola rete**
        - network_id: ID della rete
        """
        net_name = self.get_network_name(network_id)

        #in teoria, si dovrebbe ciclare tra le camere a disposizione...
        CAMERAS = self.get_devices_serial(net_name, self.NET_CAMERAS, 'camera')

        if not CAMERAS:
            raise ValueError("No cameras found in " + net_name + " network.") 

        for CAMERA in CAMERAS:
            try:
                self.take_snapshot(CAMERA, net_name, CAMERAS.index(CAMERA))
            except Exception as e:
                print(f"Error taking snapshot for camera {CAMERA}: {e}")
                continue
            

    #Funzione per scattare fotografie in tutte le reti

    def SENSE_photo_all_net(self):
        
        #Scatta la foto in tutte le reti**
        for net in self.NETWORK_ID:
            network_id = net["id"]
            self.SENSE_photo_single_net(network_id)

    # Funzione che effettua il calcolo complessivo delle detection wireless. È richiesto indicare il nome della rete
    
    def SENSE_calculate_connections(self, network_id): 

        # Per salvare il file csv ho bisogno del nome della rete, che mi ricavo tramite l'id
        net_name = self.get_network_name(network_id)

        WIRELESS_DETECTIONS = []
        number_macs_detected = self.filter_macs_in_net(network_id)
        

        for slot in self.slot_timestamps:
            t0 = slot["start"]
            t1 = slot["end"]
            date = slot ["date"]
            timeslot = slot ['timeslot']
            # Ensure t1 > t0
            if t1 <= t0:
                print(f"Skipping slot because t1 ({t1}) is not after t0 ({t0})")
                continue
            aggregated_data = {
                "Date": date,
                "Timeslot": timeslot,
                "device_connected": self.get_connections_in_timeslot(network_id, t0, t1, number_macs_detected)
            }
            WIRELESS_DETECTIONS.append(aggregated_data)


        self.create_CSV_file(WIRELESS_DETECTIONS, net_name, "wireless_detections")

        return WIRELESS_DETECTIONS

    # Funzione che effettua il calcolo complessivo delle wireless detection di tutte le reti

    def SENSE_calculate_connections_all_net(self):
        all_data = []
        for net in self.NETWORK_ID:
            network_id = net["id"]
            net_data = self.SENSE_calculate_connections(network_id)
            all_data.extend(net_data)  # accumula tutto
        return all_data


    # Calcola le condizioni meteo
    def SENSE_calculate_weather_conditions(self,network_id,weatherstation_id):
        
        """**Preleva le condizioni meteo di una rete, e le inserisce all'interno di un CSV.**
        Il CSV riporterà i seguenti campi
        1. date: La data della raccolta dei dati meteorologici nel formato YYYY-MM-DD.
        2. timeslot: L'intervallo di tempo durante il quale sono stati raccolti i dati, formattato come HH:MM:SS-HH:MM:SS.
        3. app_temp(℃): La temperatura percepita (in gradi Celsius), che tiene conto di fattori come l'umidità e il vento.
        4. dew_point(℃): Il punto di rugiada (in gradi Celsius), che indica la temperatura alla quale l'aria diventa satura di umidità.
        5. feels_like(℃): Un'altra misura della temperatura percepita (in gradi Celsius), spesso considerando il raffreddamento da vento o l'indice di calore.
        6. humidity(%): La percentuale di umidità relativa, che rappresenta la quantità di umidità presente nell'aria.
        7. temperature(℃): La temperatura reale dell'aria (in gradi Celsius) misurata durante l'intervallo di tempo.
        - network_id: ID della rete
        - weatherstation_id : ID della centralina meteo"""

        WEATHER_DETECTIONS = []
        net_name = self.get_network_name(network_id)

        for slot in self.slot_timestamps:
            t0 = slot["start"]
            t1 = slot["end"]
            date = slot ["date"]
            timeslot = slot ['timeslot']
            # Ensure t1 > t0
            if t1 <= t0:
                print(f"Skipping slot because t1 ({t1}) is not after t0 ({t0})")
                continue
            weather_info = self.get_weatherstation_historical_info(weatherstation_id, t0, t1)
            #Estraggo i dati dalla risposta
            data = weather_info.get('data', {})
            if not isinstance(data, dict):
                # Se i dati non sono un dizionario, significa che non ci sono dati disponibili
                print(f"No weather data available for {timeslot} ({date})")
                continue

            outdoor = data.get('outdoor', {})
            app_temp = outdoor.get('app_temp')
            dew_point = outdoor.get('dew_point')
            feels_like = outdoor.get('feels_like')
            humidity = outdoor.get('humidity')
            temperature = outdoor.get('temperature')

            aggregated_data = {
                "date": date,
                "timeslot": timeslot,
                "app_temp(℃)": self.get_field_mean(app_temp),    
                "dew_point(℃)": self.get_field_mean(dew_point),
                "feels_like(℃)": self.get_field_mean(feels_like),
                "humidity(%)": self.get_field_mean(humidity),
                "temperature(℃)": self.get_field_mean(temperature)
            }
            WEATHER_DETECTIONS.append(aggregated_data)

        self.create_CSV_file(WEATHER_DETECTIONS, net_name, 'weather_detections')
        return WEATHER_DETECTIONS 


    #Funzione che effettua il calcolo complessivo delle condizioni meteo di tutte le reti

    def SENSE_calculate_weather_conditions_all_net(self):
        
        #Calcola le condizioni meteo in tutte le centraline registrate**
        for net_info in self.NET_WEATHERSTATION.items():
            network_id = net_info.get("net_id")
            weatherstation_id = net_info[1].get("weatherstation")
            if not weatherstation_id:
                continue
            self.SENSE_calculate_weather_conditions(network_id, weatherstation_id)

    
    #Upload dei CSV all'interno di Box

    def SENSE_box_upload(self):   
        # TODO: si devono inserire le credenziali corrette e l'upload del csv
        oauth = OAuth2(
            client_id='YOUR_CLIENT_ID',
            client_secret='YOUR_CLIENT_SECRET',
            access_token='YOUR_ACCESS_TOKEN',
        )
        client = Client(oauth)


    ### FUNZIONI CHIAMATE API ###

    # Funzione per scattare una fotografia
    # Passo il seriale e il numero della camera, e la rete di appartenenza, tramite funzione

    def take_snapshot(self, CAMERA, net_name, idx):
        #Se non ci sono camere nei seriali, e se la camera selezionata non ha un uplink, la funzione ritorna al chiamante.

        camera_device = next((device for device in self.DEVICES.values() if device["SERIAL"] == CAMERA), None)
        if not camera_device or not camera_device.get("HAS_A_UPLINK"):
            print(f"The camera {idx} is offline (no uplink device).")
        

        try:
            response_photo = self.dashboard.camera.generateDeviceCameraSnapshot(
            CAMERA,
            )
        except Exception as e:
            raise
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        #Viene estratto l'URL dello snapshot dalla risposta.
        snapshot_url = response_photo['url']

        #Tra l'ottenimento della foto e il suo salvataggio serve del tempo
        time.sleep(6)

        # Viene scaricato lo snapshot

        download_photo = requests.get(snapshot_url)

        # qui si dovrebbe fare la POST a BOX per salvare lì la foto. Per il momento, viene usata una cartella in locale alla repository chiamata camera_snapshot
        folder = os.path.join("camera_snapshot", net_name, f"camera_{idx}")
        os.makedirs(folder, exist_ok=True)

        # Viene salvata la foto
        if download_photo.status_code >= 200 and download_photo.status_code < 300:
            filename = os.path.join(folder, f"camera_snapshot_{timestamp}.jpg")
            with open(filename, 'wb') as f:
                f.write(download_photo.content)
            print(f"Photo for camera {CAMERA} downloaded as {filename}")
        else:
            print(f"Failed to download photo. Status code: {download_photo.status_code}")


    # Chiamata API per ottenere le informazioni sulla centralina meteo

    def get_weatherstation_historical_info(self, network_id, start, end):

        params = {
            "application_key": self.APPLICATON_KEY_Centralina,
            "api_key": self.API_KEY_Centralina,
            "mac": self.get_field(network_id, "MAC_ADDRESS"),
            "start_date": start,
            "end_date": end,
            "call_back": "outdoor",
            "temp_unitid": 1,
            "rainfall_unitid": 12,
            "cycle_type": "30min"

        }
        print(start)
        response = requests.get(self.BASE_URL_Centralina + "history", params=params)
        print("risposta da get_weatherstation_historical_info: \n",response.json())
        return response.json()
    
    # Effettua una serie di chiamate API per ottenere informazioni sulle detection wireless

    def get_connections_in_timeslot(self, network_id, t0,t1, number_macs_detected):

        #TODO : Da decidere l'approccio da adottare
        
        resolution = 300 #300 = ogni 5 minuti. 3600 = ogni ora. Ogni slot 

        connections_in_timeslots = None

        # ASSUNZIONE 1: Considero validi per la mia statistica solo i dispositivi connessi tramite wireless. 
        # Uso getNetworkWirelessClientCountHistory siccome mi restituisce il numero di dispositivi connessi alla rete wireless

        response_profiles_wireless_timestamp = self.dashboard.wireless.getNetworkWirelessClientCountHistory(
            network_id, t0=t0, t1=t1, resolution = resolution
        )

        #Calcola la media dei client connessi
        client_counts = [item['clientCount'] for item in response_profiles_wireless_timestamp if item.get('clientCount') is not None]
        if client_counts:
            avg_clients_connected = sum(client_counts) / len(client_counts)
        else:
            avg_clients_connected = 0

        #Applico il fattore 0,8: la stima che viene fatta all'interno di un cantiere è che 5 persone possano possedere 6 dispositivi(fattore 1,2)
        connections_in_timeslots = int(avg_clients_connected * 0.8)

        return connections_in_timeslots
    
    def get_connections_in_timeslot_wired(self, network_id, t0,t1, number_macs_detected):
        # ASSUNZIONE 2: Considero validi per la mia statistica anche i dispositivi connessi in maniera wired. 
        # In questo caso, utilizzo la chiamata NetworkClientsOverview, in particolare il parametro di clients connected
        # Tuttavia, tra questi valori vanno individuati i dispositivi ininfluenti alla mia statistica, come ad esempio i dispositivi Meraki
    
        resolution = 300 #300 = ogni 5 minuti. 3600 = ogni ora. Ogni slot 

        connections_in_timeslots = None

        response_profiles_wireless_timestamp = self.dashboard.wireless.getNetworkWirelessClientCountHistory(
            network_id, t0=t0, t1=t1, resolution = resolution
        )

        #Calcola la media dei client connessi
        client_counts = [item['clientCount'] for item in response_profiles_wireless_timestamp if item.get('clientCount') is not None]
        if client_counts:
            avg_clients_connected = sum(client_counts) / len(client_counts)
        else:
            avg_clients_connected = 0
        
        response_client_overview = self.dashboard.networks.getNetworkClientsOverview(
            network_id, t0=t0, t1=t1
        )

        #considero il minimo tra il numero di dispositivi totali all'interno della risposta in response_clients_overview e il 
        avg_clients_connected = min(response_client_overview.get('counts', {}).get('total', 0), number_macs_detected)

        

        #Applico il fattore 0,8: la stima che viene fatta all'interno di un cantiere è che 5 persone possano possedere 6 dispositivi(fattore 1,2)
        connections_in_timeslots = int(avg_clients_connected * 0.8)

        return connections_in_timeslots
    
    
    #Funzione che ritorna il massimo numero di mac address utili individuati all'interno della rete
    
    def filter_macs_in_net(self, network_id):

        # Mi ricavo tutti i dispositivi individuati a partire dalla giornata lavorativa
        DEVICES_DETECTED = self.dashboard.networks.getNetworkClients(
            network_id, total_pages = 'all', t0 = self.slot_timestamps[0]['start']
        )

        # mi filtro i dispositivi che non fanno statistica, ovvero sia
        # 1. I dispositivi che vengono catalogati come centraline meteo (WeatherStation)
        # 2. I dispositivi che non generano traffico di rete
        # 3. I dispositivi che sono all'interno della lista dei dispositivi meraki

        client_macs = {
            client['mac'].lower()
            for client in DEVICES_DETECTED
            if 'mac' in client
            and client.get('description') != 'WeatherStation'
            and client.get('usage', {}).get('total', 0) > 0
        }
        

        filtered_client_macs = client_macs - self.excluded_macs

        #ritorno il numero di elementi all'interno di filtered_client_macs
        return len(filtered_client_macs)
    
    #Funzione che riporta la lista di stazioni meteo

    def get_weatherstation_device_list(self):
        params = {
            "application_key": self.APPLICATON_KEY_Centralina,
            "api_key": self.API_KEY_Centralina
        }
        response = requests.get(self.BASE_URL_Centralina + "list", params=params)
        return response.json()

    # Funzione che inserisce all'interno i dispositivi raggiungibili dall'esterno tramite uplink

    def process_uplink_devices(self):
        #Vengono raggruppati i device con un uplink

        #Vengono esclusi dal conteggio le stazioni meteo, siccome hanno una struttura del seriale differente
        serials = [device["SERIAL"] for device in self.DEVICES.values() if device.get("DEVICE_PRODUCT") != "weatherstation"]
        response_uplink = self.dashboard.organizations.getOrganizationDevicesUplinksAddressesByDevice(self.ORG_ID, serials=serials)

        i = 0
        for device in response_uplink:
            self.UPLINK_DEVICES[i] = {
            "NUMBER": i,
            "SERIAL": device['serial'],
            "DEVICE_PRODUCT": device['productType'],
            "DEVICE_UPLINK": device['uplinks']
            }
            i += 1

        for idx, device in self.DEVICES.items():
            serial = device["SERIAL"]
            uplink_info = next((uplink for uplink in self.UPLINK_DEVICES.values() if uplink["SERIAL"] == serial), None)
            if uplink_info:
                self.DEVICES[idx]["HAS_A_UPLINK"] = True
                self.DEVICES[idx]["DEVICE_UPLINK"] = uplink_info["DEVICE_UPLINK"]
            # Nel caso delle centraline meteo, queste hanno già un uplink e sono già state inserite all'interno dei dispositivi. Pertanto le inserisco direttamente nei dispositivi con un uplink
            # Viene usato come uplink il mac address, siccome è tramite quello che si possono effettuare le chiamate API
            elif self.DEVICES[idx]["HAS_A_UPLINK"]:
                self.UPLINK_DEVICES[idx] = {
                    "NUMBER": idx,
                    "SERIAL": device['SERIAL'],
                    "DEVICE_PRODUCT": device['DEVICE_PRODUCT'],
                    "DEVICE_UPLINK": device['DEVICE_UPLINK']
                }
            else:
                self.DEVICES[idx]["HAS_A_UPLINK"] = False
                self.DEVICES[idx]["DEVICE_UPLINK"] = None


    ### CHIAMATE DI GESTIONE ### 

    #Ottiene la media all'interno di un campo del meteo

    def get_field_mean(self, field):

        field_list = field.get('list', {})

        # Extract only the temperature values from app_temp_list (e.g., '22.5')
        field_values = [float(v) for v in field_list.values() if v not in [None, '', 'null']]
        if not field_values:
            return None
        mean = sum(field_values) / len(field_values)
        return round(mean, 2)


        
    def create_CSV_file(self, DETECTIONS, net_name, category):

        csv_folder = os.path.join("csv", net_name)
        os.makedirs(csv_folder, exist_ok=True)

        # Use the date of the first detection as part of the filename
        if DETECTIONS:
            # Extract date from the first detection slot
            #first_date_str = DETECTIONS[0]['date'] # 'YYYY-MM-DD'
            first_date_str = DETECTIONS[0].get('date') or DETECTIONS[0].get('Date')

            csv_filename = os.path.join(csv_folder, f"{category}_{net_name}_{first_date_str}.csv")

            with open(csv_filename, mode="w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=DETECTIONS[0].keys())
                writer.writeheader()
                writer.writerows(DETECTIONS)
            print(f"CSV file '{csv_filename}' created with aggregated data.")
        else:
            print("No data to write to CSV.")

    #Funzione che suddivide i dispositivi a seconda della rete di appartenenza

    def process_network_devices(self):
        
        #Processa i dispositivi 

        for net in self.NETWORK_ID:
            devices_in_network = [
                {
                    "device_name": device.get("DEVICE_MODEL"),
                    "device_serial": device.get("SERIAL"),
                    "device_category": device.get("DEVICE_PRODUCT"),
                    "HAS_A_UPLINK": device.get("HAS_A_UPLINK"),
                    "DEVICE_UPLINK": device.get("DEVICE_UPLINK")
                }
                for device in self.DEVICES.values()
                if device.get("NETWORK_ID") == net["id"]
            ]
            self.NETWORK_DEVICES.append({
                "Name": net["name"],
                "Id": net["id"],
                "devices": devices_in_network
            })



    # Funzione che inserisce le stazioni meteo all'interno del dizionario dei dispositivi.

    def process_weatherstation_devices(self):
        
        weatherstation_list = self.get_weatherstation_device_list()

        # Extract the list of weatherstation devices
        weatherstation_data = weatherstation_list.get('data', {})
        weatherstation_devices = weatherstation_data.get('list', [])
        print(weatherstation_devices)
        for device in weatherstation_devices:
            device_name = device.get('name', '')
            # The net name is after 'AI-WS-' in the device name
            if device_name.startswith('AI-WS-'):
                net_name = device_name.replace('AI-WS-', '')
                print(f"Device: {device_name}, Net name: {net_name}")
                # Add weatherstation to DEVICE if net_name matches any network
                matching_net = next((net for net in self.NETWORK_ID if net['name'] == net_name), None)
                if matching_net:
                    new_idx = max(self.DEVICES.keys()) + 1 if self.DEVICES else 0
                    self.DEVICES[new_idx] = {
                        "NUMBER": new_idx,
                        "SERIAL": device.get('id', ''),
                        "DEVICE_MODEL": device.get('stationtype', ''),
                        "DEVICE_PRODUCT": "weatherstation",
                        "MAC_ADDRESS": device.get('mac', ''),
                        "NETWORK_ID": matching_net['id'],
                        "HAS_A_UPLINK": True,
                        "DEVICE_UPLINK": device.get('mac', '')
                    }
            else:
                print(f"Device name '{device_name}' does not match expected format")

    
### FUNZIONI DI SERVIZIO ###

    #i field dove è possibile fare ricerca sono: SERIAL, NUMBER, DEVICE_MODEL, DEVICE_PRODUCT, MAC_ADDRESS, NETWORK_ID, HAS_A_UPLINK, DEVICE_UPLINK
    def get_field(self, id, field):
        for device in self.DEVICES.values():
            if str(device.get('SERIAL', '')) == str(id):
                return device.get(field, None)
        return None
        
    def get_devices_serial(self, network_id, DEVICE_LIST, device_type):
        return DEVICE_LIST.get(network_id, {}).get(device_type, [])
    
    def get_devices(self):
        return self.DEVICES

    def get_uplink_devices(self):
        return self.UPLINK_DEVICES

    def get_network_devices(self):
        return self.NETWORK_DEVICES
    
    def get_network_name(self, net_id):
        for net in self.NETWORK_ID:
            if net["id"] == net_id:
                return net["name"]
        return None
    
    def get_network_id(self, net_name):
        for net in self.NETWORK_ID:
            if net["name"] == net_name:
                return net["id"]
        return None
    
    def get_device_info(self, device_type):
        DEVICES_TO_EXTRACT = {}

        for net in self.NETWORK_DEVICES:
            net_id = net["Id"]
            net_name = net["Name"]
            dev = [
                device["device_serial"]
                for device in net["devices"]
                if device.get("device_category", "").lower() == device_type
            ]
            DEVICES_TO_EXTRACT[net_name] = {
                "net_id": net_id,
                device_type : dev
            }

        return DEVICES_TO_EXTRACT