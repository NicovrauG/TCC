// EXEMPLO DE USO DOS COMPONENTES EM UM ÚNICO CÓDIGO


#include "ADS1X15.h"
#include "Arduino.h"

//Bibliotecas para MQTT
#include <WiFi.h>
#include <PubSubClient.h>


//Config ADS ground
ADS1115 ADS(0x48);

//Config Wifi ------ PREENCHA COM OS DADOS DA SUA REDE
const char* ssid = "";
const char* password = "";

//Config endereco MQTT, dar ifconfig e verificar ------ PREENCHA COM O IP DO SEU BROKER
const char* mqtt_server = "";

WiFiClient espClient;
PubSubClient client(espClient);

bool collecting = false;

void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  if (msg == "start") collecting = true;
  if (msg == "stop") collecting = false;
}

void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32Client")) {
      client.subscribe("emg/control"); // assina tópico de controle
    } else {
      delay(5000);
    }
  }
}

void setup() 
{
  Serial.begin(115200);
  Serial.println();
  Serial.println(__FILE__);
  Serial.print("ADS1X15_LIB_VERSION: ");
  Serial.println(ADS1X15_LIB_VERSION);
  Serial.println();
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  Wire.begin();
  Wire.setClock(400000); // seta o I2C para 400KHz, tentando aumentar o SPS

  ADS.begin();
  ADS.setDataRate(ADS1X15_DATARATE_7);   // 860 SPS
  ADS.setMode(ADS1X15_MODE_CONTINUOUS);       // modo contínuo
  ADS.requestADC(0);
}


void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  ADS.setGain(0);

  if(collecting) {
    int16_t val_0 = ADS.getValue();  
    float f = ADS.toVoltage(1);  // voltage factor
    float emg_value = val_0 * f * 1000.0; // em milivolts

    // Debug no serial
    Serial.println(emg_value, 3);

    // Publica no tópico MQTT
    char msg[50];
    snprintf(msg, 50, "%.3f", emg_value);
    client.publish("emg/sensor1", msg);
  }
}
