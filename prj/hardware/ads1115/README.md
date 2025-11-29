# ADS1115 — Conversor Analógico-Digital (ADC) de Alta Resolução

![Ilustrativo_ads1115](../../../imgs/ADS1115.jpg)

## Visão Geral

O ADS1115 é um conversor analógico-digital (ADC) de 16 bits, de quatro canais (ou dois canais diferenciais), com interface I2C, produzido pela Texas Instruments. É muito usado em protótipos e projetos embarcados quando se requer maior resolução que a disponível nos ADCs internos de microcontroladores.

## Principais Características

- Resolução: 16 bits
- Interface: I2C (suporta até 3 endereços via pinos ADDR)
- Taxas de amostragem: configuráveis (8, 16, 32, 64, 128, 250, 475, 860 SPS)
- PGA (Programmable Gain Amplifier) integrado: ganhos configuráveis para medir sinais pequenos
- 4 entradas analógicas configuráveis como entradas single-ended ou 2 pares diferenciais
- Alimentação: tipicamente 2.0 V a 5.5 V
- Consumo baixo em modo contínuo e modo single-shot (por isso indicado para bateria)

## Pinout

- VCC: alimentação (2.0 V — 5.5 V)
- GND: referência terra
- SCL: clock I2C
- SDA: linha de dados I2C
- ADDR (ou A0/A1 em alguns módulos): define o endereço I2C do dispositivo (vários níveis possíveis)
- ALERT/RDY: pino de interrupção/ready (opcional, pode ser usado para indicar fim de conversão)

Observação: o nome dos pinos pode variar ligeiramente entre diferentes módulos breakout disponíveis no mercado (por exemplo, `ADDR` pode ser rotulado `ADDR0` ou `A0`).

## Endereçamento I2C

O ADS1115 possui pino ADDR que controla o último bit do endereço I2C. Dependendo da conexão, os endereços possíveis (7-bit) são:

- ADDR conectado a GND  -> 0x48
- ADDR conectado a VCC  -> 0x49
- ADDR conectado a SDA  -> 0x4A
- ADDR conectado a SCL  -> 0x4B

Confirme o endereço do seu módulo antes de comunicar via I2C.

## Modos de Operação

- Single-shot (conversão única): o ADS1115 faz uma conversão quando solicitado e volta para modo de baixo consumo.
- Continuous (contínuo): o ADS1115 converte continuamente na taxa configurada.

Para aplicações sensíveis à energia, use single-shot; para leituras contínuas em altas taxas, use continuous.

## PGA / Ganho (FSR - Full-Scale Range)

O ADS1115 possui um PGA configurável que define a faixa de entrada (FSR). Configurar corretamente o PGA melhora a resolução efetiva para sinais pequenos.

Valores típicos (ganho : FSR):

- FS = ±6.144 V  (GAIN = 2/3)
- FS = ±4.096 V  (GAIN = 1)
- FS = ±2.048 V  (GAIN = 2)
- FS = ±1.024 V  (GAIN = 4)
- FS = ±0.512 V  (GAIN = 8)
- FS = ±0.256 V  (GAIN = 16)

Escolha o ganho para maximizar a resolução sem saturar o conversor.

## Taxa de Amostragem (SPS)

Taxas suportadas típicas: 8, 16, 32, 64, 128, 250, 475, 860 SPS. Taxas maiores reduzem integração e aumentam ruído; taxas menores aumentam sensibilidade efetiva.

## Precisão e Ruído

- Resolução: 16 bits (mas a precisão útil depende de ruído, layout PCB e condicionamento de sinal)
- Drift de offset e erro de ganho variam por chip; para medições precisas considere calibração e filtragem.

## Ligação com o YD-ESP32-23

1. Conecte VCC do ADS1115 a 3.3 V (preferível com ESP32) ou 5 V se seu módulo suportar e o barramento I2C tolerar.
2. Conecte GND → GND.
3. Conecte SDA → pin SDA do ESP32 (GPIO8).
4. Conecte SCL → pin SCL do ESP32 (GPIO9).
5. Ajuste ADDR conforme necessário para evitar conflito I2C (Conectado no ground para utilizar o 0x48).

Exemplo de fiação (ESP32 comum):

- ADS1115 VCC -> ESP32 3.3V
- ADS1115 GND -> ESP32 GND
- ADS1115 SDA -> ESP32 GPIO21
- ADS1115 SCL -> ESP32 GPIO22

Observação: alguns módulos incluem resistores pull-up; caso contrário, adicione pull-ups de 4.7k–10k em SDA e SCL.

Notas:
- Use a biblioteca `Adafruit_ADS1X15` para facilitar a configuração.
- O fator de conversão (LSB) depende do ganho configurado; consulte a documentação da biblioteca/ADS1115 para obter o valor correto.

## Limitações

- Apesar de 16 bits, a resolução efetiva pode ser bem menor dependendo do ruído e do condicionamento do sinal.
- Não é isolado galvanicamente; para medições em sistemas com referencia de terra diferente, tome cuidado com aterramento.

## Recursos / Referências

- Datasheet TI ADS1115: https://www.ti.com/product/ADS1115
- Biblioteca Adafruit ADS1X15: https://github.com/adafruit/Adafruit_ADS1X15

---
