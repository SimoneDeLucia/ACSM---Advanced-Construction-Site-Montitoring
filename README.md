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

## Componenti

###### meraki_api_lib.ipynb, meraki_dtlab_mqtt

usato per provare le chiamate API usate per il monitoraggio del cantiere

###### merakiSensors.py

Libreria dove vengono racchiuse tutte le funzioni riguardanti i sensori Meraki monitorati(camera, wireless, centralina meteo)

###### database.py

raccolta di dati e aggregazione degli stessi all'interno di un database sqlite3

###### docker_compose.yml

(sperimentale) utilizzato per tunnel cloudflare per deployment di un container mqtt, al fine di sfruttare la feature delle live detection della camera

###### crane_movement_recognition.py

usando la funzione di cattura delle immagini e le API openAI, determina se la gru si è mossa o meno

...

###### csv

Cartella con all'interno dataset parziali di una rete, relativo a detection meteo, wireless, movimenti di una gru

###### dati_giornata

Cartella con all'interno dataset totali di tutte le informazioni raccolte dai dispositivi di rete


# Linee guida generali

## merakiSensors

### Strutture dati
`NETWORK_ID` : Contiene all'interno tutte le informazioni relative a una rete

### Funzioni raccolta dati

Le principali funzioni per la raccolta dei dati all'interno del cantiere sono tutte catalogate con il prefisso SENSE. 
Per un invocazione semplice per la raccolta generale dei dati, è possibile usare le funzioni con suffisso all_ne

## Istruzioni Deployment

All'interno della cartella, aprire una finestra di terminale e digitare 
`streamlit run dashboard.py`


## Variabili d'ambiente

## AUTOMATIZZARE SCRIPT CALCOLO_GIORNATA:

1. Aprire crontab con crontab -e
2. -Inserire gli script da automatizzare a specifici orari (6 e 20) e per specifici giorni (Lun-Ven):
   `0 8 * * * /usr/bin/python3 /mnt/c/Users/percorso_cartella/calcolo_giornata.py inizio 0 20 * * * /usr/bin/python3 /mnt/c/Users/percorso_cartella/calcolo_giornata.py fine`

## APRIRE DATABASE DA TERMINALE:

- sqlite3 cantiere.db
  `SELECT * FROM cantiere_records`

## Dipendenze
è a disposizione il requirements.txt. Il progetto principalmente usa le librerie meraki, streamlit, openai, pandas, box, paho-mqtt.
...
