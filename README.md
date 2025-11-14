# DTLAB-AbitareIn

Project Work 2024-2025 Cisco AbitareIN

Gruppo BrickByte

- Simone De Lucia
- Federica Ferro
- Flavio Filippo Parrotta
- Simone Parente

## Descrizione

Analisi, raccolta dati e monitoraggio di lavori all'interno di un cantiere.

Al fine di monitorare l'ambiente e la presenza di personale, vengono monitorati i seguenti dati

- Temperature
- Movimenti di una gru
- numero di connessioni wireless all'interno del cantiere

I dati sono raccolti in maniera anonima, o vengono anonimizzati il più possibile, in linea con le disposizioni GDPR in materia

Le informazioni elaborate vengono conservate all'interno di un database e mostrate mediante dashboard PowerBi

## Flusso Dati Completo

```
┌──────────────┐
│ photoscript  │ → Acquisisce foto ogni 30s
└──────┬───────┘
       │
       ▼
┌──────────────┐
│camera_snapshot│ → Organizzate per rete/camera
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│crane_movement_   │ → Analizza foto con ChatGPT
│recognition.py    │ → Genera CSV movimenti gru
└──────┬───────────┘
       │
       ▼
┌──────────────┐
│csv/          │ → CSV temporanei per rete
│  ├─ THU/     │
│  ├─ B12/     │
│  └─ HOM_BIS/ │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ database.py      │ → Aggrega tutto in SQLite
│ run_ingest()     │
└──────┬───────────┘
       │
       ▼
┌──────────────┐
│cantiere.db   │ → Database finale
└──────────────┘
       │
       ▼
┌──────────────┐
│dashboard.py  │ → Visualizzazione Streamlit. Aggregazione CSV finale per PowerBI
└──────────────┘
```

## Componenti

### Photoscript.py

#### Scopo del file

### meraki_api_lib.ipynb

##### Scopo del File

Il notebook serve come:

- Ambiente di Test API: Laboratorio per sperimentare con le API Meraki utilizzando l'equipaggiamento reale fornito dall'azienda partner
- Documentazione Procedurale: Registro delle chiamate API testate con esempi di risposta
- Prototipazione Funzionalità: Area di sviluppo per nuove feature prima dell'implementazione in produzione
- debugging e Troubleshooting: Strumento per isolare e risolvere problematiche nelle integrazioni API

#### Struttura delle Sezioni

Il notebook è organizzato in celle markdown e code, suddivise per:

- ✅ Sezioni Validate: Funzionalità completamente testate
- ⚠️ Sezioni Sperimentali: Feature in fase di sviluppo
- ❌ API Deprecate: Chiamate non utilizzate nella versione finale

#### Integrazione con il Sistema

Le funzionalità validate in questo notebook vengono successivamente:

- Refactorizzate e ottimizzate
- Integrate nella classe sensors in merakiSensors.py
  Utilizzate dagli script di produzione (calcolo_giornata.py, photoscript.py)

### merakiSensors.py

#### Panoramica

merakiSensors.py è il **modulo principale** del sistema ACSM che fornisce un'interfaccia unificata per l'interazione con tutti i sensori e dispositivi Meraki presenti nei cantieri monitorati. Questo modulo incapsula la logica di comunicazione con le API Meraki ed Ecowitt, gestendo la raccolta, l'elaborazione e l'aggregazione dei dati provenienti da diverse tipologie di dispositivi.

#### Architettura

Il modulo è strutturato attorno alla classe `sensors`, che implementa il pattern **Facade** per semplificare l'accesso alle complesse API Meraki.

```python
from merakiSensors import sensors

# Inizializzazione
s = sensors()

# Utilizzo
s.SENSE_photo_all_net()
s.SENSE_calculate_connections_all_net()
s.SENSE_calculate_weather_conditions_all_net()
```

---

#### Classe: `sensors`

##### Variabili Globali

###### API e Autenticazione

| Variabile                   | Tipo           | Descrizione                                                     |
| ----------------------------- | ---------------- | ----------------------------------------------------------------- |
| `API_KEY_Meraki`            | `str`          | Chiave API per accesso dashboard Meraki                         |
| `API_KEY_Box`               | `str`          | Chiave API per upload su Box (TODO)                             |
| `API_KEY_Centralina`        | `str`          | Chiave API per centraline meteo Ecowitt                         |
| `APPLICATON_KEY_Centralina` | `str`          | Application key per API Ecowitt                                 |
| `BASE_URL_Meraki`           | `str`          | URL base API Meraki (`https://api.meraki.com/api/v1/`)          |
| `BASE_URL_Centralina`       | `str`          | URL base API Ecowitt (`https://api.ecowitt.net/api/v3/device/`) |
| `dashboard`                 | `DashboardAPI` | Istanza del client API Meraki                                   |

###### Organizzazione e Rete

| Variabile    | Tipo         | Descrizione                           |
| -------------- | -------------- | --------------------------------------- |
| `ORG_ID`     | `str`        | ID univoco dell'organizzazione Meraki |
| `NETWORK_ID` | `list[dict]` | Lista delle reti monitorate           |

**Struttura `NETWORK_ID`:**

```python
[
    {
        "name": "THU",
        "id": "L_XXXXXXXXXXXXXXXXXXX"
    },
    {
        "name": "B12",
        "id": "L_XXXXXXXXXXXXXXXXXXX"
    },
    {
        "name": "HOM_BIS",
        "id": "L_XXXXXXXXXXXXXXXXXXX"
    }
]
```

###### Gestione Timestamp

| Variabile         | Tipo         | Descrizione                                        |
| ------------------- | -------------- | ---------------------------------------------------- |
| `slot_timestamps` | `list[dict]` | Suddivisione giornata lavorativa in slot temporali |

**Struttura `slot_timestamps`:**

```python
[
    {
        "date": "2025-11-14",
        "start": "2025-11-14T06:00:00Z",
        "end": "2025-11-14T07:59:59Z",
        "timeslot": "06:00:00-07:59:59"
    },
    # ... altri 6 slot fino alle 20:00
]
```

###### Dispositivi

| Variabile            | Tipo              | Descrizione                                               |
| ---------------------- | ------------------- | ----------------------------------------------------------- |
| `DEVICES`            | `dict[int, dict]` | Raccolta generale di tutti i dispositivi                  |
| `UPLINK_DEVICES`     | `dict[int, dict]` | Dispositivi con connettività uplink                      |
| `NETWORK_DEVICES`    | `list[dict]`      | Dispositivi raggruppati per rete                          |
| `NET_CAMERAS`        | `dict`            | Camere MV per rete                                        |
| `NET_ACCESS_POINTS`  | `dict`            | Access Point wireless per rete                            |
| `NET_SENSORS`        | `dict`            | Sensori ambientali per rete                               |
| `NET_WEATHERSTATION` | `dict`            | Centraline meteo per rete                                 |
| `excluded_macs`      | `set`             | MAC address di dispositivi da escludere dalle statistiche |

**Struttura `DEVICES`:**

```python
{
    0: {
        "NUMBER": 0,
        "SERIAL": "Q2XX-XXXX-XXXX",
        "DEVICE_MODEL": "MV12W",
        "DEVICE_PRODUCT": "camera",
        "MAC_ADDRESS": "xx:xx:xx:xx:xx:xx",
        "NETWORK_ID": "L_XXXXXXXXXXXXXXXXX",
        "HAS_A_UPLINK": True,
        "DEVICE_UPLINK": [...]
    },
    # ... altri dispositivi
}
```

**Struttura `NETWORK_DEVICES`:**

```python
[
    {
        "Name": "THU",
        "Id": "L_XXXXXXXXXXXXXXXXXXX",
        "devices": [
            {
                "device_name": "MV12W",
                "device_serial": "Q2XX-XXXX-XXXX",
                "device_category": "camera",
                "HAS_A_UPLINK": True,
                "DEVICE_UPLINK": [...]
            },
            # ... altri dispositivi della rete
        ]
    },
    # ... altre reti
]
```

**Struttura `NET_CAMERAS` (e simili):**

```python
{
    "THU": {
        "net_id": "L_XXXXXXXXXXXXXXXXXXX",
        "camera": ["Q2XX-XXXX-XXXX", "Q2YY-YYYY-YYYY"]
    },
    "B12": {
        "net_id": "L_XXXXXXXXXXXXXXXXXXX",
        "camera": ["Q2ZZ-ZZZZ-ZZZZ"]
    }
}
```

###### Thread MQTT

| Variabile      | Tipo   | Descrizione                                   |
| ---------------- | -------- | ----------------------------------------------- |
| `mqtt_threads` | `list` | Lista thread per gestione MQTT (sperimentale) |

---

#### Metodi della Classe

##### Inizializzazione

###### `__init__(self)`

Costruttore della classe che inizializza tutti i componenti necessari.

**Workflow:**

1. Creazione directory logs per output debug
2. Inizializzazione dashboard Meraki
3. Recupero ID organizzazione
4. Elaborazione reti disponibili
5. Catalogazione dispositivi
6. Generazione timestamp giornalieri

```python
s = sensors()
# Esegue automaticamente tutta la fase di inizializzazione
```

---

##### Funzioni di Inizializzazione (Private)

###### `_init_organization(self)`

Recupera l'ID dell'organizzazione Meraki associata alla chiave API.

**Chiamata API:** `dashboard.organizations.getOrganizations()`

---

###### `_process_networks(self)`

Enumera tutte le reti disponibili nell'organizzazione e popola `NETWORK_ID`.

**Chiamata API:** `dashboard.organizations.getOrganizationNetworks(ORG_ID)`

---

###### `_process_devices(self)`

Elabora e categorizza tutti i dispositivi presenti nell'organizzazione.

**Steps:**

1. Recupero seriali dispositivi Meraki
2. Catalogazione in `DEVICES`
3. Integrazione centraline meteo via `process_weatherstation_devices()`
4. Identificazione dispositivi con uplink via `process_uplink_devices()`
5. Raggruppamento per rete via `process_network_devices()`
6. Categorizzazione per tipo tramite `get_device_info()`

