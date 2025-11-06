import paho.mqtt.client as mqtt
import time
from datetime import datetime
import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from matplotlib.collections import LineCollection
from scipy.signal import butter, filtfilt, find_peaks
from pathlib import Path
import json, os


base_dir = Path(__file__).resolve().parent
output_data = base_dir.parent / "dados_e_videos" / "emg_data.csv"
output_graph = base_dir.parent / "dados_e_videos" / "emg_plot.png"
with open(base_dir / "config.json") as f:
    cfg = json.load(f)

BROKER = cfg["wifi_broker_ip"]
TOPIC_DATA = "emg/sensor1"
PORT = 1883

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

def wait_for_file(path: Path, timeout: float = 5.0, poll: float = 0.2) -> bool:
    """Aguarda até 'timeout' segundos pelo arquivo existir. Retorna True se apareceu."""
    waited = 0.0
    while waited < timeout:
        if path.exists():
            return True
        time.sleep(poll)
        waited += poll
    return False

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
    print(f"Coletando dados por {duration} segundos...")
    time.sleep(duration)

    # envia comando stop
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
    #freq_media = np.sum(freqs * espectro) / np.sum(espectro)
    cumsum = np.cumsum(espectro)
    #freq_mediana = freqs[np.searchsorted(cumsum, cumsum[-1]/2)]

    dados_positivos = np.abs(dados_filtrados)

    # --- Métricas dados positivos ---
    pico_pos = np.max(dados_positivos)
    media_pos = np.mean(dados_positivos)
    integral_pos = np.trapz(dados_positivos, dx=1/fs)
    desvio_pos = np.std(dados_positivos)

    # FFT
    N = len(dados_filtrados)
    fft_vals = np.fft.rfft(dados_filtrados)
    fft_freqs = np.fft.rfftfreq(N, d=1/fs)
    magnitude = np.abs(fft_vals) / N  # normalização da amplitude

    def freq_media_e_mediana(dados, fs):
        freqs = np.fft.rfftfreq(len(dados), d=1/fs)
        espectro = np.abs(np.fft.rfft(dados))**2
        soma_esp = np.sum(espectro)
        if soma_esp == 0 or np.isnan(soma_esp):
            return np.nan, np.nan
        freq_media = np.sum(freqs * espectro) / soma_esp
        cumsum = np.cumsum(espectro)
        freq_mediana = freqs[np.searchsorted(cumsum, cumsum[-1]/2)]
        return freq_media, freq_mediana
    
    freq_media, freq_mediana = freq_media_e_mediana(dados_filtrados, fs)
    freq_media_pos, freq_mediana_pos = freq_media_e_mediana(dados_positivos, fs)

    # --- Envoltório linear (passa-baixa de 5 Hz) ---
    envoltorio = filtro_passa_baixa(np.abs(dados_filtrados), fs, 5, ordem=4)

    # --- RMS deslizante (janela de 250 ms) ---
    janela = int(fs * 0.250)
    rms = np.sqrt(np.convolve(dados_filtrados**2, np.ones(janela)/janela, mode='valid'))
    tempo_rms = np.arange(len(rms)) / fs


    # Parametros de detecção (ajuste se necessário)
    peak_height = np.max(envoltorio) * 0.25   # 25% do pico máximo
    min_distance_s = 0.2                       # separação mínima entre picos em segundos
    min_distance_samples = int(min_distance_s * fs)

    peaks, props = find_peaks(envoltorio, height=peak_height, distance=min_distance_samples)
    peak_times = tempo[peaks]  # tempo relativo em segundos
    peak_values = envoltorio[peaks]

    # --- Procura arquivos de ângulos gravados (JSONL) ---
    angles_dir = base_dir.parent / "dados_e_videos"
    angle_files = list(angles_dir.glob("video_angles.jsonl"))

    matched_angles_ts = np.array([])
    matched_angles_vals = np.array([])
    if angle_files:
        best_file = None
        best_count = 0
        # escolhe o arquivo que mais possui timestamps dentro da janela de coleta
        start_abs = start_time
        end_abs = start_time + duration
        for fpath in angle_files:
            count = 0
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            obj = json.loads(line)
                            t = float(obj.get("t", 0.0))
                            if start_abs <= t <= end_abs:
                                count += 1
                        except Exception:
                            continue
            except Exception:
                continue
            if count > best_count:
                best_count = count
                best_file = fpath

        if best_file and best_count > 0:
            # se o arquivo ainda estiver sendo escrito pelo processo de vídeo, aguarda um pouco
            if not wait_for_file(best_file, timeout=5.0, poll=0.2):
                # não apareceu em tempo, tenta continuar sem ângulos
                best_file = None

        if best_file and best_count > 0:
            ts_list = []
            val_list = []
            try:
                with open(best_file, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            obj = json.loads(line)
                            t = float(obj.get("t", 0.0))
                            a = float(obj.get("angle", np.nan))
                            if start_abs - 0.5 <= t <= end_abs + 0.5:
                                ts_list.append(t)
                                val_list.append(a)
                        except Exception:
                            continue
                # depois de ler com sucesso, remove o arquivo para não reaparecer em próximas coletas
                try:
                    os.remove(str(best_file))
                except Exception:
                    pass
            except Exception:
                pass

            if ts_list:
                # converte para arrays e para tempo relativo à coleta EMG
                matched_angles_ts = np.array(ts_list) - start_abs
                matched_angles_vals = np.array(val_list)

    # --- Interpola ângulo nos tempos dos picos (se houver ângulos) ---
    if matched_angles_ts.size > 0 and peak_times.size > 0:
        # garante ordenação para interp
        order = np.argsort(matched_angles_ts)
        matched_angles_ts = matched_angles_ts[order]
        matched_angles_vals = matched_angles_vals[order]
        # interpola (valores fora do alcance viram NaN)
        angles_at_peaks = np.interp(peak_times, matched_angles_ts, matched_angles_vals,
                                    left=np.nan, right=np.nan)
    else:
        angles_at_peaks = np.full_like(peak_times, np.nan, dtype=float)

    # --- Salva arquivo JSONL com picos e ângulos (opcional) ---
    peaks_out = angles_dir / f"emg_peaks_with_angles_{int(start_abs)}.jsonl"
    try:
        with open(peaks_out, "w", encoding="utf-8") as fh:
            for i, pt in enumerate(peak_times):
                entry = {
                    "peak_time_abs": float(start_abs + float(pt)),
                    "peak_time_rel": float(pt),
                    "emg_envoltorio": float(peak_values[i]),
                    "angle_at_peak": None if np.isnan(angles_at_peaks[i]) else float(angles_at_peaks[i])
                }
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # --- Plot em 3 partes ---
    fig, (ax1, ax2, ax3, ax4, ax5, ax6, ax7) = plt.subplots(
        7, 1, figsize=(duration, 30),
        gridspec_kw={'height_ratios': [3, 3, 3, 3, 3, 3, 2]}
    )

    fig.suptitle(f"Data da coleta: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", fontsize=26, y=0.995)

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

    if len(peaks) > 0:
        # marcador dos picos no envoltório
        ax2.scatter(peak_times, peak_values, color='red', s=30, label='Picos (envoltório)')

        # soma das amplitudes dos picos (usada para calcular % por amplitude)
        sum_peaks = np.sum(peak_values) if peak_values.size > 0 else 0.0

        # padding vertical em unidades de dados para posicionar texto acima da linha
        y_range = dados_positivos.max() - dados_positivos.min()
        y_pad = y_range * 0.05 if y_range > 0 else (np.abs(peak_values).max() * 0.05 + 1e-6)

        # anotações acima de cada pico com o ângulo e % de ativação por amplitude
        for i, (peak_idx, t, pv) in enumerate(zip(peaks, peak_times, peak_values)):
            ang = angles_at_peaks[i] if (i < len(angles_at_peaks)) else np.nan

            # percentual baseado apenas na amplitude do pico
            if sum_peaks > 0:
                percent = 100.0 * pv / sum_peaks
            else:
                percent = np.nan

            if not np.isnan(ang):
                txt = f"{ang:.1f}°\n{percent:.1f}%"
                # posiciona texto em coordenadas de dados, ligeiramente acima do pico
                y_above = pv + y_pad
                ax2.text(
                    t, y_above, txt,
                    ha='center', va='bottom',
                    fontsize=14, color='red', fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
                    zorder=10
                )

        # marcador visual adicional para picos com ângulo disponível
        if matched_angles_ts.size > 0:
            valid = ~np.isnan(angles_at_peaks)
            if np.any(valid):
                ax2.scatter(peak_times[valid], peak_values[valid], color='orange', marker='x', s=40,
                            label='Ângulo no pico')

        ax2.legend(fontsize=12, loc='upper right')


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

    ax4.plot(tempo, envoltorio, color='red', linewidth=1)
    ax4.set_title('Envoltório Linear (Passa-baixa 5 Hz)', fontsize=26)
    ax4.set_xlabel('Tempo (s)', fontsize=20)
    ax4.set_ylabel('Ativação', fontsize=20)
    ax4.grid(True)

    ax5.plot(tempo_rms, rms, color='purple', linewidth=1)
    ax5.set_title('RMS Deslizante (Janela 250 ms)', fontsize=26)
    ax5.set_xlabel('Tempo (s)', fontsize=20)
    ax5.set_ylabel('RMS', fontsize=20)
    ax5.grid(True)

    ax6.plot(fft_freqs, magnitude, color='orange', linewidth=1)
    ax6.set_title('Transformada Rápida de Fourier (FFT)', fontsize=26)
    ax6.set_xlabel('Frequência (Hz)', fontsize=20)
    ax6.set_ylabel('Magnitude', fontsize=20)
    ax6.grid(True)
    ax6.set_xlim(0, 500)  # limita até 500 Hz (faixa útil do EMG)

    # Opcional: barra de cores
    cbar = fig.colorbar(lc, ax=ax3)
    cbar.set_label('Intensidade (0–100%)', fontsize=18)

    # Texto com métricas (originais e positivas)
    ax7.axis("off")
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
        "\n"
    )
    ax7.text(0.05, 0.95, texto, fontsize=20, va="top", ha="left")


    plt.tight_layout()
    plot_file = "../dados_e_videos/emg_plot.png"
    plt.savefig(plot_file, dpi=80)
    plt.close()



if __name__ == "__main__":
    collect_data(duration, output_path=output_data)
