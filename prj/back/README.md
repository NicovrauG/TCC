# Neste diretório estão os arquivos:
 - `comp_vision.py` — Script python para abrir a câmera e gravar um vídeo com a estimativa de pose em tempo real.
 - `emg_code.py` — Script responsável por escutar os dados que chegam no Broker MQTT, processar/filtrar os dados e gerar tanto um CSV dos dados quanto um relatório do sinal plotado em PDF.
 - `server.py` — Servidor FastAPI da aplicação WEB, responsável também por gerenciar a execução dos scripts citados.
 - `requirements.txt` — Lista de pacotes necessários para rodar o servidor e scripts.