**Chiamate API:**

- `dashboard.organizations.getOrganizationDevices(ORG_ID)`
- `dashboard.organizations.getOrganizationDevicesUplinksAddressesByDevice()`

---

###### `_process_timestamps(self)`

Genera gli slot temporali per la giornata lavorativa (6:00-20:00) suddivisi in 7 intervalli di 2 ore.

**Logica:**

```python
# Giornata = 14 ore (6:00 - 20:00)
# Slot = 7 intervalli
# Durata slot = 14 * 60 / 7 = 120 minuti
```

**Timezone:** Europe/Rome (gestito tramite `pytz`)

---

###### `_init_mqtt(self)` ⚠️

Inizializza client MQTT per ricezione eventi in tempo reale dalle camere.

**Stato:** Sperimentale - da completare

---

##### Funzioni Sensori (SENSE_*)

Tutte le funzioni con prefisso `SENSE_` sono funzioni di alto livello per la raccolta dati dai sensori.

###### `SENSE_photo_single_net(self, network_id)`

Scatta fotografie con tutte le camere presenti in una specifica rete.

**Parametri:**

- `network_id` (str): ID della rete Meraki

**Processo:**

1. Recupera lista camere dalla rete
2. Per ogni camera:
   - Genera timestamp
   - Richiede snapshot
   - Attende disponibilità (6 secondi)
   - Scarica e salva immagine

**Output:** File JPEG in `camera_snapshot/[RETE]/camera_[IDX]/`

**Naming:** `camera_[SERIAL]_snapshot_[YYYYMMDD_HHMMSS].jpg`

```python
s.SENSE_photo_single_net("L_XXXXXXXXXXXXXXXXXXX")
# Scatta foto su rete THU
```

---

###### `SENSE_photo_all_net(self)`

Scatta fotografie su tutte le reti configurate.

**Equivalente a:**

```python
for net in NETWORK_ID:
    SENSE_photo_single_net(net['id'])
```

---

###### `SENSE_calculate_connections(self, network_id)`

Calcola il numero di dispositivi client connessi alla rete wireless per ogni slot temporale.

**Parametri:**

- `network_id` (str): ID della rete Meraki

**Processo:**

1. Filtraggio dispositivi validi (esclusi Meraki, centraline, dispositivi senza traffico)
2. Per ogni slot temporale:
   - Chiamata API per conteggio client wireless
   - Calcolo media su intervalli di 5 minuti
   - Applicazione fattore correttivo 0.8 (1.2 device/persona)

**Output:** File CSV in `csv/[RETE]/wireless_detections_[RETE]_[DATA].csv`

**Struttura CSV:**

```csv
date,Timeslot,DeviceConnected
2025-11-14,06:00:00-07:59:59,5
2025-11-14,08:00:00-09:59:59,12
...
```

**Chiamate API:**

- `dashboard.wireless.getNetworkWirelessClientCountHistory()`
- `dashboard.networks.getNetworkClients()`

```python
connections = s.SENSE_calculate_connections("L_XXXXXXXXXXXXXXXXXXX")
# Restituisce lista dizionari con dati aggregati
```

---

###### `SENSE_calculate_connections_all_net(self)`

Calcola connessioni wireless per tutte le reti.

---

###### `SENSE_calculate_weather_conditions(self, network_id, weatherstation_id)`

Raccoglie dati meteo dalla centralina Ecowitt per ogni slot temporale.

**Parametri:**

- `network_id` (str): ID rete Meraki
- `weatherstation_id` (int): ID centralina Ecowitt

**Metriche raccolte:**

- `app_temp`: Temperatura apparente (°C)
- `dew_point`: Punto di rugiada (°C)
- `feels_like`: Temperatura percepita (°C)
- `humidity`: Umidità relativa (%)
- `temperature`: Temperatura reale (°C)

**Output:** File CSV in `csv/[RETE]/weather_detections_[RETE]_[DATA].csv`

**Struttura CSV:**

```csv
date,Timeslot,app_temp(℃),dew_point(℃),feels_like(℃),humidity(%),temperature(℃)
2025-11-14,06:00:00-07:59:59,18.5,12.3,17.8,65,19.2
...
```

**Chiamate API:**

- `get_weatherstation_historical_info()` (API Ecowitt)

```python
weather = s.SENSE_calculate_weather_conditions(
    network_id="L_575897802350018094",
    weatherstation_id=266643
)
```

---

###### `SENSE_calculate_weather_conditions_all_net(self)`

Raccoglie dati meteo da tutte le centraline configurate.

---

###### `SENSE_box_upload(self)` 🚧

Funzione per caricare CSV su Box cloud storage.

**Stato:** TODO - da implementare

---

##### Funzioni Chiamate API

###### `take_snapshot(self, CAMERA, net_name, idx)`

Scatta una singola fotografia da una camera specifica.

**Parametri:**

- `CAMERA` (str): Seriale della camera
- `net_name` (str): Nome della rete
- `idx` (int): Indice della camera nella rete

**Chiamate API:**

- `dashboard.camera.generateDeviceCameraSnapshot()`

---

###### `get_weatherstation_historical_info(self, network_id, start, end)`

Recupera dati storici dalla centralina meteo.

**Parametri:**

- `network_id` (str): ID rete (per recuperare MAC centralina)
- `start` (str): Timestamp inizio ISO8601
- `end` (str): Timestamp fine ISO8601

**Parametri API Ecowitt:**

- `cycle_type`: "30min" (aggregazione dati)
- `temp_unitid`: 1 (Celsius)
- `rainfall_unitid`: 12 (mm)
- `call_back`: "outdoor" (dati esterni)

**Ritorno:** Dict con dati meteo aggregati

---

###### `get_connections_in_timeslot(self, network_id, t0, t1, number_macs_detected)`

Calcola connessioni wireless in un intervallo temporale specifico.

**Parametri:**

- `network_id` (str): ID rete
- `t0` (str): Timestamp inizio
- `t1` (str): Timestamp fine
- `number_macs_detected` (int): Numero totale MAC rilevati nella giornata

**Logica:**

1. Chiamata API con risoluzione 300s (5 minuti)
2. Estrazione valori `clientCount` non nulli
3. Calcolo media connessioni
4. Applicazione fattore 0.8 per stima persone

**Ritorno:** `int` - Numero stimato persone presenti

---

###### `get_connections_in_timeslot_wired(self, network_id, t0, t1, number_macs_detected)` 🚧

Versione alternativa che considera anche connessioni cablate.

**Stato:** Implementazione alternativa commentata

---

###### `filter_macs_in_net(self, network_id)`

Determina il numero massimo di dispositivi client validi nella rete.

**Esclusioni:**

- Dispositivi con descrizione "WeatherStation"
- Dispositivi senza traffico di rete (`usage.total == 0`)
- Dispositivi Meraki (presenti in `excluded_macs`)

**Chiamate API:**

- `dashboard.networks.getNetworkClients()`

**Ritorno:** `int` - Numero MAC validi

---

###### `get_weatherstation_device_list(self)`

Recupera lista completa centraline meteo dall'account Ecowitt.

**Chiamate API:** `GET https://api.ecowitt.net/api/v3/device/list`

**Ritorno:** Dict con lista dispositivi


###### `process_uplink_devices(self)`

Identifica dispositivi con connettività uplink e aggiorna `UPLINK_DEVICES` e `DEVICES`.

**Chiamate API:**

- `dashboard.organizations.getOrganizationDevicesUplinksAddressesByDevice()`


##### Funzioni di Gestione

###### `get_field_mean(self, field)`

Calcola la media di un campo meteo da risposta API Ecowitt.

**Parametri:**

- `field` (dict): Campo con struttura `{"list": {...}}`

**Processo:**

1. Estrae valori numerici dalla lista
2. Filtra valori nulli/invalidi
3. Calcola media aritmetica
4. Arrotonda a 2 decimali

**Ritorno:** `float` o `None`

```python
# Esempio struttura input
field = {
    "list": {
        "1699945200": "22.5",
        "1699948800": "23.1",
        "1699952400": "null"
    }
}
mean = s.get_field_mean(field)  # 22.8
```


###### `create_CSV_file(self, DETECTIONS, net_name, category)`

Genera file CSV con dati aggregati.

**Parametri:**

- `DETECTIONS` (list[dict]): Lista record da salvare
- `net_name` (str): Nome rete
- `category` (str): Categoria dati (es. "wireless_detections", "weather_detections")

**Output:** `csv/[NET_NAME]/[CATEGORY]_[NET_NAME]_[DATA].csv`


###### `process_network_devices(self)`

Organizza dispositivi raggruppandoli per rete di appartenenza.

**Popola:** `NETWORK_DEVICES`


###### `process_weatherstation_devices(self)`

Integra centraline meteo Ecowitt nel sistema di gestione dispositivi.

**Mapping:**

- Nome dispositivo Ecowitt: `AI-WS-[NOME_RETE]`
- Associazione a rete Meraki tramite nome

**Aggiorna:** `DEVICES` con entry tipo "weatherstation"


##### Funzioni di Servizio

###### `get_field(self, id, field)`

Recupera un campo specifico di un dispositivo.

**Parametri:**

- `id` (str): Seriale dispositivo
- `field` (str): Nome campo da recuperare

**Campi disponibili:**

- `SERIAL`, `NUMBER`, `DEVICE_MODEL`, `DEVICE_PRODUCT`
- `MAC_ADDRESS`, `NETWORK_ID`, `HAS_A_UPLINK`, `DEVICE_UPLINK`

**Ritorno:** Valore del campo o `None`

```python
mac = s.get_field("Q2XX-XXXX-XXXX", "MAC_ADDRESS")
```

###### `get_devices_serial(self, network_id, DEVICE_LIST, device_type)`

Estrae seriali di dispositivi di un tipo specifico da una lista.

**Parametri:**

- `network_id` (str): ID rete
- `DEVICE_LIST` (dict): Dizionario dispositivi raggruppati
- `device_type` (str): Tipo dispositivo (es. "camera")

