#include "ADS1X15.h"
#include "Arduino.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <LittleFS.h>

#define CONFIG_FILE "/config.json"

// =============== CONFIGURAÇÃO ADS1115 =================
ADS1115 ADS(0x48);

// =============== MQTT =================
WiFiClient espClient;
PubSubClient client(espClient);

// =============== VARIÁVEIS GLOBAIS =================
int mqtt_port = 1883;

struct Config {
  String ssid;
  String password;
  String broker_ip;
};

Config config;

// FUNCOES

bool loadConfig();
void saveConfig(const String &jsonStr);
void callback(char* topic, byte* payload, unsigned int length);
void setup_wifi();
void reconnect();


bool loadConfig() {
  if (!LittleFS.begin(true, "/littlefs")) {
    Serial.println("Erro ao montar LittleFS");
    return false;
  }

  File file = LittleFS.open(CONFIG_FILE, "r", false);
  if (!file) {
    Serial.println("Arquivo de configuração não encontrado");
    return false;
  }

  String json = "";
  while (file.available()) json += (char)file.read();
  file.close();

  Serial.print("Conteúdo do config.json lido: ");
  Serial.println(json);

  DynamicJsonDocument doc(512);
  DeserializationError error = deserializeJson(doc, json);
  if (error) {
    Serial.print("Erro ao desserializar JSON do arquivo: ");
    Serial.println(error.c_str());
    return false;
  }

  bool hasNew = doc.containsKey("wifi_ssid") || doc.containsKey("wifi_password") || doc.containsKey("wifi_broker_ip");
  bool hasOld = doc.containsKey("ssid") || doc.containsKey("password") || doc.containsKey("broker_ip");
  if (!hasNew && !hasOld) {
    Serial.println("JSON válido, mas faltam chaves esperadas (wifi_ssid/wifi_password/wifi_broker_ip ou ssid/password/broker_ip).");
    return false;
  }

  if (doc.containsKey("wifi_ssid")) config.ssid = doc["wifi_ssid"].as<String>();
  else if (doc.containsKey("ssid")) config.ssid = doc["ssid"].as<String>();
  else config.ssid = "";

  if (doc.containsKey("wifi_password")) config.password = doc["wifi_password"].as<String>();
  else if (doc.containsKey("password")) config.password = doc["password"].as<String>();
  else config.password = "";

  if (doc.containsKey("wifi_broker_ip")) config.broker_ip = doc["wifi_broker_ip"].as<String>();
  else if (doc.containsKey("broker_ip")) config.broker_ip = doc["broker_ip"].as<String>();
  else config.broker_ip = "";

  Serial.print("ssid: "); Serial.println(config.ssid);
  Serial.print("password: "); Serial.println(config.password);
  Serial.print("broker: "); Serial.println(config.broker_ip);

  return true;
}

void saveConfig(const String &jsonStr) {
  Serial.print("JSON recebido via Serial: ");
  Serial.println(jsonStr);

  DynamicJsonDocument doc(512);
  DeserializationError error = deserializeJson(doc, jsonStr);
  if (error) {
    Serial.print("Erro ao decodificar JSON recebido: ");
    Serial.println(error.c_str());
    return;
  }

  DynamicJsonDocument outDoc(512);
  if (doc.containsKey("wifi_ssid")) outDoc["wifi_ssid"] = doc["wifi_ssid"].as<const char*>();
  else if (doc.containsKey("ssid")) outDoc["wifi_ssid"] = doc["ssid"].as<const char*>();

  if (doc.containsKey("wifi_password")) outDoc["wifi_password"] = doc["wifi_password"].as<const char*>();
  else if (doc.containsKey("password")) outDoc["wifi_password"] = doc["password"].as<const char*>();

  if (doc.containsKey("wifi_broker_ip")) outDoc["wifi_broker_ip"] = doc["wifi_broker_ip"].as<const char*>();
  else if (doc.containsKey("broker_ip")) outDoc["wifi_broker_ip"] = doc["broker_ip"].as<const char*>();

  File file = LittleFS.open(CONFIG_FILE, "w", true);
  if (!file) {
    Serial.println("Erro ao abrir arquivo para escrita");
    return;
  }

  serializeJson(outDoc, file);
  file.close();

  File f2 = LittleFS.open(CONFIG_FILE, "r");
  if (f2) {
    String saved = "";
    while (f2.available()) saved += (char)f2.read();
    f2.close();
    Serial.print("Arquivo salvo (config.json): ");
    Serial.println(saved);
  }

  Serial.println("Configurações salvas, reiniciando...");
  delay(1000);
  ESP.restart();
}

