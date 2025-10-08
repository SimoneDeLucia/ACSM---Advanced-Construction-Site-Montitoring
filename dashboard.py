import streamlit as st
import pandas as pd
from calcolo_giornata import calcolo_giornata_csv
from glob import glob
import os

st.title("📊 Dashboard Monitoraggio Giornata")

#Pulsante per calcolare giornata da dashboard
if st.button("⚙️ Calcola Giornata"):
    calcolo_giornata_csv()
    st.success("Dati giornata calcolati!")

#Mostra ultimi CSV salvati
st.header("📂 Ultimi dati disponibili")

csv_files = sorted(glob("dati_giornata/*.csv"), reverse=True)

if not csv_files:
    st.warning("Nessun file CSV trovato in dati_giornata/")
else:
    #Seleziona un file dall’elenco
    selected_file = st.selectbox("Seleziona dataset", csv_files)

    #Leggi il CSV
    df = pd.read_csv(selected_file)

    #Mostra tabella
    st.subheader(f"Anteprima dati: {os.path.basename(selected_file)}")
    st.dataframe(df)

    # --- Grafici ---
    st.header("Analisi")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Movimenti Gru")
        st.line_chart(df.set_index("Timeslot")["Crane_Moves"])

    with col2:
        st.subheader("Dispositivi Wireless")
        st.line_chart(df.set_index("Timeslot")["Wireless_Devices"])

    st.subheader("Meteo")
    st.line_chart(df.set_index("Timeslot")[["Temperature", "Feels_Like", "App_Temp"]])
