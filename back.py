from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import cv2

app = FastAPI()

# Permitir acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção, restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "backend/dados.csv"
PROC_EMG = None
PROC_BLAZEPOSE = None

@app.post("/start")
def start_scripts():
    global PROC_EMG, PROC_BLAZEPOSE
    # dispara o script de coleta EMG
    PROC_EMG = subprocess.Popen(["python", "backend/coleta_serial.py"])
    # dispara o script do BlazePose
    PROC_BLAZEPOSE = subprocess.Popen(["python", "backend/blazepose.py"])
    return {"status": "started"}

@app.post("/stop")
def stop_scripts():
    global PROC_EMG, PROC_BLAZEPOSE
    if PROC_EMG: PROC_EMG.terminate()
    if PROC_BLAZEPOSE: PROC_BLAZEPOSE.terminate()
    return {"status": "stopped"}

@app.get("/data")
def get_data():
    """Retorna o CSV mais recente do EMG"""
    if os.path.exists(DATA_FILE):
        return FileResponse(DATA_FILE, media_type="text/csv")
    return {"error": "file not found"}

@app.get("/video_feed")
def video_feed():
    """Stream de vídeo do BlazePose (webcam ou arquivo processado)"""
    cap = cv2.VideoCapture(0)  # substitua por saída do seu blazepose.py

    def generate():
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # converte frame para JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")