**Ritorno:** `list[str]` - Lista seriali


###### `get_devices(self)`

**Ritorno:** `dict` - Copia di `DEVICES`


###### `get_uplink_devices(self)`

**Ritorno:** `dict` - Copia di `UPLINK_DEVICES`


###### `get_network_devices(self)`

**Ritorno:** `list[dict]` - Copia di `NETWORK_DEVICES`


###### `get_network_name(self, net_id)`

Converte ID rete in nome leggibile.

**Parametri:**

- `net_id` (str): ID rete Meraki

**Ritorno:** `str` - Nome rete o `None`

```python
name = s.get_network_name("L_575897802350018094")  # "THU"
```


###### `get_network_id(self, net_name)`

Converte nome rete in ID Meraki.

**Parametri:**

- `net_name` (str): Nome rete

**Ritorno:** `str` - ID rete o `None`

```python
id = s.get_network_id("THU")  # "L_575897802350018094"
```

---

#### `get_device_info(self, device_type)`

Raggruppa dispositivi di una specifica tipologia per rete.

**Parametri:**

- `device_type` (str): Tipo dispositivo (es. "camera", "wireless", "weatherstation")

**Ritorno:** `dict` - Struttura:

```python
{
    "THU": {
        "net_id": "L_575897802350018094",
        "camera": ["Q2XX-XXXX-XXXX", ...]
    },
    ...
}
```

**Uso interno:**

```python
NET_CAMERAS = get_device_info("camera")
NET_WEATHERSTATION = get_device_info("weatherstation")
```

---

#### Pattern di Utilizzo

##### Caso d'uso 1: Raccolta Completa Dati Giornalieri

```python
from merakiSensors import sensors

# Inizializzazione
s = sensors()

# Raccolta foto
s.SENSE_photo_all_net()

# Raccolta connessioni wireless
s.SENSE_calculate_connections_all_net()

# Raccolta dati meteo
s.SENSE_calculate_weather_conditions_all_net()

# I CSV sono salvati automaticamente in csv/[RETE]/
```

##### Caso d'uso 2: Monitoraggio Rete Specifica

```python
s = sensors()

# Ottieni ID rete
net_id = s.get_network_id("THU")

# Raccogli dati solo per questa rete
s.SENSE_photo_single_net(net_id)
connections = s.SENSE_calculate_connections(net_id)
weather = s.SENSE_calculate_weather_conditions(net_id, 266643)
```

##### Caso d'uso 3: Interrogazione Dispositivi

```python
s = sensors()

# Ottieni tutti i dispositivi
devices = s.get_devices()

# Ottieni camere di una rete
cameras = s.NET_CAMERAS["THU"]["camera"]

# Ottieni MAC di un dispositivo
mac = s.get_field("Q2XX-XXXX-XXXX", "MAC_ADDRESS")
```


#### Altri dettagli



##### Threading MQTT

La funzionalità MQTT è attualmente sperimentale e non completamente integrata. L'attributo `mqtt_threads` è presente ma non utilizzato.


##### Conformità GDPR

I MAC address raccolti sono pseudonimizzati (utilizzati solo per conteggi aggregati). Nessun dato personale identificabile viene memorizzato nei CSV finali.

### crane_movement_recognition.py

#### Panoramica

crane_movement_recognition.py è il modulo di **analisi intelligente delle immagini** che utilizza l'API di OpenAI (GPT-4 Vision) per rilevare e quantificare i movimenti della gru da torre presente nei cantieri monitorati. Questo componente implementa un sistema di Computer Vision basato su Large Language Model per automatizzare il conteggio dei movimenti della gru, fornendo dati cruciali per il monitoraggio dell'attività di cantiere.

#### Scopo del Modulo

Il modulo serve a:

1. **Analisi Automatica Immagini**: Rilevamento movimento gru senza intervento umano
2. **Quantificazione Attività**: Conteggio preciso movimenti per fascia oraria
3. **Correlazione Meteo**: Associazione condizioni atmosferiche all'attività di cantiere
4. **Generazione Report**: Produzione CSV strutturati per analisi successive
5. **Riduzione Costi Monitoraggio**: Eliminazione necessità di supervisione manuale

## Variabili Globali

##### Credenziali e Client

```python
client = OpenAI(api_key="SegretoDiStato")
```

| Variabile | Tipo | Descrizione |
|-----------|------|-------------|
| `client` | `OpenAI` | Istanza client OpenAI per chiamate API |

⚠️ **NOTA SICUREZZA**: La chiave API è hardcoded come placeholder. In produzione utilizzare variabili d'ambiente.

##### Directory e Date di Test

```python
images_directory = "camera_snapshot"
giornata_festiva = date.fromisoformat('2025-07-05')
giornata_lavorativa = date.fromisoformat('2025-07-07')
```

| Variabile | Valore | Descrizione |
|-----------|--------|-------------|
| `images_directory` | `"camera_snapshot"` | Directory radice snapshot |
| `giornata_festiva` | `date(2025, 7, 5)` | Data test (nessun lavoro) |
| `giornata_lavorativa` | `date(2025, 7, 7)` | Data test (cantiere attivo) |

##### Fasce Orarie

###### Produzione (REAL_TIMEFRAMES)

```python
real_timeframes = [
    (time.fromisoformat('06:00:00'), time.fromisoformat('07:59:59')),
    (time.fromisoformat('08:00:00'), time.fromisoformat('09:59:59')),
    (time.fromisoformat('10:00:00'), time.fromisoformat('11:59:59')),
    (time.fromisoformat('12:00:00'), time.fromisoformat('13:59:59')),
    (time.fromisoformat('14:00:00'), time.fromisoformat('15:59:59')),
    (time.fromisoformat('16:00:00'), time.fromisoformat('17:59:59')),
    (time.fromisoformat('18:00:00'), time.fromisoformat('20:00:00'))
]
```

**7 fasce orarie**: 6:00-20:00 (orario lavorativo standard cantiere)

###### Testing (TEST_TIMEFRAMES)

```python
test_timeframes = [
    (time.fromisoformat('14:00:00'), time.fromisoformat('14:59:59')),
    (time.fromisoformat('15:00:00'), time.fromisoformat('15:59:59'))
]
```

**2 fasce ridotte**: per testing rapido API

##### Template CSV

```python
csv_template = 'Day Timeframe WasCraneUsed NumberOfMoves Weather \n DATE FRAME USED MOVE CONDITION'
```

Struttura output CSV con placeholder per parsing risposta GPT-4.

---

#### Classi

##### `class Image`

Rappresenta una singola fotografia con metadati estratti.

###### Attributi

| Attributo | Tipo | Descrizione |
|-----------|------|-------------|
| `path` | `str` | Path completo file immagine |
| `date` | `date` | Data scatto estratta da filename |
| `time` | `time` | Ora scatto estratta da filename |
| `base64_encoding` | `str` | Encoding base64 per API |

###### Metodi

**`__init__(self, path: str, date: date, time: time, base64_encoding: str)`**

Costruttore classe Image.

**Esempio:**
```python
img = Image(
    path="camera_snapshot/THU/camera_0/snapshot_20251114_153045.jpg",
    date=date(2025, 11, 14),
    time=time(15, 30, 45),
    base64_encoding="iVBORw0KGgoAAAANS..."
)
```

---

#### Funzioni Principali

##### `encode_image(image_path: str) -> str`

Converte immagine JPEG in stringa base64 per invio API OpenAI.

**Parametri:**
- `image_path` (str): Path assoluto o relativo file immagine

**Ritorno:** `str` - Stringa base64 dell'immagine

**Processo:**
1. Apertura file in modalità binaria (`rb`)
2. Encoding base64
3. Decodifica in ASCII per compatibilità JSON

**Esempio:**
```python
encoded = encode_image("camera_snapshot/THU/camera_0/photo.jpg")
# Output: "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBD..."
```

**Utilizzo Interno:**
Chiamata da `create_image_list()` per preparare payload API.

---

##### `create_image_list(images_directory: str) -> List[Image]`

Scansiona directory snapshot e crea lista oggetti `Image` con encoding base64.

**Parametri:**
- `images_directory` (str): Directory radice (es. "camera_snapshot")

**Ritorno:** `List[Image]` - Lista oggetti Image ordinati cronologicamente

**Struttura Directory Attesa:**
```
camera_snapshot/
├── THU/
│   └── camera_0/
│       ├── camera_Q2XX_snapshot_20251114_063000.jpg
│       ├── camera_Q2XX_snapshot_20251114_083000.jpg
│       └── ...
├── B12/
└── HOM_BIS/
```

**Processo:**
1. `os.listdir()` per enumerare file
2. Parsing filename per estrarre data/ora
3. Encoding base64 di ogni immagine
4. Creazione oggetto `Image` per ciascuna

**Formato Filename:** `camera_[SERIAL]_snapshot_[YYYYMMDD]_[HHMMSS].jpg`

**Esempio:**
```python
images = create_image_list("camera_snapshot/THU/camera_0")
# Output: [
#   Image(path="...", date=date(2025,11,14), time=time(6,30,0), ...),
#   Image(path="...", date=date(2025,11,14), time=time(8,30,0), ...),
#   ...
# ]
```

**Gestione Errori:**
- Salta file con naming non conforme
- Ignora file non-immagine

---

##### `organize_photos_by_date(images: List[Image]) -> Dict[date, List[Image]]`

Raggruppa foto per giornata.

**Parametri:**
- `images` (List[Image]): Lista output da `create_image_list()`

**Ritorno:** `Dict[date, List[Image]]` - Dizionario giorno → lista foto

**Struttura Output:**
```python
{
    date(2025, 11, 14): [Image(...), Image(...), ...],
    date(2025, 11, 15): [Image(...), Image(...), ...],
}
```

**Ordinamento:**
- Foto ordinate per timestamp all'interno di ogni giorno

**Esempio:**
```python
images = create_image_list("camera_snapshot")
by_date = organize_photos_by_date(images)

# Accesso foto del 14 novembre
photos_nov14 = by_date[date(2025, 11, 14)]
print(f"Foto del 14/11: {len(photos_nov14)}")
```

