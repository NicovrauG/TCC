import cv2
import mediapipe as mp
import numpy as np
import time
from datetime import datetime
import subprocess
from pathlib import Path
import os

tempo_execucao = 20

timestamp = datetime.now().strftime("%Y%m%d_%H%M")

# Inicializa o MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def calcular_angulo(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ab = a - b
    cb = c - b
    angulo = np.arccos(np.dot(ab, cb) / (np.linalg.norm(ab) * np.linalg.norm(cb)))
    return np.degrees(angulo)

input_path = f'../dados_e_videos/video_{timestamp}.mp4'
output_path = f'../dados_e_videos/video_{timestamp}_h264.mp4'

# Captura da webcam
cap = cv2.VideoCapture(0)

# Configura gravação de vídeo
fourcc = cv2.VideoWriter_fourcc(*'mp4v')   # Codec MP4
fps = 20.0
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
out = cv2.VideoWriter(input_path, fourcc, fps, (frame_width, frame_height))

with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    warmup_frames = 5
    for _ in range(warmup_frames):
        ret_w, frame_w = cap.read()
        time.sleep(0.1)

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

            ombro = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                     landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            cotovelo = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                        landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
            punho = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                     landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

            angulo = calcular_angulo(ombro, cotovelo, punho)

            cv2.putText(image, str(int(angulo)),
                        tuple(np.multiply(cotovelo, [frame_width, frame_height]).astype(int)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        except:
            pass

        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Exibe vídeo
        cv2.imshow('BlazePose - Angulo do Cotovelo', image)

        # Grava frame processado
        out.write(image)

        if cv2.waitKey(10) & 0xFF == ord('q'):  # ainda pode sair com 'q'
            break

cap.release()
out.release()
cv2.destroyAllWindows()

try:
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # opcional: substituir o arquivo original pelo transcodificado para manter mesmo nome
    out_p = Path(output_path)
    in_p = Path(input_path)
    if out_p.exists():
        os.replace(str(out_p), str(in_p))
        print(f"Transcodificação concluída e '{output_path}' movido para '{input_path}'")
except subprocess.CalledProcessError as e:
    print("ffmpeg falhou:", e)
