import paho.mqtt.client as mqtt
import time
import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

BROKER = "192.168.238.153"
PORT = 1883
TOPIC_DATA = "emg/sensor1"
TOPIC_CTRL = "emg/control"

data_buffer = []



def filtro_passa_alta(dados, fs, fc, ordem=4):
    nyq = 0.5 * fs
    normal_fc = fc / nyq
    b, a = butter(ordem, normal_fc, btype='high')
    return filtfilt(b, a, dados)

def filtro_passa_baixa(dados, fs, fc, ordem=4):
    nyq = 0.5 * fs
    normal_fc = fc / nyq
    b, a = butter(ordem, normal_fc, btype='low')
    return filtfilt(b, a, dados)

def filtro_rejeita_banda(dados, fs, f1, f2, ordem=4):
    nyq = 0.5 * fs
    low = f1 / nyq
    high = f2 / nyq
    b, a = butter(ordem, [low, high], btype='bandstop')
    return filtfilt(b, a, dados)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Conectado ao broker!")
        client.subscribe(TOPIC_DATA)
    else:
        print("Falha na conexão. Código:", rc)

def on_message(client, userdata, msg):
    global data_buffer, start_time
    payload = msg.payload.decode()
    timestamp = time.time() - start_time
    data_buffer.append((timestamp, payload))

def collect_data(duration=20, output_file=f"../dados_e_videos/emg_data.csv"):
    global data_buffer, start_time
    data_buffer = []
    start_time = time.time()

    client = mqtt.Client(protocol=mqtt.MQTTv311, transport="tcp", callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    # envia comando start
    client.publish(TOPIC_CTRL, "start")
    print(f"Coletando dados por {duration} segundos...")
    time.sleep(duration)

    # envia comando stop
    client.publish(TOPIC_CTRL, "stop")
    client.loop_stop()
    client.disconnect()

    # salva CSV
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t (s)", "emg_value"])
        writer.writerows(data_buffer)

    print(f"Coleta finalizada! {len(data_buffer)} amostras salvas em {output_file}")


    fs = 1000  # Hz
    ordem = 4

    # Frequências de corte
    fc_passa_alta = 20     # Hz
    fc_passa_baixa = 450 # Hz

    # Leitura dos dados
    df = pd.read_csv(output_file)
    dados = pd.to_numeric(df['emg_value'], errors='coerce').dropna().values

    # Remoção do offset DC
    dados = dados - np.mean(dados)

    # Aplicação dos filtros
    dados_filtrados = filtro_passa_alta(dados, fs, fc_passa_alta, ordem)
    dados_filtrados = filtro_passa_baixa(dados_filtrados, fs, fc_passa_baixa, ordem)
    # Tempo para gráfico
    tempo = np.arange(len(dados)) / fs

    # Gráfico
    plt.figure(figsize=(20, 10))
    plt.plot(tempo, dados_filtrados, label='Filtrado', linewidth=0.5)
    plt.title('Sinal EMG Filtrado (20–450 Hz)', fontsize=32)
    plt.xlabel('Tempo (s)', fontsize=30)
    plt.ylabel('Amplitude (ADC)', fontsize=30)
    plt.grid(True)
    plt.legend(fontsize=20)
    plt.tight_layout()
    plt.tick_params(axis='both', labelsize=20) 
    plot_file = "../dados_e_videos/emg_plot.png"
    plt.savefig(plot_file)
    plt.close()
    print(plot_file)

    
if __name__ == "__main__":
    collect_data(duration=10, output_file=f"../dados_e_videos/emg_data.csv")
    
    