---

##### `organize_photos_by_timestamp(date_organized_photos: Dict) -> Dict`

Suddivide foto giornaliere in fasce orarie predefinite.

**Parametri:**
- `date_organized_photos` (Dict): Output di `organize_photos_by_date()`

**Ritorno:** `Dict[date, Dict[Tuple[time, time], List[Image]]]` - Struttura annidata

**Struttura Output:**
```python
{
    date(2025, 11, 14): {
        (time(6,0,0), time(7,59,59)): [Image(...), Image(...)],
        (time(8,0,0), time(9,59,59)): [Image(...), Image(...), Image(...)],
        ...
    },
    date(2025, 11, 15): {...}
}
```

**Logica Assegnazione Fascia:**
```python
for image in day_images:
    for (start_time, end_time) in timeframes:
        if start_time <= image.time <= end_time:
            # Assegna a questa fascia
```

**Esempio:**
```python
by_date = organize_photos_by_date(images)
by_timeframe = organize_photos_by_timestamp(by_date)

# Accesso foto fascia 6:00-7:59 del 14 novembre
morning_photos = by_timeframe[date(2025,11,14)][(time(6,0,0), time(7,59,59))]
print(f"Foto mattina presto: {len(morning_photos)}")
```

---

##### `create_request_list(day: date, timeframes_dict: Dict) -> List[Dict]`

Costruisce payload per API OpenAI con immagini e prompt per ogni fascia oraria.

**Parametri:**
- `day` (date): Giornata da analizzare
- `timeframes_dict` (Dict): Output di `organize_photos_by_timestamp()`

**Ritorno:** `List[Dict]` - Lista messaggi per chiamata API Chat Completion

**Struttura Messaggio:**
```python
[
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Analyze these construction site images..."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64,/9j/4AAQ...",
                    "detail": "low"
                }
            },
            # ... altre immagini della fascia ...
        ]
    },
    # ... messaggi per altre fasce orarie ...
]
```

**Prompt Inviato:**
```text
Analyze these construction site images from [START_TIME] to [END_TIME] 
on [DATE]. Determine:

1. Was the tower crane actively used? (Yes/No)
2. Estimate total crane movements (0 if unused)
3. Weather conditions observed

Response format:
[DATE] [START-END] [Yes/No] [NumberOfMoves] [WeatherCondition]

Example: 2025-11-14 06:00-07:59 Yes 15 Sunny
```

**Parametri API:**
- `detail: "low"`: Riduce costi elaborazione (sufficiente per rilevamento gru)
- Encoding: `data:image/jpeg;base64,`

**Esempio:**
```python
by_timeframe = organize_photos_by_timestamp(by_date)
requests = create_request_list(date(2025,11,14), by_timeframe)

print(f"Messaggi generati: {len(requests)}")  # 7 (uno per fascia)
```

---

##### `generate_chatGPT_response(day: date, timeframes_dict: Dict) -> Tuple[str, str]`

Invia richieste a GPT-4 Vision e genera risposta + file CSV.

**Parametri:**
- `day` (date): Giornata da analizzare
- `timeframes_dict` (Dict): Foto organizzate per fascia

**Ritorno:** `Tuple[str, str]`
- `[0]`: Risposta testuale GPT-4
- `[1]`: Path file CSV generato

**Configurazione API:**
```python
response = client.chat.completions.create(
    model="gpt-4o-mini",  # Modello con supporto visione
    messages=requests,
    max_tokens=300,       # Limite per risposta concisa
    temperature=0.2       # Determinismo alto
)
```

**Parametri Ottimizzazione:**
- `max_tokens=300`: Sufficiente per 7 righe CSV
- `temperature=0.2`: Riduce variabilità nelle risposte (consistenza)

**Formato Risposta Attesa:**
```
2025-11-14 06:00-07:59 Yes 12 Sunny
2025-11-14 08:00-09:59 Yes 25 Cloudy
2025-11-14 10:00-11:59 Yes 18 Sunny
2025-11-14 12:00-13:59 No 0 Rainy
2025-11-14 14:00-15:59 Yes 8 PartlyCloudy
2025-11-14 16:00-17:59 Yes 15 Sunny
2025-11-14 18:00-20:00 No 0 Dusk
```

**Generazione CSV:**
1. Template iniziale con header
2. Sostituzione placeholder `DATE FRAME USED MOVE CONDITION`
3. Inserimento risposta GPT-4
4. Salvataggio in `test_case_response.csv`

**Esempio Output CSV:**
```csv
Day Timeframe WasCraneUsed NumberOfMoves Weather
2025-11-14 06:00-07:59 Yes 12 Sunny
2025-11-14 08:00-09:59 Yes 25 Cloudy
2025-11-14 10:00-11:59 Yes 18 Sunny
2025-11-14 12:00-13:59 No 0 Rainy
2025-11-14 14:00-15:59 Yes 8 PartlyCloudy
2025-11-14 16:00-17:59 Yes 15 Sunny
2025-11-14 18:00-20:00 No 0 Dusk
```

**Utilizzo:**
```python
by_timeframe = organize_photos_by_timestamp(by_date)
response_text, csv_path = generate_chatGPT_response(
    date(2025, 11, 14),
    by_timeframe
)

print(f"Risposta GPT-4:\n{response_text}")
print(f"CSV salvato in: {csv_path}")
```

**Gestione Errori:**
```python
try:
    response = client.chat.completions.create(...)
except openai.APIError as e:
    print(f"Errore API OpenAI: {e}")
except openai.RateLimitError as e:
    print(f"Rate limit raggiunto: {e}")
```

---

##### `image_detection(day: date, image_folder: str, network: str, camera: str)`

**Funzione wrapper principale** per orchestrazione completa analisi.

**Parametri:**

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `day` | `date` | Data da analizzare (YYYY-MM-DD) |
| `image_folder` | `str` | Directory radice snapshot |
| `network` | `str` | Nome rete (es. "THU", "B12") |
| `camera` | `str` | ID camera (es. "camera_0") |

**Workflow Completo:**

```python
def image_detection(day, image_folder, network, camera):
    # 1. Costruisce path specifico
    full_path = f"{image_folder}/{network}/{camera}"
    
    # 2. Carica e organizza immagini
    images = create_image_list(full_path)
    by_date = organize_photos_by_date(images)
    by_timeframe = organize_photos_by_timestamp(by_date)
    
    # 3. Genera risposta GPT-4 e CSV
    response, csv_path = generate_chatGPT_response(day, by_timeframe)
    
    # 4. Salva CSV in directory strutturata
    os.makedirs("csv", exist_ok=True)
    final_csv = f"csv/image_analysis_{network}_{camera}_{day}.csv"
    shutil.move(csv_path, final_csv)
    
    return final_csv
```

**Output:** Path CSV finale in `csv/image_analysis_[RETE]_[CAMERA]_[DATA].csv`

**Esempio Utilizzo da calcolo_giornata.py:**
```python
from crane_movement_recognition import image_detection
from datetime import date

# Analizza foto rete THU, camera 0, giorno 14 novembre
csv_file = image_detection(
    day=date(2025, 11, 14),
    image_folder="camera_snapshot",
    network="THU",
    camera="camera_0"
)

print(f"Analisi completata: {csv_file}")
# Output: "Analisi completata: csv/image_analysis_THU_camera_0_2025-11-14.csv"
```

---

#### Integrazione con il Sistema

##### Chiamata da calcolo_giornata.py

```python
from crane_movement_recognition import image_detection
from datetime import datetime

def genera_csv_gru(day, rete, camera="camera_0"):
    """
    Genera CSV di analisi gru per la rete indicata.
    """
    # Chiama modulo di riconoscimento
    image_detection(day, "camera_snapshot", rete, camera)
    
    # Legge risultati
    csv_filename = f"csv/image_analysis_{rete}_{camera}_{day}.csv"
    
    with open(csv_filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    return rows

# Utilizzo
giorno_corrente = datetime.now().date()
dati_gru_thu = genera_csv_gru(giorno_corrente, "THU")
dati_gru_b12 = genera_csv_gru(giorno_corrente, "B12")
```

##### Integrazione con Database

```python
from crane_movement_recognition import image_detection

def parse_crane_csv(csv_path: str) -> Dict:
    """
    Legge CSV generato da image_detection.
    """
    crane_data = {}
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['Day'], row['Timeframe'])
            crane_data[key] = {
                'used': row['WasCraneUsed'],
                'moves': int(row['NumberOfMoves']),
                'weather': row['Weather']
            }
    
    return crane_data
```

---

#### Prompt Engineering

##### Struttura Prompt Utilizzato

Il prompt inviato a GPT-4 Vision è progettato per massimizzare precisione e strutturazione output.

###### Componenti Prompt

**1. Contesto Temporale:**
```
Analyze these construction site images from [START_TIME] to [END_TIME] on [DATE].
```
Fornisce frame temporale per contestualizzazione.

**2. Task Specifici:**
```
Determine:
1. Was the tower crane actively used? (Yes/No)
2. Estimate total crane movements (0 if unused)
3. Weather conditions observed
```
Tre task chiari e misurabili.

**3. Formato Output:**
```
Response format:
[DATE] [START-END] [Yes/No] [NumberOfMoves] [WeatherCondition]

Example: 2025-11-14 06:00-07:59 Yes 15 Sunny
```
Esempio concreto per guidare struttura risposta.

###### Strategie Ottimizzazione

| Strategia | Implementazione | Beneficio |
|-----------|-----------------|-----------|
| **Few-shot learning** | Esempio risposta incluso | Consistenza formato |
| **Temperature bassa** | 0.2 | Determinismo alto |
| **Token limit** | 300 max | Risposte concise |
| **Detail: low** | Immagini downscaled | Riduzione costi |
| **Specificity** | "tower crane" vs "crane" | Disambiguazione |

##### Esempi Risposte GPT-4

###### Giornata Lavorativa Intensa

**Input:** 42 foto da 6:00 a 20:00 (6 foto/fascia)