// =============== CALLBACK MQTT =================
void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.print("Mensagem recebida em ");
  Serial.print(topic);
  Serial.print(": ");
  Serial.println(msg);
}

// =============== WIFI =================
void setup_wifi() {
  Serial.print("Conectando ao WiFi ");
  Serial.println(config.ssid);
  WiFi.begin(config.ssid.c_str(), config.password.c_str());
  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED && tentativas < 20) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado!");
    Serial.print("IP local: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFalha ao conectar no Wi-Fi.");
  }
}

// =============== MQTT =================
void reconnect() {
  while (!client.connected()) {
    Serial.print("Tentando conectar ao broker MQTT...");
    if (client.connect("ESP32Client")) {
      Serial.println(" conectado!");
      client.subscribe("emg/control");
    } else {
      Serial.print(" falhou, rc=");
      Serial.print(client.state());
      Serial.println(" tentando novamente em 5s");
      delay(5000);
    }
    Serial.print("ssid: "); Serial.println(config.ssid);
    Serial.print("password: "); Serial.println(config.password);
    Serial.print("broker: "); Serial.println(config.broker_ip);
    if (Serial.available()) {
      String jsonStr = Serial.readStringUntil('\n');
      jsonStr.trim();
      if (jsonStr.startsWith("{") && jsonStr.endsWith("}")) {
        saveConfig(jsonStr);
      }
    }
  }
  
}

// =============== SETUP =================
void setup() {
  Serial.begin(460800);
  delay(2000); // espera a USB estabilizar
  Serial.println("\nIniciando sistema...");

  if (!LittleFS.begin(true, "/littlefs")) {
    Serial.println("Erro ao montar LittleFS");
  }

  if (!loadConfig()) {
    Serial.println("Nenhuma config em LittleFS. Aguardando configuração via Serial (envie JSON por linha)...");
    while (!loadConfig()) {
      if (Serial.available()) {
        String jsonStr = Serial.readStringUntil('\n');
        jsonStr.trim();
        if (jsonStr.startsWith("{") && jsonStr.endsWith("}")) {
          saveConfig(jsonStr); // salva e reinicia
        } else if (jsonStr.length() > 0) {
          Serial.println("JSON inválido recebido, envie objeto JSON completo em uma linha.");
        }
      }
      delay(100);
    }
  }

  Serial.print("Config carregada: ");
  Serial.println(config.ssid);

  setup_wifi();

  client.setServer(config.broker_ip.c_str(), mqtt_port);
  client.setCallback(callback);

  Wire.begin();
  Wire.setClock(400000);
  ADS.begin();
  ADS.setDataRate(ADS1X15_DATARATE_7); // 860 SPS
  ADS.setMode(ADS1X15_MODE_CONTINUOUS);
  ADS.requestADC(0);

  Serial.println("Sistema iniciado!");
}

// =============== LOOP =================
void loop() {
  if (Serial.available()) {
    String jsonStr = Serial.readStringUntil('\n');
    jsonStr.trim();
    if (jsonStr.startsWith("{") && jsonStr.endsWith("}")) {
      saveConfig(jsonStr);
    }
  }
  if (WiFi.status() != WL_CONNECTED) {
    setup_wifi();
  }
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  ADS.setGain(0);
  int16_t val_0 = ADS.getValue();
  float f = ADS.toVoltage(1);
  float emg_value = val_0 * f * 1000.0; // mV

  char msg[50];
  snprintf(msg, 50, "%.3f", emg_value);
  if(client.connected()) {
    client.publish("emg/sensor1", msg);
  }
}
