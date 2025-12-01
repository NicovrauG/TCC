# Servidor
from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI
# Gerenciamento de diretorio
from pathlib import Path
# Banco de dados
import psycopg2
from ..database.db_config import Base, engine
from ..database import models
# Para rodar os outros codigos
import subprocess
# Para timestamps
from datetime import datetime
# Adicionais
import socket, json, glob, time, os, serial


app = FastAPI()

# Caminhos base (diretório onde este arquivo servidor está)
BASE_DIR = Path(__file__).resolve().parent
FRONT_DIR = BASE_DIR.parent.parent / "front"

# serve arquivos estáticos em /static
app.mount("/static", StaticFiles(directory=str(FRONT_DIR), html=True), name="static")

# rota raiz e /index.html que devolvem o index da pasta front
@app.get("/")
def root_index():
    return FileResponse(FRONT_DIR / "index.html")

@app.get("/index.html")
def index_html():
    return FileResponse(FRONT_DIR / "index.html")

@app.get("/paciente.html")
def paciente_html():
    return FileResponse(FRONT_DIR / "paciente.html")

@app.on_event("startup")
def startup_event():
    print("🔧 Criando tabelas (se não existirem)...")
    Base.metadata.create_all(bind=engine)



# Configuração do banco
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}


# Executa scripts externos (emg_code e comp_vision)
def run_scripts(rodar_dados=True, rodar_video=True, tempo_execucao=20):
    try:
        server_dir = BASE_DIR
        script1 = server_dir / "emg_code.py"   # dados
        script2 = server_dir / "comp_vision.py"    # vídeo

        videos_dir = server_dir.parent / "dados_e_videos"
        import re
        max_idx = 0
        for p in videos_dir.glob("video_*.mp4"):
            m = re.match(r"video_(\d+)\.mp4$", p.name)
            if m:
                idx = int(m.group(1))
                if idx > max_idx:
                    max_idx = idx
        next_index = max_idx + 1
        video_filename = f"video_{next_index:04d}.mp4"
        video_file_path = server_dir.parent / "dados_e_videos" / video_filename

        processes = []

        if rodar_video:
            processes.append(subprocess.Popen(
                ["python", str(script2), str(tempo_execucao), str(next_index)],
                cwd=str(server_dir)
            ))
            time.sleep(2)
        if rodar_dados:
            processes.append(subprocess.Popen(
                ["python", str(script1), str(tempo_execucao)],
                cwd=str(server_dir)
            ))
        # espera terminar
        for p in processes:
            p.wait()

        emg_file_path = server_dir.parent / "dados_e_videos" / "emg_data.csv"
        plot_file_png = server_dir.parent / "dados_e_videos" / "emg_plot.png"
        plot_file_pdf = server_dir.parent / "dados_e_videos" / "emg_plot.pdf"

        csv_data = plot_png_data = plot_pdf_data = None

        if rodar_dados:
            if not emg_file_path.exists():
                raise FileNotFoundError(f"{emg_file_path} não encontrado")
            # png é usado para mostrar na interface
            if not plot_file_png.exists():
                raise FileNotFoundError(f"{plot_file_png} não encontrado")
            # pdf é o relatorio que será salvo no banco (pode ser opcional)
            if not plot_file_pdf.exists():
                plot_pdf_data = None
            else:
                with open(plot_file_pdf, "rb") as f:
                    plot_pdf_data = f.read()

            with open(emg_file_path, "rb") as f:
                csv_data = f.read()
            with open(plot_file_png, "rb") as f:
                plot_png_data = f.read()

        if rodar_video and not video_file_path.exists():
            raise FileNotFoundError(f"{video_file_path} não encontrado")

        return csv_data, plot_png_data, plot_pdf_data, str(video_file_path) if rodar_video else None

    except Exception as e:
        raise

# utilitário para obter IP local
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Conecta sem enviar nada para descobrir o IP da interface ativa
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


# utilitário para garantir bytes vindo do banco
def _to_bytes(raw):
    if raw is None:
        return None
    if isinstance(raw, memoryview):
        return raw.tobytes()
    if isinstance(raw, bytes):
        return raw
    try:
        return bytes(raw)
    except Exception:
        raise HTTPException(status_code=500, detail="Formato de dados no banco inesperado")


@app.post("/pacientes")
async def criar_paciente(request: Request): # cria paciente
    body = await request.json()
    nome = body.get("nome")
    if not nome:
        raise HTTPException(status_code=400, detail="Campo 'nome' é obrigatório")
    idade = body.get("idade")
    peso = body.get("peso")
    altura = body.get("altura")
    genero = body.get("genero")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO paciente (nome, idade, peso, altura, genero)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (nome, idade, peso, altura, genero))
        paciente_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return {"id": paciente_id, "message": "Paciente criado com sucesso"}


@app.get("/pacientes")
def listar_pacientes(): # lista pacientes
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, idade, peso, altura, genero FROM paciente ORDER BY nome")
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    pacientes = []
    for r in rows:
        pacientes.append({
            "id": r[0],
            "nome": r[1],
            "idade": r[2],
            "peso": r[3],
            "altura": r[4],
            "genero": r[5]
        })
    return pacientes