**Output:**
```
2025-11-14 06:00-07:59 Yes 18 ClearSky
2025-11-14 08:00-09:59 Yes 35 Sunny
2025-11-14 10:00-11:59 Yes 42 Sunny
2025-11-14 12:00-13:59 No 0 Sunny
2025-11-14 14:00-15:59 Yes 28 PartlyCloudy
2025-11-14 16:00-17:59 Yes 22 Cloudy
2025-11-14 18:00-20:00 No 0 Dusk
```

**Analisi:**
- Pausa pranzo rilevata (12-14)
- Diminuzione attività verso sera
- Tracking condizioni meteo

###### Giornata Festiva/Maltempo

**Input:** 21 foto da 6:00 a 20:00 (3 foto/fascia)

**Output:**
```
2025-11-14 06:00-07:59 No 0 Rainy
2025-11-14 08:00-09:59 No 0 HeavyRain
2025-11-14 10:00-11:59 No 0 Rainy
2025-11-14 12:00-13:59 No 0 Overcast
2025-11-14 14:00-15:59 No 0 LightRain
2025-11-14 16:00-17:59 No 0 Cloudy
2025-11-14 18:00-20:00 No 0 Dusk
```

**Analisi:**
- Nessuna attività rilevata
- Condizioni meteo avverse registrate

---


### calcolo_giornata.py

#### Panoramica

calcolo_giornata.py è il **modulo di orchestrazione centrale** del sistema ACSM che coordina la raccolta completa dei dati giornalieri da tutte le fonti (fotografie, wireless, meteo, analisi gru) e li aggrega in CSV unificati pronti per la visualizzazione in dashboard e PowerBI.

#### Scopo del Modulo

Il modulo serve a:

1. **Orchestrazione Completa**: Coordina tutti i moduli di raccolta dati in un'unica esecuzione
2. **Aggregazione Multi-Fonte**: Unifica dati da Meraki, Ecowitt e OpenAI in singoli CSV per rete
3. **CSV Finale PowerBI**: Genera file strutturati in `dati_giornata/` per import immediato
4. **Schedulazione Automatica**: Progettato per esecuzione cron giornaliera (6:00 e 20:00)
5. **Trigger Dashboard**: Callable da Streamlit per generazione on-demand

---


#### Componenti Implementati

##### 1. Funzione Principale: `calcolo_giornata_csv()`

```python
def calcolo_giornata_csv():
    """
    Orchestrazione completa raccolta dati giornalieri.
    """
    # Inizializzazione
    s = sensors()
    today = date.today()
    
    # Step 1-4: Raccolta dati raw
    s.SENSE_photo_all_net()
    s.SENSE_calculate_connections_all_net()
    s.SENSE_calculate_weather_conditions_all_net()
    
    # Step 5: Analisi gru per ogni rete
    networks = ["THU", "B12", "HOM_BIS"]
    for network in networks:
        image_detection(today, "camera_snapshot", network, "camera_0")
    
    # Step 6-7: Merge e salvataggio
    for network in networks:
        merge_network_data(network, today)
```

**Caratteristiche:**
- **Atomicità**: Esegue tutte le operazioni in sequenza (no parallelizzazione)
- **Idempotenza**: Può essere rieseguita per stessa data (overwrite CSV)
- **Error Handling**: Continua anche se una rete fallisce (try/except per network)

---

##### 2. Funzione di Aggregazione: `merge_network_data(network, date)`

```python
def merge_network_data(network: str, date: date):
    """
    Aggrega CSV sparsi in un unico file finale per rete.
    """
    # Path CSV input
    crane_csv = f"csv/image_analysis_{network}_camera_0_{date}.csv"
    wireless_csv = f"csv/{network}/wireless_detections_{network}_{date}.csv"
    weather_csv = f"csv/{network}/weather_detections_{network}_{date}.csv"
    
    # Caricamento DataFrames
    df_crane = pd.read_csv(crane_csv)
    df_wireless = pd.read_csv(wireless_csv)
    df_weather = pd.read_csv(weather_csv)
    
    # Normalizzazione colonne Timeslot
    df_crane['Timeslot'] = df_crane['Timeframe'].str.replace(' ', '')
    df_wireless['Timeslot'] = df_wireless['Timeslot'].str.strip()
    df_weather['Timeslot'] = df_weather['Timeslot'].str.strip()
    
    # Merge sequenziali su Timeslot
    df_merged = df_crane.merge(df_wireless, on='Timeslot', how='outer')
    df_merged = df_merged.merge(df_weather, on='Timeslot', how='outer')
    
    # Ridenominazione colonne per PowerBI
    df_merged.rename(columns={
        'WasCraneUsed': 'Crane_Used',
        'NumberOfMoves': 'Crane_Moves',
        'DeviceConnected': 'Wireless_Devices',
        'temperature(℃)': 'Temperature',
        'humidity(%)': 'Humidity',
        'feels_like(℃)': 'Feels_Like',
        'app_temp(℃)': 'App_Temp',
        'dew_point(℃)': 'Dew_Point'
    }, inplace=True)
    
    # Selezione e ordinamento colonne
    columns_order = [
        'Timeslot', 'Crane_Used', 'Crane_Moves', 
        'Wireless_Devices', 'Temperature', 'Humidity',
        'Feels_Like', 'App_Temp', 'Dew_Point', 'Weather'
    ]
    df_final = df_merged[columns_order]
    
    # Salvataggio
    output_path = f"dati_giornata/dati_giornata_{network}_{date}.csv"
    os.makedirs("dati_giornata", exist_ok=True)
    df_final.to_csv(output_path, index=False)
    
    print(f"✅ CSV finale salvato: {output_path}")
```

**Logica Merge:**
- **Join Type**: `OUTER JOIN` per preservare tutte le fasce orarie anche se dati parziali
- **Key**: Colonna `Timeslot` (formato "HH:MM-HH:MM")
- **Gestione Missing**: Celle vuote per dati mancanti (null/NaN)

---

##### 3. Struttura CSV Finale

**Path Output:** `dati_giornata/dati_giornata_[RETE]_[YYYYMMDD].csv`

**Esempio:** `dati_giornata/dati_giornata_THU_20251114.csv`

**Schema Colonne:**

| Colonna | Tipo | Fonte | Descrizione |
|---------|------|-------|-------------|
| `Timeslot` | `str` | Merge Key | Fascia oraria (06:00-07:59, ..., 18:00-20:00) |
| `Crane_Used` | `str` | GPT-4 Vision | "Yes"/"No" utilizzo gru |
| `Crane_Moves` | `int` | GPT-4 Vision | Numero movimenti stimati |
| `Wireless_Devices` | `int` | Meraki API | Conteggio dispositivi wireless |
| `Temperature` | `float` | Ecowitt API | Temperatura reale (°C) |
| `Humidity` | `float` | Ecowitt API | Umidità relativa (%) |
| `Feels_Like` | `float` | Ecowitt API | Temperatura percepita (°C) |
| `App_Temp` | `float` | Ecowitt API | Temperatura apparente (°C) |
| `Dew_Point` | `float` | Ecowitt API | Punto di rugiada (°C) |
| `Weather` | `str` | GPT-4 Vision | Condizioni meteo osservate |

**Esempio Record:**
```csv
Timeslot,Crane_Used,Crane_Moves,Wireless_Devices,Temperature,Humidity,Feels_Like,App_Temp,Dew_Point,Weather
06:00-07:59,Yes,12,8,18.5,65,17.8,18.2,12.3,Sunny
08:00-09:59,Yes,25,15,20.1,60,19.5,19.8,13.1,Cloudy
10:00-11:59,Yes,18,22,22.3,55,21.8,22.0,13.8,PartlyCloudy
12:00-13:59,No,0,10,23.5,50,23.0,23.2,14.2,Sunny
14:00-15:59,Yes,8,18,24.1,48,23.8,23.9,14.5,Sunny
16:00-17:59,Yes,15,12,23.0,52,22.5,22.7,14.0,Cloudy
18:00-20:00,No,0,5,21.5,58,21.0,21.2,13.5,Dusk
```

---

#### Integrazione con Altri Moduli

##### Chiamata da Dashboard Streamlit

```python
from calcolo_giornata import calcolo_giornata_csv

if st.button("⚙️ Calcola Giornata"):
    with st.spinner("Elaborazione in corso..."):
        calcolo_giornata_csv()
    st.success("✅ Dati giornata calcolati!")
    st.rerun()  # Refresh per caricare nuovi CSV
```

##### Schedulazione Cron (Automatica)

```bash
# Crontab entry per esecuzione automatica

# Mattina: avvio raccolta foto (6:00)
0 6 * * 1-5 /usr/bin/python3 /path/to/photoscript.py >> /var/log/acsm.log 2>&1

# Sera: stop foto + calcolo giornata (20:00)
0 20 * * 1-5 /usr/bin/python3 /path/to/photoscript.py stop >> /var/log/acsm.log 2>&1
5 20 * * 1-5 /usr/bin/python3 /path/to/calcolo_giornata.py >> /var/log/acsm.log 2>&1
```

**Logica Schedulazione:**
- **6:00**: Avvio photoscript (raccolta continua ogni 30s)
- **20:00**: Stop photoscript
- **20:05**: Esecuzione `calcolo_giornata_csv()` per aggregare dati giornata

---


#### Utilizzo

##### Esecuzione Manuale

```bash
# Da terminale
python3 calcolo_giornata.py

# Output atteso
📸 Raccolta foto completata
📡 Dati wireless raccolti per THU, B12, HOM_BIS
🌤️ Dati meteo raccolti per THU, B12, HOM_BIS
🏗️ Analisi gru THU completata
🏗️ Analisi gru B12 completata
🏗️ Analisi gru HOM_BIS completata
✅ CSV finale salvato: dati_giornata/dati_giornata_THU_20251114.csv
✅ CSV finale salvato: dati_giornata/dati_giornata_B12_20251114.csv
✅ CSV finale salvato: dati_giornata/dati_giornata_HOM_BIS_20251114.csv
```



### dashboard.py


#### Panoramica

