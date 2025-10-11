import paho.mqtt.client as mqtt
import time
import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from matplotlib.collections import LineCollection
from scipy.signal import butter, filtfilt
from pathlib import Path


base_dir = Path(__file__).resolve().parent
output_data = base_dir.parent / "dados_e_videos" / "emg_data.csv"
output_graph = base_dir.parent / "dados_e_videos" / "emg_plot.png"


BROKER = "192.168.238.153"
PORT = 1883
TOPIC_DATA = "emg/sensor1"
TOPIC_CTRL = "emg/control"

data_buffer = []
duration = int(sys.argv[1]) if len(sys.argv) > 1 else 10


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

def collect_data(duration, output_path):
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
    with open(output_data, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t (s)", "emg_value"])
        writer.writerows(data_buffer)

    print(f"Coleta finalizada! {len(data_buffer)} amostras salvas em {output_data}")


    fs = 1000  # Hz
    ordem = 4

    # Frequências de corte
    fc_passa_alta = 20     # Hz
    fc_passa_baixa = 450 # Hz

    # Leitura dos dados
    df = pd.read_csv(output_data)
    dados = pd.to_numeric(df['emg_value'], errors='coerce').dropna().values

    # Remoção do offset DC
    dados = dados - np.mean(dados)

    # Aplicação dos filtros
    dados_filtrados = filtro_passa_alta(dados, fs, fc_passa_alta, ordem)
    dados_filtrados = filtro_passa_baixa(dados_filtrados, fs, fc_passa_baixa, ordem)
    # Tempo para gráfico
    tempo = np.arange(len(dados)) / fs

    # --- Cálculo das métricas ---
    pico = np.max(np.abs(dados_filtrados))
    media = np.mean(np.abs(dados_filtrados))
    integral = np.trapz(np.abs(dados_filtrados), dx=1/fs)
    desvio = np.std(dados_filtrados)

    # FFT para frequência média/mediana
    freqs = np.fft.rfftfreq(len(dados_filtrados), d=1/fs)
    espectro = np.abs(np.fft.rfft(dados_filtrados))**2
    freq_media = np.sum(freqs * espectro) / np.sum(espectro)
    cumsum = np.cumsum(espectro)
    freq_mediana = freqs[np.searchsorted(cumsum, cumsum[-1]/2)]

    dados_positivos = np.abs(dados_filtrados)

    # --- Métricas dados positivos ---
    pico_pos = np.max(dados_positivos)
    media_pos = np.mean(dados_positivos)
    integral_pos = np.trapz(dados_positivos, dx=1/fs)
    desvio_pos = np.std(dados_positivos)

    freqs_pos = np.fft.rfftfreq(len(dados_positivos), d=1/fs)
    espectro_pos = np.abs(np.fft.rfft(dados_positivos))**2
    freq_media_pos = np.sum(freqs_pos * espectro_pos) / np.sum(espectro_pos)
    cumsum_pos = np.cumsum(espectro_pos)
    freq_mediana_pos = freqs_pos[np.searchsorted(cumsum_pos, cumsum_pos[-1]/2)]

    # --- Plot em 3 partes ---
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(
        4, 1, figsize=(20, 16), 
        gridspec_kw={'height_ratios': [3, 3, 3, 1]}
    )

    # Gráfico 1 - Sinal filtrado normal
    ax1.plot(tempo, dados_filtrados, label='Filtrado', linewidth=0.5, color="blue")
    ax1.set_title('Sinal EMG Filtrado (20–450 Hz)', fontsize=28)
    ax1.set_xlabel('Tempo (s)', fontsize=22)
    ax1.set_ylabel('Amplitude (ADC)', fontsize=22)
    ax1.grid(True)
    ax1.legend(fontsize=18)
    ax1.tick_params(axis='both', labelsize=18)

    # Gráfico 2 - Sinal transformado em positivo
    ax2.plot(tempo, dados_positivos, label='Filtrado Positivo (abs)', linewidth=0.5, color="green")
    ax2.set_title('Sinal EMG Positivado (valor absoluto)', fontsize=28)
    ax2.set_xlabel('Tempo (s)', fontsize=22)
    ax2.set_ylabel('Amplitude (ADC)', fontsize=22)
    ax2.grid(True)
    ax2.legend(fontsize=18)
    ax2.tick_params(axis='both', labelsize=18)

    norm = plt.Normalize(dados_positivos.min(), dados_positivos.max())

    # Criar pontos para o LineCollection
    points = np.array([tempo, dados_positivos]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Cria o LineCollection (mapa de cores conforme intensidade)
    lc = LineCollection(segments, cmap='coolwarm', norm=norm)
    lc.set_array(dados_positivos)   # valores usados no colormap
    lc.set_linewidth(2)

    # Gráfico 3 - Sinal colorido
    ax3.add_collection(lc)
    ax3.set_xlim(tempo.min(), tempo.max())
    ax3.set_ylim(dados_positivos.min(), dados_positivos.max())
    ax3.set_title('Sinal EMG Colorido (intensidade → cor)', fontsize=28)
    ax3.set_xlabel('Tempo (s)', fontsize=22)
    ax3.set_ylabel('Ativação', fontsize=22)
    ax3.tick_params(axis='both', labelsize=18)

    # Opcional: barra de cores
    cbar = fig.colorbar(lc, ax=ax3)
    cbar.set_label('Intensidade (0–100%)', fontsize=18)

    # Texto com métricas (originais e positivas)
    ax4.axis("off")
    texto = (
        "=== Métricas Originais ===\n"
        f"Pico: {pico:.2f}\n"
        f"Média: {media:.2f}\n"
        f"Integral: {integral:.2f}\n"
        f"Desvio Padrão: {desvio:.2f}\n"
        f"Frequência Média: {freq_media:.2f} Hz\n"
        f"Frequência Mediana: {freq_mediana:.2f} Hz\n\n"
        "=== Métricas Positivas ===\n"
        f"Pico: {pico_pos:.2f}\n"
        f"Média: {media_pos:.2f}\n"
        f"Integral: {integral_pos:.2f}\n"
        f"Desvio Padrão: {desvio_pos:.2f}\n"
        f"Frequência Média: {freq_media_pos:.2f} Hz\n"
        f"Frequência Mediana: {freq_mediana_pos:.2f} Hz"
    )
    ax4.text(0.05, 0.95, texto, fontsize=20, va="top", ha="left")


    plt.tight_layout()
    plot_file = "../dados_e_videos/emg_plot.png"
    plt.savefig(plot_file, dpi=100)
    plt.close()

if __name__ == "__main__":
    collect_data(duration, output_path=output_data)
