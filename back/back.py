from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import psycopg2
import subprocess
from datetime import datetime
import csv
from io import StringIO

app = FastAPI()

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
    "dbname": "projetoemg",
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

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        video_filename = f"video_{timestamp}.mp4"
        video_file_path = server_dir.parent / "dados_e_videos" / video_filename

        env = {"VIDEO_PATH": str(video_file_path)}
        p1 = subprocess.Popen(["python", str(script1)], cwd=str(server_dir))
        p2 = subprocess.Popen(["python", str(script2)], cwd=str(server_dir))

        p1.wait()
        p2.wait()

        # supondo que Server_coletor grava dados.csv e video.mp4 no mesmo dir
        emg_file_path = server_dir.parent / "dados_e_videos" / "emg_data.csv"
        plot_file_path = server_dir.parent / "dados_e_videos" / "emg_plot.png"

        if not emg_file_path.exists() or not video_file_path.exists():
            raise FileNotFoundError("dados.csv ou video.mp4 não gerados pelos scripts")

        with open(emg_file_path, "rb") as f:
            csv_data = f.read()

        with open(plot_file_path, "rb") as f:
            plot_data = f.read()

        return csv_data, plot_data, str(video_file_path)
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erro ao rodar scripts: {e.stderr}") from e
    except Exception as e:
        raise

# Endpoint para iniciar coleta
@app.post("/start")
async def start_coleta(request: Request):
    body = await request.json()
    usuario = body.get("nome", "Anônimo")
    idade = body.get("idade", 0)

    try:
        csv_data, plot_data, video_path = run_scripts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar arquivos: {e}")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO coleta (nome, idade, data_coleta, dados_emg, grafico_emg, video_path)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    """, (usuario, idade, datetime.now(), psycopg2.Binary(csv_data), psycopg2.Binary(plot_data), video_path))

    coleta_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Coleta armazenada com sucesso", "id": coleta_id}

@app.get("/coletas")
def listar_coletas():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id, nome, idade, data_coleta FROM coleta ORDER BY data_coleta DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    coletas = []
    for row in rows:
        coletas.append({
            "id": row[0],
            "nome": row[1],
            "idade": row[2],
            "data": row[3].strftime("%Y-%m-%d %H:%M:%S")
        })
    return coletas

@app.get("/csv/{coleta_id}")
def get_csv_json(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT dados_emg FROM coleta WHERE id = %s", (coleta_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Coleta não encontrada")

    raw = row[0]
    # raw pode ser bytes, memoryview ou outro tipo; garantir bytes antes de retornar/decodificar
    if isinstance(raw, memoryview):
        csv_bytes = raw.tobytes()
    elif isinstance(raw, bytes):
        csv_bytes = raw
    else:
        # tenta converter com bytes()
        try:
            csv_bytes = bytes(raw)
        except Exception:
            raise HTTPException(status_code=500, detail="Formato de dados no banco inesperado")

    # Retorna como arquivo CSV para download (Content-Disposition)
    return Response(content=csv_bytes, media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="coleta_{coleta_id}.csv"'})

@app.get("/grafico/{coleta_id}")
def get_grafico(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT grafico_emg FROM coleta WHERE id = %s", (coleta_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Coleta não encontrada")
    return Response(content=row[0], media_type="image/png")

# Endpoint para exibir vídeo
@app.get("/video/{coleta_id}")
def get_video(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT video_path FROM coleta WHERE id = %s", (coleta_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Coleta não encontrada")

    video_path = Path(row[0])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado")

    ext = video_path.suffix.lower()
    if ext == ".mp4":
        media_type = "video/mp4"
    elif ext == ".webm":
        media_type = "video/webm"
    elif ext == ".ogg" or ext == ".ogv":
        media_type = "video/ogg"
    else:
        media_type = "application/octet-stream"

    return FileResponse(str(video_path), media_type=media_type)
