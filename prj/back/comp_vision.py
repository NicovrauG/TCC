import cv2
import mediapipe as mp
import numpy as np
import time
import subprocess
from pathlib import Path
import os, sys, json

tempo_execucao = int(sys.argv[1]) if len(sys.argv) > 1 else 10
index_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None

if index_arg is not None:
    name = f"{index_arg:04d}"

# Inicializa o MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Calcula o ângulo entre três pontos
def calcular_angulo(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ab = a - b
    cb = c - b
    angulo = np.arccos(np.dot(ab, cb) / (np.linalg.norm(ab) * np.linalg.norm(cb)))
    return np.degrees(angulo)

# Configura caminhos de entrada e saída de arquivos
input_path = f'../dados_e_videos/video_{name}.mp4'
output_path = f'../dados_e_videos/video_{name}_h264.mp4'
angles_path = Path(__file__).resolve().parent.parent / "dados_e_videos" / "video_angles.jsonl"

# Captura da webcam
cap = cv2.VideoCapture(0)
angles_file = open(angles_path, "a", buffering=1, encoding="utf-8")

# Configura gravação de vídeo
fourcc = cv2.VideoWriter_fourcc(*'mp4v')   # Codec MP4
fps = 30.0
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
out = cv2.VideoWriter(input_path, fourcc, fps, (frame_width, frame_height))

frame_count = 0

with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    warmup_frames = 30
    t0 = time.time()
    for _ in range(warmup_frames):
        ret_w, frame_w = cap.read()
    t1 = time.time()
    measured_fps = warmup_frames / max(0.001, (t1 - t0))
    print(f"[INFO] measured_fps={measured_fps:.2f}")

    out = cv2.VideoWriter(input_path, fourcc, measured_fps, (frame_width, frame_height))

    inicio = time.time()
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Verifica tempo de execução
        if time.time() - inicio > tempo_execucao:
            print("Tempo de execução finalizado!")
            break

        # Processa frame
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        try:
            landmarks = results.pose_landmarks.landmark

            # Bíceps Direito
            ombro_direito = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                    landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            cotovelo_direito = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                    landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
            punho_direito = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                    landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

            # Bíceps Esquerdo
            ombro_esquerdo = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            cotovelo_esquerdo = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
            punho_esquerdo = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]

            # Calcula ângulo
            angulo = calcular_angulo(ombro_direito, cotovelo_direito, punho_direito)

            # Exibe ângulo na tela
            cv2.putText(image, str(int(angulo)),
                        tuple(np.multiply(cotovelo_direito, [frame_width, frame_height]).astype(int)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
            try:
                # Salva ângulo em arquivo
                entry = {"t": time.time(), "angle": float(angulo)}
                angles_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
                angles_file.flush()
                try:
                    os.fsync(angles_file.fileno())
                except Exception:
                    pass
            except Exception:
                pass
        except:
            pass

        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Exibe vídeo
        cv2.imshow('BlazePose - Angulo do Cotovelo_direito', image)

        # Grava frame processado
        out.write(image)
        frame_count += 1

        if cv2.waitKey(10) & 0xFF == ord('q'):  # ainda pode sair com 'q'
            break

# Libera recursos
cap.release()
out.release()
angles_file.close()
cv2.destroyAllWindows()

elapsed = max(0.001, time.time() - inicio)
actual_fps = frame_count / elapsed if elapsed > 0 else fps
print(f"[INFO] frames={frame_count} elapsed={elapsed:.2f}s actual_fps={actual_fps:.2f}")

# Transcodifica vídeo para H.264 usando ffmpeg (necessário para aparecer no navegador)
try:
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-r", "30",
        output_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out_p = Path(output_path)
    in_p = Path(input_path)
    if out_p.exists():
        os.replace(str(out_p), str(in_p))
        print(f"Transcodificação concluída e '{output_path}' movido para '{input_path}'")
except subprocess.CalledProcessError as e:
    print("ffmpeg falhou:", e)