@app.get("/pacientes/{paciente_id}/coletas")
def listar_coletas_paciente(paciente_id: int): # lista coletas de um paciente
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, data_coleta FROM coletas
            WHERE paciente_id = %s
            ORDER BY data_coleta DESC
        """, (paciente_id,))
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    coletas = []
    for row in rows:
        data = row[1]
        coletas.append({
            "id": row[0],
            "data": data.strftime("%Y%m%d_%H%M") if data else None
        })
    return coletas



@app.post("/start")
async def start_coleta(request: Request): # inicia coleta associada a um paciente
    body = await request.json()
    tempo_execucao = body.get("tempo_execucao", 20)
    paciente_id = body.get("paciente_id")
    rodar_dados = body.get("rodar_dados", True)
    rodar_video = body.get("rodar_video", True)

    if not paciente_id:
        raise HTTPException(status_code=400, detail="campo 'paciente_id' obrigatório")

    try:
        csv_data, plot_png, plot_pdf, video_path = run_scripts(rodar_dados, rodar_video, tempo_execucao)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar arquivos: {e}")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO coletas (paciente_id, data_coleta, dados_emg, grafico_emg, relatorio_pdf, video_path)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (
            paciente_id, datetime.now(),
            psycopg2.Binary(csv_data) if csv_data else None,
            psycopg2.Binary(plot_png) if plot_png else None,
            psycopg2.Binary(plot_pdf) if plot_pdf else None,
            video_path
        ))
        coleta_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
    finally:
        conn.close()

    return {"message": "Coleta armazenada com sucesso", "id": coleta_id}


@app.get("/csv/{coleta_id}")
def get_csv_json(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("SELECT dados_emg FROM coletas WHERE id = %s", (coleta_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Coleta não encontrada")

    csv_bytes = _to_bytes(row[0])
    return Response(content=csv_bytes, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="coleta_{coleta_id}.csv"'})


@app.get("/grafico/{coleta_id}")
def get_grafico(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("SELECT grafico_emg FROM coletas WHERE id = %s", (coleta_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Coleta não encontrada")
    plot_bytes = _to_bytes(row[0])
    return Response(content=plot_bytes, media_type="image/png")


@app.get("/relatorio/{coleta_id}")
def get_relatorio(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("SELECT relatorio_pdf FROM coletas WHERE id = %s", (coleta_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    if not row or row[0] is None:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    pdf_bytes = _to_bytes(row[0])
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="relatorio_{coleta_id}.pdf"'})


@app.get("/video/{coleta_id}")
def get_video(coleta_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("SELECT video_path FROM coletas WHERE id = %s", (coleta_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Coleta não encontrada")

    video_path = row[0]
    if video_path is None:
        raise HTTPException(status_code=404, detail="Caminho de vídeo não registrado")

    video_path = Path(video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado")

    ext = video_path.suffix.lower()
    if ext == ".mp4":
        media_type = "video/mp4"
    elif ext == ".webm":
        media_type = "video/webm"
    elif ext in (".ogg", ".ogv"):
        media_type = "video/ogg"
    else:
        media_type = "application/octet-stream"

    return FileResponse(str(video_path), media_type=media_type)




# ------------------ Configuração do aparelho ------------------

CONFIG_PATH = BASE_DIR / "config.json"


# utilitário para encontrar a porta serial mais recente do ESP
def find_latest_esp_port():
    ports = glob.glob("/dev/ttyACM*")
    if not ports:
        raise FileNotFoundError("Nenhum dispositivo /dev/ttyACM encontrado.")
    ports.sort(key=os.path.getctime, reverse=True)
    return ports[0]


# envia JSON de configuração via Serial para o ESP
def send_config_to_esp(config_data, retries=5):
    config = {
        "ssid": config_data["wifi_ssid"],
        "password": config_data["wifi_password"],
        "broker_ip": config_data["wifi_broker_ip"],
    }

    esp_json = json.dumps(config) + "\n"

    for attempt in range(retries):
        try:
            port = find_latest_esp_port()
            print(f"[INFO] Tentando enviar config para {port} (tentativa {attempt+1}/{retries})")
            ser = serial.Serial(port, 115200, timeout=2)
            time.sleep(2)  # espera estabilizar a porta
            ser.write(esp_json.encode())
            ser.flush()
            ser.close()
            print("[INFO] Configuração enviada com sucesso ao ESP.")
            return True
        except FileNotFoundError:
            print("[ERRO] Nenhum dispositivo /dev/ttyACM encontrado.")
            time.sleep(2)
        except serial.SerialException as e:
            print(f"[ERRO] Falha na serial: {e}")
            time.sleep(2)

    print("[ERRO] Falha ao enviar configuração após múltiplas tentativas.")
    return False


@app.get("/config/ip")
def get_ip_info():
    return {"broker_ip": get_local_ip()}

@app.post("/config/save")
async def save_config(request: Request):
    body = await request.json()
    ssid = body.get("wifi_ssid")
    password = body.get("wifi_password")

    if not ssid or not password:
        raise HTTPException(status_code=400, detail="SSID e senha são obrigatórios.")

    broker_ip = get_local_ip()
    config_data = {
        "wifi_ssid": ssid,
        "wifi_password": password,
        "wifi_broker_ip": broker_ip,
    }

    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f, indent=4)

    success = send_config_to_esp(config_data)

    return {
        "status": "ok" if success else "erro",
        "broker_ip": broker_ip
    }



