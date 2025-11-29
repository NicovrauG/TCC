# Nesse diretório se encontram informações referentes ao hardware e firmware utilizados.
 - `EMG.cpp` — Código que roda no microcontrolador, as funções principais são de:
   - Conectividade Wi-Fi
   - Captura dos dados vindos do sensor EMG + Conversor ADS1115 na comunicação I2C
   - Envio dos dados para o broker MQTT conforme as configurações recebidas
 -  `platformio.ini` — Arquivo de configurações para o PlatformIO.