dashboard.py è l'**interfaccia web interattiva** per la visualizzazione e l'analisi dei dati di cantiere raccolti dal sistema ACSM. Implementato con Streamlit, fornisce una dashboard dinamica per monitorare movimenti gru, connessioni wireless e condizioni meteo in formato tabellare e grafico.

#### Scopo del Modulo

Il modulo serve a:

1. **Visualizzazione Dati**: Interfaccia user-friendly per esplorare dataset giornalieri
2. **Trigger Calcolo**: Bottone per generare CSV aggregati on-demand
3. **Analisi Grafica**: Chart interattivi per trend temporali
4. **Export PowerBI**: CSV pre-formattati per importazione in Power BI
5. **Monitoring Operativo**: Dashboard accessibile da browser per supervisori cantiere



#### Componenti Implementati

##### 1. Header e Titolo

```python
st.title("📊 Dashboard Monitoraggio Giornata")
```

**Output:** Intestazione principale con emoji per visual appeal

---

##### 2. Trigger Calcolo Giornata

```python
if st.button("⚙️ Calcola Giornata"):
    calcolo_giornata_csv()
    st.success("Dati giornata calcolati!")
```

###### Funzionalità

| Elemento | Tipo | Descrizione |
|----------|------|-------------|
| **Button** | `st.button()` | Widget interattivo Streamlit |
| **Action** | `calcolo_giornata_csv()` | Import da calcolo_giornata.py |
| **Feedback** | `st.success()` | Toast notifica verde con messaggio |

**Comportamento:**
1. Utente clicca bottone "⚙️ Calcola Giornata"
2. Esecuzione `calcolo_giornata_csv()` (vedi modulo dedicato)
3. Generazione CSV in `dati_giornata/` con nome pattern `dati_giornata_[RETE]_[DATA].csv`
4. Notifica successo operazione

**Workflow Sottostante:**
```python
# In calcolo_giornata.py (chiamato dal bottone)
def calcolo_giornata_csv():
    s = sensors()
    s.SENSE_photo_all_net()                        # Foto
    s.SENSE_calculate_connections_all_net()        # Wireless
    s.SENSE_calculate_weather_conditions_all_net() # Meteo
    
    # Analisi gru per ogni rete
    for network in ["THU", "B12", "HOM_BIS"]:
        image_detection(date.today(), "camera_snapshot", network, "camera_0")
    
    # Merge CSV e salvataggio in dati_giornata/
    merge_and_save_csv()
```

---

##### 3. Selezione Dataset

```python
st.header("📂 Ultimi dati disponibili")

csv_files = sorted(glob("dati_giornata/*.csv"), reverse=True)

if not csv_files:
    st.warning("Nessun file CSV trovato in dati_giornata/")
else:
    selected_file = st.selectbox("Seleziona dataset", csv_files)
```

###### Funzionalità

**Scansione Directory:**
- `glob("dati_giornata/*.csv")`: Trova tutti i CSV
- `sorted(..., reverse=True)`: Ordina per data decrescente (più recenti primi)

**Gestione Casi:**

| Condizione | Output |
|------------|--------|
| **CSV presenti** | Dropdown con lista file |
| **Directory vuota** | Warning arancione "Nessun file CSV trovato" |

**Esempio Dropdown:**
```
Seleziona dataset
├─ dati_giornata_THU_20251114.csv     ← Più recente
├─ dati_giornata_B12_20251114.csv
├─ dati_giornata_HOM_BIS_20251113.csv
└─ dati_giornata_THU_20251113.csv
```

---

##### 4. Anteprima Tabellare

```python
df = pd.read_csv(selected_file)

st.subheader(f"Anteprima dati: {os.path.basename(selected_file)}")
st.dataframe(df)
```

###### Funzionalità

**Caricamento CSV:**
- Parsing automatico con Pandas
- Inferenza tipi colonne

**Widget `st.dataframe()`:**
- Tabella interattiva scrollabile
- Ordinamento colonne con click header
- Ricerca inline (se abilitato)

**Esempio Output:**

```
Anteprima dati: dati_giornata_THU_20251114.csv

| Timeslot      | Crane_Used | Crane_Moves | Wireless_Devices | Temperature | Humidity | Feels_Like | App_Temp | Dew_Point |
|---------------|------------|-------------|------------------|-------------|----------|------------|----------|-----------|
| 06:00-07:59   | Yes        | 12          | 8                | 18.5        | 65       | 17.8       | 18.2     | 12.3      |
| 08:00-09:59   | Yes        | 25          | 15               | 20.1        | 60       | 19.5       | 19.8     | 13.1      |
| 10:00-11:59   | Yes        | 18          | 22               | 22.3        | 55       | 21.8       | 22.0     | 13.8      |
| ...           | ...        | ...         | ...              | ...         | ...      | ...        | ...      | ...       |
```

**Struttura CSV Attesa:**

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `Timeslot` | `str` | Fascia oraria (HH:MM-HH:MM) |
| `Crane_Used` | `str` | "Yes"/"No" |
| `Crane_Moves` | `int` | Numero movimenti gru |
| `Wireless_Devices` | `int` | Conteggio dispositivi connessi |
| `Temperature` | `float` | Temperatura reale (°C) |
| `Humidity` | `float` | Umidità relativa (%) |
| `Feels_Like` | `float` | Temperatura percepita (°C) |
| `App_Temp` | `float` | Temperatura apparente (°C) |
| `Dew_Point` | `float` | Punto di rugiada (°C) |

---

##### 5. Visualizzazioni Grafiche

###### Layout a Colonne

```python
st.header("Analisi")

col1, col2 = st.columns(2)
```

**Struttura:** 2 colonne affiancate per layout responsive

---

###### Chart 1: Movimenti Gru

```python
with col1:
    st.subheader("Movimenti Gru")
    st.line_chart(df.set_index("Timeslot")["Crane_Moves"])
```

**Tipo:** Line chart singola serie

**Configurazione:**
- **X-axis:** `Timeslot` (impostato come index)
- **Y-axis:** `Crane_Moves`
- **Stile:** Linea continua con marker punti

**Esempio Output:**

```
Movimenti Gru
     40 │                    ●
        │                   ╱ ╲
     30 │                  ╱   ╲
        │                 ╱     ╲
     20 │          ●     ╱       ●
        │         ╱ ╲   ╱         ╲
     10 │    ●   ╱   ╲ ╱           ●
        │   ╱ ╲ ╱     ●             ╲
      0 │  ╱   ●                     ●
        └─────────────────────────────────
          06:00 08:00 10:00 12:00 14:00 16:00 18:00
```

**Insights:**
- Picco attività mattino (8-10)
- Pausa pranzo (12-14)
- Diminuzione pomeridiana

---

###### Chart 2: Dispositivi Wireless

```python
with col2:
    st.subheader("Dispositivi Wireless")
    st.line_chart(df.set_index("Timeslot")["Wireless_Devices"])
```

**Tipo:** Line chart singola serie

**Configurazione:**
- **X-axis:** `Timeslot`
- **Y-axis:** `Wireless_Devices`

**Esempio Output:**

```
Dispositivi Wireless
     30 │              ●───●
        │             ╱     ╲
     20 │        ●───╱       ╲
        │       ╱             ╲
     10 │  ●───╱               ●───●
        │                           ╲
      0 │                            ●
        └─────────────────────────────────
          06:00 08:00 10:00 12:00 14:00 16:00 18:00
```

**Insights:**
- Correlazione con orari lavorativi
- Possibile stima presenze operai

---

###### Chart 3: Condizioni Meteo

```python
st.subheader("Meteo")
st.line_chart(df.set_index("Timeslot")[["Temperature", "Feels_Like", "App_Temp"]])
```

**Tipo:** Multi-line chart (3 serie)

**Configurazione:**
- **X-axis:** `Timeslot`
- **Y-axis:** 3 metriche temperature
- **Legenda:** Automatica per distinguere serie

**Esempio Output:**

```
Meteo
     30°C │
          │         ●────●────● Temperature
          │        ╱
     25°C │   ●───╱   ●────●   Feels_Like
          │      ╱   ╱
     20°C │ ●───╱   ╱          App_Temp
          │        ╱
     15°C │                    
          └─────────────────────────────────
            06:00 08:00 10:00 12:00 14:00 16:00 18:00
```

**Serie Visualizzate:**

| Serie | Colore (Auto) | Descrizione |
|-------|---------------|-------------|
| `Temperature` | Blu | Temperatura reale misurata |
| `Feels_Like` | Arancione | Temperatura percepita (wind chill) |
| `App_Temp` | Verde | Temperatura apparente (heat index) |

**Insights:**
- Trend termico giornaliero
- Differenza percezione vs realtà
- Condizioni comfort lavoratori

---


#### Avvio Dashboard

##### Locale

```bash
# Navigare nella directory progetto
cd /path/to/ACSM---Advanced-Construction-Site-Montitoring

# Installare dipendenze (se non già fatto)
pip install streamlit pandas

# Avvio dashboard
streamlit run dashboard.py
```

**Output Console:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```

**Browser:** Apre automaticamente `http://localhost:8501`



#### Pattern di Utilizzo

##### Workflow Operatore Cantiere

```
1. Operatore accede dashboard: http://server:8501
2. Click "⚙️ Calcola Giornata" alle 20:30
3. Attesa 2-3 minuti elaborazione
4. Selezione CSV giornata corrente dal dropdown
5. Analisi visuale grafici
6. Download CSV per invio supervisore
```

##### Workflow Supervisore

```
1. Ricezione CSV da operatore (email/WhatsApp)
2. Import in PowerBI Desktop
3. Refresh dashboard aziendale
4. Condivisione report stakeholder
```

---

**Versione:** 1.0  
**Ultimo aggiornamento:** Novembre 2025  
**Stato:** Produzione  
**URL Demo:** `http://localhost:8501` (locale)

### database.py

raccolta di dati e aggregazione degli stessi all'interno di un database sqlite3

#### Panoramica

