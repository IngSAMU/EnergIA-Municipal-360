import json,time
import paho.mqtt.client as mqtt
from core import init_db,upsert_telemetry
BROKER="broker.hivemq.com"; PORT=1883; TOPIC="energia360/lima-demo-a91c/SJL-001/telemetry"
init_db()
def on_connect(c,u,f,rc,p=None):
    print(f"[MQTT] Conectado {BROKER}:{PORT} reason={rc}"); c.subscribe(TOPIC); print("[MQTT] Suscrito:",TOPIC)
def on_message(c,u,m):
    try:
        d=json.loads(m.payload.decode())
        r=upsert_telemetry({"node_id":"SJL-001","load_kw":float(d["load_kw"]),"voltage_v":float(d["voltage_v"]),"night":bool(d.get("night")),"repeated":bool(d.get("repeated"))})
        print(f"[WOKWI→DB] SJL-001 | IAE {r['iae']} | {r['state']}")
    except Exception as ex: print("[ERROR]",ex,m.payload)
cl=mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2,client_id=f"energia360-{int(time.time())}")
cl.on_connect=on_connect; cl.on_message=on_message
print("EnergIA Municipal 360 — Puente MQTT"); print("Topic:",TOPIC)
cl.connect(BROKER,PORT,60); cl.loop_forever()
