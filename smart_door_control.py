import network
from umqtt.simple import MQTTClient
import machine
import time
import cryptolib
import ubinascii
import settings
import json
import _thread

# WiFi 连接信息
#WIFI_SSID = "洛宝的萝卜"
#WIFI_PASSWORD = "20010203"

WIFI_SSID = "洛宝的大萝卜"
WIFI_PASSWORD = "23336666"

# MQTT 服务器信息
MQTT_BROKER = "shanghai.fuquan.moe"
MQTT_PORT = 31883
MQTT_CLIENT_ID = settings.id
MQTT_TOPIC = settings.id

# GPIO 引脚
GPIO_PIN = 13

ROLLCODE_FILE = 'rollcode.json'

def get_rollcode():
    """
    加载保存的滚码数据，如果文件不存在或数据损坏，则返回初始滚码值0。
    """
    try:
        with open(ROLLCODE_FILE, 'r') as file:
            rollcode = json.load(file)
        return rollcode
    except (OSError, ValueError):
        return 0

def save_rollcode(rollcode):
    """
    保存滚码数据到文件中。
    """
    with open(ROLLCODE_FILE, 'w') as file:
        json.dump(rollcode, file)

def check_rollcode(rollcode):
    """
    检查滚码值并保存。
    """
    usedcode = get_rollcode()
    if rollcode > usedcode:
        save_rollcode(rollcode)
        return True
    return False

def unpad(text):
    """
    PKCS7 反填充函数
    """
    padding_size = ord(text[-1])
    return text[:-padding_size]

def decrypt(key, encrypted_text):
    """
    使用 ECB 模式进行 AES 解密
    """
    cipher = cryptolib.aes(key, 1)
    encrypted_bytes = ubinascii.a2b_base64(encrypted_text)
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return unpad(decrypted_bytes.decode('utf-8'))

# 连接到 WiFi
def connect_to_wifi():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("Connecting to WiFi...")
        sta_if.active(True)
        sta_if.connect(WIFI_SSID, WIFI_PASSWORD)
        while not sta_if.isconnected():
            pass
    print("WiFi connected:", sta_if.ifconfig())

def open_lock():
    machine.Pin(GPIO_PIN, machine.Pin.OUT).value(1)
    time.sleep(1)  # 持续一秒钟
    machine.Pin(GPIO_PIN, machine.Pin.OUT).value(0)

# MQTT 消息处理函数
def mqtt_callback(topic, msg):
    print("Received message:", msg)
    msg = decrypt(settings.key, msg.decode())
    msg = json.loads(msg)
    if not check_rollcode(msg["rollingcode"]):
        return
    if msg["action"] == "open":
        open_lock()

# 连接到 MQTT 服务器并订阅主题
def connect_to_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
    client.set_callback(mqtt_callback)
    client.connect()
    print("Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC)
    print("Subscribed to topic:", MQTT_TOPIC)
    return client

def heartbeat(client):
    while True:
        print("Making a heartbeat")
        client.publish(str(settings.id)+"/heartbeat", "heartbeat")
        time.sleep(10)

# 主程序
def main():
    connect_to_wifi()
    mqtt_client = connect_to_mqtt()
    
    _thread.start_new_thread(heartbeat, (mqtt_client,))

    try:
        while True:
            mqtt_client.wait_msg()
                
    finally:
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