database.py è il modulo responsabile della **persistenza e aggregazione dei dati** raccolti dal sistema ACSM. Gestisce la creazione, il popolamento e l'interrogazione di un database SQLite che consolida informazioni provenienti da tre fonti distinte: fotografie delle camere, connessioni wireless e dati meteorologici.

#### Scopo del Modulo

Il modulo serve a:

1. **Centralizzare i Dati**: Unificare dati provenienti da CSV dispersi in un unico database relazionale
2. **Persistenza Storica**: Mantenere traccia cronologica delle attività di cantiere
3. **Aggregazione Temporale**: Organizzare dati per giornata e fascia oraria
4. **Integrazione Multi-Fonte**: Correlare dati da Meraki, analisi gru (ChatGPT) e centraline meteo

#### Architettura Database

##### Schema Tabella: `cantiere_records`

```sql
CREATE TABLE cantiere_records (
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
);
```

###### Campi Tabella

| Campo              | Tipo    | Vincoli                    | Descrizione                             |
| -------------------- | --------- | ---------------------------- | ----------------------------------------- |
| `id`               | INTEGER | PRIMARY KEY, AUTOINCREMENT | Identificatore univoco record           |
| `network`          | TEXT    | NOT NULL                   | Nome rete (es. "THU", "B12", "HOM_BIS") |
| `day`              | TEXT    | NOT NULL                   | Data in formato ISO (YYYY-MM-DD)        |
| `timeframe`        | TEXT    | NOT NULL                   | Fascia oraria (es. "06:00-07:59")       |
| `photo_paths`      | TEXT    | -                          | JSON array con percorsi immagini        |
| `wireless_clients` | INTEGER | -                          | Numero dispositivi wireless rilevati    |
| `crane_used`       | TEXT    | -                          | Utilizzo gru ("Yes"/"No")               |
| `crane_moves`      | INTEGER | -                          | Numero movimenti gru                    |
| `weather`          | TEXT    | -                          | Condizioni meteo (JSON o stringa)       |
| `created_at`       | TEXT    | DEFAULT now()              | Timestamp inserimento                   |

**Vincolo di Unicità:** `UNIQUE(network, day, timeframe)` - Impedisce duplicati per stesso cantiere/giorno/fascia

---

#### Variabili Globali

```python
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
```

| Variabile         | Valore        | Descrizione                            |
| ------------------- | --------------- | ---------------------------------------- |
| `REAL_TIMEFRAMES` | `list[tuple]` | 7 fasce orarie lavorative (6:00-20:00) |
| `IMAGES_DIR`      | `str`         | Directory radice snapshot camere       |
| `CRANE_CSV`       | `str`         | Path CSV analisi gru (output ChatGPT)  |
| `DB_PATH`         | `str`         | Path database SQLite                   |

---

#### Funzioni Principali

##### `create_database(db_path: str = DB_PATH)`

Crea il database SQLite e lo schema della tabella se non esistenti.

**Parametri:**

- `db_path` (str, optional): Path database. Default: `"cantiere.db"`

**Comportamento:**

- Crea file database se assente
- Definisce tabella `cantiere_records` con vincoli
- Operazione idempotente (safe per chiamate multiple)

**Utilizzo:**

```python
create_database()  # Crea cantiere.db
create_database("backup.db")  # Database alternativo
```

---

##### `insert_or_replace_record(...)`

Inserisce o aggiorna un record nel database.

**Firma Completa:**

```python
def insert_or_replace_record(
    db_path: str,
    network: str,
    day: str,
    timeframe: str,
    photo_paths: List[str],
    wireless_clients: int,
    crane_used: str,
    crane_moves: int,
    weather: str
)
```

**Parametri:**

| Parametro          | Tipo        | Descrizione               |
| -------------------- | ------------- | --------------------------- |
| `db_path`          | `str`       | Path database             |
| `network`          | `str`       | Nome rete (es. "THU")     |
| `day`              | `str`       | Data ISO (YYYY-MM-DD)     |
| `timeframe`        | `str`       | Fascia (HH:MM-HH:MM)      |
| `photo_paths`      | `List[str]` | Lista percorsi foto       |
| `wireless_clients` | `int`       | Conteggio dispositivi     |
| `crane_used`       | `str`       | "Yes" o "No"              |
| `crane_moves`      | `int`       | Numero movimenti          |
| `weather`          | `str`       | Dati meteo (stringa/JSON) |

**Comportamento:**

- **INSERT**: Se chiave univoca (network, day, timeframe) non esiste
- **UPDATE**: Se record già presente, sovrascrive dati e aggiorna `created_at`

**Strategia di Conflitto:** `ON CONFLICT(...) DO UPDATE SET`

**Utilizzo:**

```python
insert_or_replace_record(
    "cantiere.db",
    network="THU",
    day="2025-11-14",
    timeframe="06:00-07:59",
    photo_paths=["path/to/photo1.jpg", "path/to/photo2.jpg"],
    wireless_clients=8,
    crane_used="Yes",
    crane_moves=15,
    weather='{"temp": 18.5, "humidity": 65}'
)
```

---

##### `extract_date_time_from_filename(filename: str) -> Optional[Tuple[date, time]]`

Estrae data e ora da nome file snapshot.

**Formato Atteso:** `camera_[SERIAL]_snapshot_[YYYYMMDD]_[HHMMSS].jpg`

**Esempio:**

```python
# Input: "camera_Q2XX1234_snapshot_20251114_153045.jpg"
result = extract_date_time_from_filename(filename)
# Output: (date(2025, 11, 14), time(15, 30, 45))
```

**Ritorno:**

- `Tuple[date, time]`: Coppia data/ora estratta
- `None`: Se parsing fallisce

**Logica:**

1. Rimuove estensione file
2. Split su underscore
3. Estrae componenti data/ora da posizioni attese
4. Valida formato e converte in oggetti `datetime`

---

##### `build_timeframes_from_images(...) -> Dict[Tuple[str,str,str], List[str]]`

Organizza fotografie in fasce orarie per rete e camera.

**Firma Completa:**

```python
def build_timeframes_from_images(
    images_dir: str,
    timeframes: List[Tuple[time, time]]
) -> Dict[Tuple[str,str,str], List[str]]
```

**Parametri:**

- `images_dir` (str): Directory radice snapshot
- `timeframes` (List[Tuple]): Lista fasce orarie

**Struttura Directory Attesa:**

```
camera_snapshot/
├── THU/
│   ├── camera_0/
│   │   ├── camera_Q2XX_snapshot_20251114_063000.jpg
│   │   ├── camera_Q2XX_snapshot_20251114_083000.jpg
│   │   └── ...
│   └── camera_1/
├── B12/
└── HOM_BIS/
```

**Ritorno:** Dizionario con chiave `(rete, camera, fascia)` e valore lista path foto

**Struttura Output:**

```python
{
    ("THU", "camera_0", "06:00-07:59"): [
        "camera_snapshot/THU/camera_0/photo1.jpg",
        "camera_snapshot/THU/camera_0/photo2.jpg"
    ],
    ("THU", "camera_0", "08:00-09:59"): [...],
    ("B12", "camera_0", "06:00-07:59"): [...]
}
```

**Logica:**

1. Scansiona ricorsivamente directory
2. Estrae data/ora da ogni filename
3. Determina fascia oraria di appartenenza
4. Raggruppa per (rete, camera, fascia)

---

##### `parse_crane_csv(csv_path: str = CRANE_CSV) -> Dict[Tuple[str, str], Dict]`

Legge e struttura dati CSV analisi gru generato da ChatGPT.

**Formato CSV Atteso:**

```csv
Day Timeframe WasCraneUsed NumberOfMoves Weather
2025-11-14 06:00-07:59 Yes 12 Sunny
2025-11-14 08:00-09:59 No 0 Cloudy
```

**Ritorno:** Dizionario con chiave `(data, fascia)` e valori dettagli gru

**Struttura Output:**

```python
{
    ("2025-11-14", "06:00-07:59"): {
        "used": "Yes",
        "moves": 12,
        "weather": "Sunny"
    },
    ("2025-11-14", "08:00-09:59"): {
        "used": "No",
        "moves": 0,
        "weather": "Cloudy"
    }
}
```

**Gestione Errori:**

- Salta righe malformate
- Converte `NumberOfMoves` in intero (default 0 se fallisce)

---

##### `get_wireless_clients_for_network(...) -> int`

Recupera conteggio dispositivi wireless da oggetto `sensors`.

**Firma Completa:**

```python
def get_wireless_clients_for_network(
    s_obj: 'sensors',
    network_id: str,
    date_str: str,
    tf_label: str,
    label_to_tf: Dict[str, Tuple[time, time]]
) -> int
```

**Parametri:**

| Parametro     | Tipo      | Descrizione                      |
| --------------- | ----------- | ---------------------------------- |
| `s_obj`       | `sensors` | Istanza classe merakiSensors     |
| `network_id`  | `str`     | ID rete Meraki                   |
| `date_str`    | `str`     | Data ISO (YYYY-MM-DD)            |
| `tf_label`    | `str`     | Label fascia (es. "06:00-07:59") |
| `label_to_tf` | `Dict`    | Mapping label → tuple time      |

**Processo:**

1. Cerca CSV wireless nella directory `csv/[RETE]/`
2. Pattern matching: `wireless_detections_[RETE]_[DATA].csv`
3. Legge CSV e cerca riga corrispondente a data/fascia
4. Estrae campo `DeviceConnected`

**Ritorno:** `int` - Numero dispositivi o 0 se non trovato

**Fallback:** Se CSV assente o riga mancante, tenta chiamata API diretta (TODO)

---

##### `run_ingest(...)`

Funzione principale di orchestrazione per popolamento database.

**Firma Completa:**

```python
def run_ingest(
    images_dir: str = IMAGES_DIR,
    csv_path: str = CRANE_CSV,
    db_path: str = DB_PATH
)
```

**Workflow Completo:**

