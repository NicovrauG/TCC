from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import psycopg2
import subprocess
from datetime import datetime

app = FastAPI()



CORRIGIR: ESTÁ RODANDO UM ARQUIVO DE CADA VEZ, TEM QUE SER OS DOIS AO MESMO TEMPO, FORA ISSO
DEU ERRO EM  INFO:     127.0.0.1:54020 - "POST /start HTTP/1.1" 500 Internal Server Error




# Caminhos base (diretório onde este arquivo back.py está)
BASE_DIR = Path(__file__).resolve().parent
FRONT_DIR = BASE_DIR.parent / "front"

# serve arquivos estáticos em /static
app.mount("/static", StaticFiles(directory=str(FRONT_DIR), html=True), name="static")

# rota raiz e /index.html que devolvem o index da pasta front
@app.get("/")
def root_index():
    return FileResponse(FRONT_DIR / "index.html")

@app.get("/index.html")
def index_html():
    return FileResponse(FRONT_DIR / "index.html")


# Configuração do banco
DB_CONFIG = {
    "dbname": "nicolas",
    "user": "nicolas",
    "password": "1921",
    "host": "localhost",
    "port": "5432"
}

# Executa scripts externos (usa caminhos absolutos)
def run_scripts():
    try:
        server_dir = BASE_DIR  # ajuste se os scripts estiverem em outra pasta
        script1 = server_dir / "Server_coletor.py"
        script2 = server_dir / "teste_viscomp.py"

        # executa e captura saída (rodar no diretório dos scripts)
        emg_out = subprocess.run(
            ["python", str(script1)],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(server_dir),
        )
        subprocess.run(["python", str(script2)], check=True, cwd=str(server_dir))

        # supondo que Server_coletor grava dados.csv e video.mp4 no mesmo dir
        emg_file_path = server_dir / "dados.csv"
        video_file_path = server_dir / "video.mp4"

        if not emg_file_path.exists() or not video_file_path.exists():
            raise FileNotFoundError("dados.csv ou video.mp4 não gerados pelos scripts")

        with open(emg_file_path, "rb") as f:
            csv_data = f.read()

        with open(video_file_path, "rb") as f:
            video_data = f.read()

        return csv_data, video_data
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erro ao rodar scripts: {e.stderr}") from e
    except Exception as e:
        raise

# Endpoint para iniciar coleta
@app.post("/start")
def start_coleta(usuario: str = "teste_voluntario", idade: int = 22):
    try:
        csv_data, video_data = run_scripts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar arquivos: {e}")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO coleta (usuario, idade, data_coleta, arquivo_csv, video_mp4)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    """, (usuario, idade, datetime.now(), psycopg2.Binary(csv_data), psycopg2.Binary(video_data)))

    coleta_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Coleta armazenada com sucesso", "id": coleta_id}

# Endpoint para baixar CSV
@app.get("/csv/{coleta_id}")
def get_csv(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT arquivo_csv FROM coleta WHERE id = %s", (coleta_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Coleta não encontrada")
    csv_data = row[0]
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=dados.csv"})

# Endpoint para exibir vídeo
@app.get("/video/{coleta_id}")
def get_video(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT video_mp4 FROM coleta WHERE id = %s", (coleta_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Coleta não encontrada")
    video_data = row[0]
    return Response(content=video_data, media_type="video/mp4")
