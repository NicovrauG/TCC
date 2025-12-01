# YD-ESP32-23

![Ilustrativo_sen0240](../../../imgs/esp32.jpg)

A **YD-ESP32-23** é a placa ESP32 utilizada no protótipo, oferecendo conectividade Wi‑Fi, Bluetooth, múltiplas interfaces periféricas e alta capacidade de processamento para aplicações de IoT, sensoriamento e sistemas embarcados.

# Dados Técnicos da YD-ESP32-23

| Característica      | Descrição                              |
| ------------------- | -------------------------------------- |
| MCU                 | ESP32 (Xtensa dual‑core)               |
| Conectividade       | Wi‑Fi 2.4 GHz, Bluetooth/BLE           |
| Tensão de Operação  | 3.3V (recomendado)                     |
| Interface I2C       | SDA = GPIO8, SCL = GPIO9               |
| Interface UART      | Suportada (GPIOs configuráveis)        |
| Interface SPI       | Suportada                              |
| Alimentação via USB | Dependendo do módulo                   |
| GPIOs Disponíveis   | Grande variedade, dependendo do modelo |

# Pinagem Básica (Visão Geral)

| Pino  | Função Principal | Observações        |
| ----- | ---------------- | ------------------ |
| GPIO8 | SDA (I2C)        | Usado no protótipo |
| GPIO9 | SCL (I2C)        | Usado no protótipo |
| 3V3   | Alimentação      | Não exceder 3.3V   |
| GND   | Terra            | Referência comum   |

> Para detalhes completos de pinagem, consulte o repositório oficial.

# Componentes Necessários

* Placa YD‑ESP32‑23
* Cabo USB (se aplicável)
* Fonte 3.3V
* Sensores/ADCs externos (como SEN0240 ou ADS1115)
* Jumpers para conexão

# Recomendações

* Utilize sempre alimentação **3.3V** — tensões superiores podem danificar o módulo.
* Mantenha **GND comum** entre todos os dispositivos do sistema.
* No barramento I2C, utilize **resistores pull‑up** caso seu módulo não possua.
* Evite cabos longos no I2C para prevenir ruído.

# Exemplo de Uso com I2C

```cpp
#include <Wire.h>

void setup() {
  Wire.begin(8, 9); // SDA = GPIO8, SCL = GPIO9
  Serial.begin(115200);
  Serial.println("ESP32 pronto!");
}

void loop() {
  // Comunicação I2C com sensores...
}
```

# Integração com o Sistema

* Comunicação I2C com **ADS1115** para leitura EMG do SEN0240.
* Envio de dados via Wi‑Fi ou USB Serial.
* Execução de filtros e processamento em tempo real.

# Aplicações

* Prototipagem de sistemas biomédicos
* Aquisição de sinais EMG
* Automação e IoT
* Processamento de sinais embarcado

# Referências

* Repositório oficial: [https://github.com/rtek1000/YD-ESP32-23](https://github.com/rtek1000/YD-ESP32-23)