```
┌─────────────────────────────────────────────┐
│ 1. Crea database (se non esiste)           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 2. Inizializza merakiSensors                │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 3. Organizza foto per rete/camera/fascia   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 4. Parsing CSV analisi gru                  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 5. Per ogni rete:                           │
│    ├─ Per ogni fascia oraria:               │
│    │   ├─ Recupera foto                     │
│    │   ├─ Recupera dati gru (da CSV)        │
│    │   ├─ Recupera wireless clients (API)   │
│    │   └─ INSERT/UPDATE database            │
└─────────────────────────────────────────────┘
```

**Esempio Output Console:**

```
📸 Foto organizzate per fascia oraria
📊 CSV gru parsato: 21 record
🏗️ Elaborazione rete: THU
   ✓ Fascia 06:00-07:59: 5 foto, 8 client, gru attiva (12 movimenti)
   ✓ Fascia 08:00-09:59: 7 foto, 15 client, gru attiva (25 movimenti)
   ...
🏗️ Elaborazione rete: B12
   ...
✅ Ingest completato: 21 record inseriti/aggiornati
```

**Utilizzo:**

```python
# Utilizzo base
run_ingest()

# Personalizzato
run_ingest(
    images_dir="backup_snapshots",
    csv_path="analisi_gru_novembre.csv",
    db_path="database_novembre.db"
)
```

#### Gestione Database da Terminale

##### Apertura Database

```bash
sqlite3 cantiere.db
```

##### Query SQL Interattive

```sql
-- Visualizza tutti i record
SELECT * FROM cantiere_records;

-- Filtra per rete
SELECT * FROM cantiere_records WHERE network = 'THU';

-- Conteggio record per giorno
SELECT day, COUNT(*) as num_records 
FROM cantiere_records 
GROUP BY day;

-- Ultimo aggiornamento per rete
SELECT network, MAX(created_at) as last_update
FROM cantiere_records
GROUP BY network;
```

### Comandi Utilità

```sql
-- Schema tabella
.schema cantiere_records

-- Esporta in CSV
.headers on
.mode csv
.output export.csv
SELECT * FROM cantiere_records;
.output stdout

-- Statistiche database
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT network) as total_networks,
    COUNT(DISTINCT day) as total_days,
    MIN(day) as first_day,
    MAX(day) as last_day
FROM cantiere_records;
```

---

##

### crane_movement_recognition.py

usando la funzione di cattura delle immagini e le API openAI, determina se la gru si è mossa o meno

### docker_compose.yml

#### Panoramica

docker-compose.yml definisce l'**infrastruttura containerizzata** per l'esposizione sicura del broker MQTT utilizzato per ricevere eventi real-time dalle camere Meraki MV Sense. Il file orchestra due servizi Docker: un broker MQTT locale (Eclipse Mosquitto) e un tunnel Cloudflare per l'esposizione pubblica senza apertura porte sul firewall.

#### Scopo della Configurazione

L'infrastruttura Docker serve a:

1. **MQTT Broker Locale**: Ricevere messaggi MV Sense dalle camere Meraki
2. **Esposizione Sicura**: Tunnel Cloudflare per accesso pubblico senza port forwarding
3. **Persistenza Dati**: Volumi Docker per configurazione e log Mosquitto
4. **Isolamento Rete**: Network bridge dedicato per comunicazione inter-container
5. **Zero-Trust Security**: Nessuna porta esposta direttamente su Internet

---

#### Architettura

##### Diagramma Infrastruttura

```
┌─────────────────────────────────────────────────────────┐
│                    Internet                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTPS (Cloudflare Edge)
                     ▼
┌─────────────────────────────────────────────────────────┐
│            Cloudflare Tunnel                            │
│  (cloudflared container)                                │
│  - Autenticazione con Tunnel Token                      │
│  - Routing mqtt.merakiabitarein.app → localhost         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ cloudflare_tunnel_network (bridge)
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Eclipse Mosquitto MQTT Broker                   │
│  (mosquitto container)                                  │
│  - Port 1883 (MQTT)                                     │
│  - Port 9001 (WebSocket)                                │
│  - Volumi persistenti: config, data, log                │
└─────────────────────────────────────────────────────────┘
                     ▲
                     │ MQTT Publish
                     │
┌─────────────────────────────────────────────────────────┐
│           Camere Meraki MV                              │
│  - Invio eventi MV Sense (motion, object detection)     │
│  - Topic: /merakimv/{serial}/0                          │
└─────────────────────────────────────────────────────────┐
```

---

#### Servizi Definiti

##### 1. mosquitto - MQTT Broker

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto
    container_name: mqtt_broker_merakiabitarein
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    ports:
      - 1883:1883  # MQTT
      - 9001:9001  # WebSocket
    stdin_open: true
    tty: true
    networks:
      - cloudflare_tunnel_network
```

###### Configurazione

| Parametro | Valore | Descrizione |
|-----------|--------|-------------|
| **Image** | `eclipse-mosquitto` | Broker MQTT open-source ufficiale |
| **Container Name** | `mqtt_broker_merakiabitarein` | Nome container per identificazione |
| **Volumes** | 3 mount points | Persistenza configurazione, dati, log |
| **Ports** | 1883, 9001 | MQTT standard e WebSocket |
| **stdin_open/tty** | `true` | Abilita modalità interattiva (debug) |
| **Network** | `cloudflare_tunnel_network` | Bridge privato per comunicazione con cloudflared |

###### Volumi Persistenti

```
./mosquitto/
├── config/
│   └── mosquitto.conf    # Configurazione broker
├── data/
│   └── mosquitto.db      # Messaggi persistenti (se QoS > 0)
└── log/
    └── mosquitto.log     # Log operazioni
```

###### Porte Esposte

| Porta | Protocollo | Utilizzo |
|-------|------------|----------|
| **1883** | MQTT | Camere Meraki → Broker |
| **9001** | WebSocket | Client browser/app web (opzionale) |

---

##### 2. `cloudflared` - Cloudflare Tunnel

```yaml
cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    networks:
      - cloudflare_tunnel_network
```

#### Configurazione

| Parametro | Valore | Descrizione |
|-----------|--------|-------------|
| **Image** | `cloudflare/cloudflared:latest` | Client tunnel ufficiale Cloudflare |
| **Container Name** | `cloudflared` | Nome container |
| **Restart Policy** | `unless-stopped` | Riavvio automatico su crash/reboot |
| **Command** | `tunnel run` | Esegue tunnel configurato |
| **Environment** | `TUNNEL_TOKEN` | Token autenticazione da variabile d'ambiente |
| **Network** | `cloudflare_tunnel_network` | Bridge condiviso con Mosquitto |

###### Variabile d'Ambiente

**`CLOUDFLARE_TUNNEL_TOKEN`**: Token generato dal Cloudflare Dashboard
###### Funzionamento

```
Camere Meraki → mqtt.merakiabitarein.app (DNS Cloudflare)
                         ↓
                 Cloudflare Edge (autenticazione)
                         ↓
                 Tunnel cifrato → cloudflared container
                         ↓
                 Bridge network → mosquitto:1883
```
##### 3. `networks` - Bridge Network

```yaml
networks:
  cloudflare_tunnel_network:
    driver: bridge
```

###### Configurazione

| Parametro | Valore | Descrizione |
|-----------|--------|-------------|
| **Nome** | `cloudflare_tunnel_network` | Identificatore rete Docker |
| **Driver** | `bridge` | Network bridge isolato |

**Subnet assegnata automaticamente:** `172.x.x.x/16` (Docker gestito)

**Comunicazione Inter-Container:**

```
cloudflared → mosquitto (risoluzione DNS automatica)
http://mosquitto:1883
```

---

#### Utilizzo

##### Avvio Infrastruttura

```bash
# Navigare nella directory progetto
cd /path/to/ACSM---Advanced-Construction-Site-Montitoring

# Creare file .env con token
echo "CLOUDFLARE_TUNNEL_TOKEN=your_token_here" > .env

# Avvio servizi in background
docker-compose up -d

# Verifica stato
docker-compose ps
```

**Output Atteso:**

```
NAME                        IMAGE                          STATUS
cloudflared                 cloudflare/cloudflared:latest  Up 10 seconds
mqtt_broker_merakiabitarein eclipse-mosquitto              Up 10 seconds
```

##### Verifica Connettività

###### Test Locale MQTT

```bash
# Installare client MQTT
sudo apt-get install mosquitto-clients

# Sottoscrizione topic test
mosquitto_sub -h localhost -p 1883 -t test/topic

# (in altra finestra) Pubblicazione messaggio
mosquitto_pub -h localhost -p 1883 -t test/topic -m "Hello MQTT"
```

###### Test Tunnel Cloudflare

```bash
# Verifica risoluzione DNS
nslookup mqtt.merakiabitarein.app

# Test connessione MQTT tramite tunnel
mosquitto_sub -h mqtt.merakiabitarein.app -p 1883 -t test/topic
```

##### Monitoraggio

###### Log Container

```bash
# Log mosquitto
docker-compose logs -f mosquitto

# Log cloudflared
docker-compose logs -f cloudflared

# Log entrambi
docker-compose logs -f
```


# Linee guida generali


#### Istruzioni Deployment

All'interno della cartella, aprire una finestra di terminale e digitare
`streamlit run dashboard.py`

#### Variabili d'ambiente

è necessario implementare le variabili d'ambiente mediante

- file `credentials.py` con all'interno le chiavi API dei vari servizi implementati
- file `.env`, con all interno

#### AUTOMATIZZARE SCRIPT CALCOLO_GIORNATA:

1. Aprire crontab con crontab -e
2. -Inserire gli script da automatizzare a specifici orari (6 e 20) e per specifici giorni (Lun-Ven):
   `0 8 * * * /usr/bin/python3 /mnt/c/Users/percorso_cartella/photoscript.py inizio 0 20 * * * /usr/bin/python3 /mnt/c/Users/percorso_cartella/photoscript.py fine`

#### APRIRE DATABASE DA TERMINALE:

- sqlite3 cantiere.db
  `SELECT * FROM cantiere_records`

#### Dipendenze

è a disposizione il requirements.txt. Il progetto principalmente usa le librerie meraki, streamlit, openai, pandas, box, paho-mqtt.

