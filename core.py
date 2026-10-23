from __future__ import annotations
import random, sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "energia360.db"

DISTRICTS = [
    ("SJL","San Juan de Lurigancho",-11.9635,-76.9860),
    ("SJM","San Juan de Miraflores",-12.1595,-76.9722),
    ("VMT","Villa María del Triunfo",-12.1620,-76.9430),
    ("LVI","La Victoria",-12.0648,-77.0304),
    ("ATE","Ate",-12.0260,-76.9210),
    ("LIM","Cercado de Lima",-12.0464,-77.0428),
    ("CAL","Callao",-12.0566,-77.1181),
    ("VEN","Ventanilla",-11.8770,-77.1250),
    ("SMI","San Miguel",-12.0774,-77.0928),
    ("SAN","Santa Anita",-12.0432,-76.9700),
]

# Dispersión cartográfica REFERENCIAL por distrito.
# Evita patrones circulares/anillos y separa los nodos de forma irregular.
# NO representa coordenadas exactas de instalaciones reales.
DISTRICT_SPREAD = {
    "SJL": (0.032, 0.020),
    "SJM": (0.020, 0.018),
    "VMT": (0.030, 0.026),
    "LVI": (0.014, 0.012),
    "ATE": (0.030, 0.028),
    "LIM": (0.016, 0.014),
    "CAL": (0.024, 0.024),
    "VEN": (0.032, 0.028),
    "SMI": (0.014, 0.014),
    "SAN": (0.014, 0.014),
}

def generate_dispersed_points(code, lat0, lon0, count, seed):
    rng = random.Random(seed)
    lat_span, lon_span = DISTRICT_SPREAD.get(code, (0.018, 0.018))
    points = []
    min_sep = 0.0022 if count <= 10 else 0.0015 if count <= 20 else 0.0011

    for _ in range(count):
        chosen = None
        for _attempt in range(150):
            lat = lat0 + rng.uniform(-lat_span, lat_span)
            lon = lon0 + rng.uniform(-lon_span, lon_span)

            if all((((lat-p[0])**2 + (lon-p[1])**2) ** 0.5) >= min_sep for p in points):
                chosen = (lat, lon)
                break

        if chosen is None:
            chosen = (
                lat0 + rng.uniform(-lat_span, lat_span),
                lon0 + rng.uniform(-lon_span, lon_span),
            )

        points.append(chosen)

    return points

STATUS_ORDER = ["NORMAL","OBSERVACION","ATENCION","PRIORIDAD ALTA"]

# Catálogo de referencia: puntos reales/públicos + zonas estratégicas.
# NO significa que sean los mayores consumidores medidos por una empresa eléctrica.
REFERENCE_SITES = {
    "SJL": [
        ("Mall Aventura San Juan de Lurigancho","Centro comercial","PUBLICO_REAL",5.0),
        ("Línea 1 - Estación Bayóvar","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación Santa Rosa","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación San Martín","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación San Carlos","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación Los Postes","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación Los Jardines","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación Pirámide del Sol","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación Caja de Agua","Transporte masivo","PUBLICO_REAL",4.0),
        ("Eje comercial Próceres de la Independencia","Corredor comercial","REFERENCIA_ZONAL",3.5),
    ],
    "SJM": [
        ("Mall del Sur","Centro comercial","PUBLICO_REAL",5.5),
        ("Línea 1 - Estación Atocongo","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación San Juan","Transporte masivo","PUBLICO_REAL",4.0),
        ("Eje comercial Ciudad de Dios","Corredor comercial","REFERENCIA_ZONAL",3.8),
        ("Mercado / comercio Ciudad de Dios","Mercado / comercio","REFERENCIA_ZONAL",3.5),
        ("Corredor Panamericana Sur - Atocongo","Corredor comercial","REFERENCIA_ZONAL",4.0),
        ("Zona de talleres - Pamplona","Talleres / servicios","REFERENCIA_ZONAL",2.8),
        ("Zona comercial María Auxiliadora","Comercio / servicios","REFERENCIA_ZONAL",3.0),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
    "VMT": [
        ("Real Plaza Villa María","Centro comercial","PUBLICO_REAL",5.0),
        ("Línea 1 - Estación Villa María","Transporte masivo","PUBLICO_REAL",4.0),
        ("Línea 1 - Estación María Auxiliadora","Transporte masivo","PUBLICO_REAL",4.0),
        ("Zona industrial de Villa María del Triunfo","Zona industrial","REFERENCIA_ZONAL",6.0),
        ("Eje industrial / talleres Nueva Esperanza","Talleres / industria ligera","REFERENCIA_ZONAL",4.5),
        ("Corredor comercial Av. Pachacútec","Corredor comercial","REFERENCIA_ZONAL",3.5),
        ("Mercado / comercio José Gálvez","Mercado / comercio","REFERENCIA_ZONAL",3.2),
        ("Servicios urbanos - sector Cercado VMT","Servicios","REFERENCIA_ZONAL",2.8),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
    "LVI": [
        ("Emporio Comercial de Gamarra","Gran conglomerado comercial","PUBLICO_REAL",6.0),
        ("Línea 1 - Estación Gamarra","Transporte masivo","PUBLICO_REAL",4.0),
        ("Mercado / comercio Av. Aviación","Mercado / comercio","REFERENCIA_ZONAL",3.5),
        ("Corredor comercial Av. México","Corredor comercial","REFERENCIA_ZONAL",3.5),
        ("Zona de talleres automotrices","Talleres / servicios","REFERENCIA_ZONAL",3.5),
        ("Galerías textiles - Gamarra sector A","Galerías / comercio","REFERENCIA_ZONAL",4.0),
        ("Galerías textiles - Gamarra sector B","Galerías / comercio","REFERENCIA_ZONAL",4.0),
        ("Almacenes logísticos - sector A","Almacén / logística","REFERENCIA_ZONAL",3.5),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
    "ATE": [
        ("Real Plaza Puruchuco","Centro comercial","PUBLICO_REAL",6.0),
        ("Real Plaza Santa Clara","Centro comercial","PUBLICO_REAL",5.0),
        ("Zona comercial CERES","Conglomerado comercial","PUBLICO_REAL",4.0),
        ("Mercado Josfel","Mercado / comercio","PUBLICO_REAL",4.0),
        ("Zona industrial Santa Clara","Zona industrial","REFERENCIA_ZONAL",6.0),
        ("Zona industrial Ate-Vitarte","Zona industrial","REFERENCIA_ZONAL",6.0),
        ("Corredor Carretera Central","Corredor comercial / industrial","REFERENCIA_ZONAL",5.0),
        ("Huaycán - eje comercial","Corredor comercial","REFERENCIA_ZONAL",3.5),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
    "LIM": [
        ("Real Plaza Centro Cívico","Centro comercial","PUBLICO_REAL",5.0),
        ("Mesa Redonda","Gran conglomerado comercial","REFERENCIA_ZONAL",5.5),
        ("Mercado Central de Lima","Mercado / comercio","REFERENCIA_ZONAL",4.5),
        ("Línea 1 - Estación Presbítero Maestro","Transporte masivo","PUBLICO_REAL",4.0),
        ("Centro Histórico - eje comercial","Corredor comercial","REFERENCIA_ZONAL",4.0),
        ("Zona comercial Av. Abancay","Corredor comercial","REFERENCIA_ZONAL",4.0),
        ("Galerías / almacenes Barrios Altos","Galerías / almacenes","REFERENCIA_ZONAL",3.8),
        ("Servicios públicos - Centro de Lima","Infraestructura pública","REFERENCIA_ZONAL",3.5),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
    "CAL": [
        ("Minka - complejo comercial","Centro comercial","PUBLICO_REAL",5.0),
        ("Zona portuaria del Callao","Puerto / logística","REFERENCIA_ZONAL",7.0),
        ("Aeropuerto Jorge Chávez - entorno logístico","Infraestructura aeroportuaria","REFERENCIA_ZONAL",7.0),
        ("Terminales / depósitos logísticos","Logística / almacenes","REFERENCIA_ZONAL",5.5),
        ("Zona industrial Gambetta","Zona industrial","REFERENCIA_ZONAL",6.0),
        ("Mercado / comercio Callao Cercado","Mercado / comercio","REFERENCIA_ZONAL",3.5),
        ("Corredor Av. Argentina - Callao","Corredor industrial / comercial","REFERENCIA_ZONAL",5.0),
        ("Almacenes portuarios - sector A","Almacén / logística","REFERENCIA_ZONAL",5.0),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
    "VEN": [
        ("Zona industrial de Ventanilla","Zona industrial","REFERENCIA_ZONAL",6.0),
        ("Parque industrial / talleres - sector A","Talleres / industria ligera","REFERENCIA_ZONAL",4.5),
        ("Eje comercial Ventanilla Cercado","Corredor comercial","REFERENCIA_ZONAL",3.5),
        ("Mercado / comercio Mi Perú-Ventanilla","Mercado / comercio","REFERENCIA_ZONAL",3.2),
        ("Depósitos logísticos - sector A","Almacén / logística","REFERENCIA_ZONAL",4.5),
        ("Depósitos logísticos - sector B","Almacén / logística","REFERENCIA_ZONAL",4.5),
        ("Servicios urbanos - Pachacútec","Servicios","REFERENCIA_ZONAL",3.0),
        ("Talleres / metalmecánica - sector B","Talleres / industria ligera","REFERENCIA_ZONAL",4.0),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
    "SMI": [
        ("Plaza San Miguel","Centro comercial","PUBLICO_REAL",5.5),
        ("Parque de las Leyendas - entorno de servicios","Entretenimiento / servicios","REFERENCIA_ZONAL",4.0),
        ("Corredor comercial Av. La Marina","Corredor comercial","REFERENCIA_ZONAL",4.0),
        ("Open Plaza / comercio La Marina","Centro comercial / retail","REFERENCIA_ZONAL",4.5),
        ("Clúster gastronómico / comercial","Comercio / servicios","REFERENCIA_ZONAL",3.2),
        ("Edificios multifamiliares - sector A","Residencial intensivo","REFERENCIA_ZONAL",3.0),
        ("Edificios multifamiliares - sector B","Residencial intensivo","REFERENCIA_ZONAL",3.0),
        ("Talleres / servicios - sector A","Talleres / servicios","REFERENCIA_ZONAL",2.8),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
    "SAN": [
        ("Mall Aventura Santa Anita","Centro comercial","PUBLICO_REAL",5.5),
        ("Gran Mercado Mayorista de Lima","Mercado mayorista","REFERENCIA_ZONAL",6.5),
        ("Corredor Carretera Central - Santa Anita","Corredor comercial / logístico","REFERENCIA_ZONAL",4.5),
        ("Mercados y almacenes - sector A","Mercado / almacén","REFERENCIA_ZONAL",4.5),
        ("Mercados y almacenes - sector B","Mercado / almacén","REFERENCIA_ZONAL",4.5),
        ("Zona de talleres - sector A","Talleres / servicios","REFERENCIA_ZONAL",3.2),
        ("Zona comercial Los Ruiseñores","Corredor comercial","REFERENCIA_ZONAL",3.2),
        ("Servicios logísticos - sector A","Logística / almacenes","REFERENCIA_ZONAL",4.0),
        ("Nodo municipal de alumbrado - sector A","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
        ("Nodo municipal de alumbrado - sector B","Infraestructura municipal","SIMULADO_MUNICIPAL",2.0),
    ],
}

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def classify_iae(load_kw, voltage_v, night, repeated, baseline_kw=2.0):
    b=max(float(baseline_kw or 2.0),0.5); r=float(load_kw)/b; s=0; reasons=[]
    if r>=4: s+=55; reasons.append("demanda ≥4× patrón")
    elif r>=3: s+=45; reasons.append("demanda ≥3× patrón")
    elif r>=2: s+=30; reasons.append("demanda ≥2× patrón")
    elif r>=1.5: s+=20; reasons.append("demanda ≥1.5× patrón")
    elif r>=1.2: s+=10; reasons.append("demanda sobre patrón")
    va=voltage_v<205 or voltage_v>240
    if va: s+=10; reasons.append("tensión fuera de 205–240 V")
    if night and r>=1.5: s+=30; reasons.append("actividad nocturna atípica")
    if repeated and r>=1.2: s+=15; reasons.append("patrón repetitivo")
    if r>=4 and va: s+=15; reasons.append("combinación severa carga+tensión")
    s=max(0,min(100,int(round(s))))
    if s>=80: state="PRIORIDAD ALTA"; rec="Priorizar verificación técnica y abrir caso de evaluación."
    elif s>=60: state="ATENCION"; rec="Programar revisión técnica y contrastar con historial."
    elif s>=40: state="OBSERVACION"; rec="Monitorear tendencia y validar persistencia."
    else: state="NORMAL"; rec="Continuar monitoreo."
    return s,state,(" + ".join(reasons) if reasons else "Comportamiento dentro del patrón esperado"),rec

def connect():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB_PATH,timeout=30,check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL;")
    return c

def init_db(nodes_per_district=10):
    c=connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT);
    CREATE TABLE IF NOT EXISTS nodes(
      node_id TEXT PRIMARY KEY,district_code TEXT,district TEXT,site_name TEXT,category TEXT,reference_type TEXT,
      lat REAL,lon REAL,baseline_kw REAL,load_kw REAL,voltage_v REAL,night INTEGER,repeated INTEGER,
      iae INTEGER,state TEXT,reason TEXT,recommendation TEXT,source TEXT,last_seen TEXT);
    CREATE TABLE IF NOT EXISTS readings(
      id INTEGER PRIMARY KEY AUTOINCREMENT,node_id TEXT,ts TEXT,load_kw REAL,voltage_v REAL,
      night INTEGER,repeated INTEGER,iae INTEGER,state TEXT,source TEXT);
    """)
    if c.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]==0:
        seed_nodes(c,nodes_per_district)
    c.commit(); c.close()

def get_nodes_per_district():
    c=connect()
    row=c.execute("SELECT v FROM settings WHERE k='nodes_per_district'").fetchone()
    c.close()
    return int(row[0]) if row else 10

def rebuild_nodes(nodes_per_district):
    if nodes_per_district not in (10,20,30):
        raise ValueError("Solo se permiten 10, 20 o 30 nodos por distrito.")
    if DB_PATH.exists():
        DB_PATH.unlink()
    c=connect()
    c.executescript("""
    CREATE TABLE settings(k TEXT PRIMARY KEY,v TEXT);
    CREATE TABLE nodes(
      node_id TEXT PRIMARY KEY,district_code TEXT,district TEXT,site_name TEXT,category TEXT,reference_type TEXT,
      lat REAL,lon REAL,baseline_kw REAL,load_kw REAL,voltage_v REAL,night INTEGER,repeated INTEGER,
      iae INTEGER,state TEXT,reason TEXT,recommendation TEXT,source TEXT,last_seen TEXT);
    CREATE TABLE readings(
      id INTEGER PRIMARY KEY AUTOINCREMENT,node_id TEXT,ts TEXT,load_kw REAL,voltage_v REAL,
      night INTEGER,repeated INTEGER,iae INTEGER,state TEXT,source TEXT);
    """)
    seed_nodes(c,nodes_per_district)
    c.commit(); c.close()

def seed_nodes(c,nodes_per_district):
    c.execute("INSERT OR REPLACE INTO settings(k,v) VALUES('nodes_per_district',?)",(str(nodes_per_district),))
    rng=random.Random(360+nodes_per_district)

    for code,dist,lat0,lon0 in DISTRICTS:
        base_sites=list(REFERENCE_SITES[code])

        # Garantiza que incluso con 10 nodos por distrito exista
        # un caso sintético visible en "Tipo de punto":
        # "Robo de electricidad (SIMULADO)".
        # Se sustituye únicamente el nodo 10 de referencia del distrito;
        # NO se etiqueta ninguna ubicación real como robo.
        base_sites[9] = (
            "Caso simulado — posible robo de electricidad / conexión irregular",
            "Robo de electricidad (SIMULADO)",
            "SINTETICO_RIESGO",
            2.2,
        )

        # Nodos 11-30: celdas sintéticas para fiscalización/riesgo.
        for j in range(11,nodes_per_district+1):
            if j % 4 == 0:
                nm=f"Caso simulado {j-10} — ROBO DE ELECTRICIDAD"
                cat="Robo de electricidad (SIMULADO)"
                ref="SINTETICO_RIESGO"
                base=2.2
            elif j % 4 == 1:
                nm=f"Alumbrado / tablero municipal {j-10}"
                cat="Infraestructura municipal"
                ref="SIMULADO_MUNICIPAL"
                base=2.0
            elif j % 4 == 2:
                nm=f"Taller / depósito simulado {j-10} — posible ROBO DE ELECTRICIDAD"
                cat="Robo de electricidad (SIMULADO)"
                ref="SINTETICO_RIESGO"
                base=3.0
            else:
                nm=f"Comercio vecinal de referencia {j-10}"
                cat="Comercio vecinal"
                ref="SIMULADO_MUNICIPAL"
                base=2.5
            base_sites.append((nm,cat,ref,base))

        dispersed = generate_dispersed_points(
            code,
            lat0,
            lon0,
            nodes_per_district,
            seed=3600 + nodes_per_district + sum(ord(ch) for ch in code),
        )

        for i,(site,cat,ref,base) in enumerate(base_sites[:nodes_per_district],1):
            nid=f"{code}-{i:03d}"

            # Posición irregular y dispersa dentro del distrito.
            # Es REFERENCIAL para el ejercicio; no corresponde a una coordenada real exacta.
            lat, lon = dispersed[i-1]

            source="WOKWI-LAB" if nid=="SJL-001" else "SIMULADOR"
            load=base*rng.uniform(.75,1.18)
            volt=rng.uniform(216,226)
            night=False; rep=False

            # Algunos nodos sintéticos de riesgo arrancan con anomalía para demostrar fiscalización.
            if ref=="SINTETICO_RIESGO" and i%4==0:
                load=base*rng.uniform(3.2,4.8)
                volt=rng.choice([rng.uniform(197,204),rng.uniform(242,249)])
                night=True
                rep=True

            iae,state,reason,rec=classify_iae(load,volt,night,rep,base)
            ts=now_iso()
            vals=(nid,code,dist,site,cat,ref,lat,lon,base,round(load,2),round(volt,1),int(night),int(rep),iae,state,reason,rec,source,ts)
            c.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",vals)
            c.execute("""INSERT INTO readings(node_id,ts,load_kw,voltage_v,night,repeated,iae,state,source)
                         VALUES(?,?,?,?,?,?,?,?,?)""",
                      (nid,ts,round(load,2),round(volt,1),int(night),int(rep),iae,state,source))

def simulate_tick():
    init_db()
    c=connect(); rng=random.Random()
    for nid,base,oldl,oldv,ref in c.execute("SELECT node_id,baseline_kw,load_kw,voltage_v,reference_type FROM nodes WHERE source='SIMULADOR'").fetchall():
        p=rng.random(); night=rng.random()<.12; rep=rng.random()<.08
        if ref=="SINTETICO_RIESGO": p*=0.55
        if p<.08:
            load=base*rng.uniform(3.5,5.0); volt=rng.choice([rng.uniform(194,204),rng.uniform(241,249)])
            night=rng.random()<.75; rep=rng.random()<.70
        elif p<.20:
            load=base*rng.uniform(1.7,3.0); volt=rng.uniform(208,238); night=rng.random()<.40
        else:
            load=oldl*.75+base*rng.uniform(.78,1.22)*.25; volt=oldv*.78+rng.uniform(216,226)*.22
        iae,state,reason,rec=classify_iae(load,volt,night,rep,base); ts=now_iso()
        c.execute("""UPDATE nodes SET load_kw=?,voltage_v=?,night=?,repeated=?,iae=?,state=?,reason=?,recommendation=?,last_seen=? WHERE node_id=?""",
                  (round(load,2),round(volt,1),int(night),int(rep),iae,state,reason,rec,ts,nid))
        c.execute("""INSERT INTO readings(node_id,ts,load_kw,voltage_v,night,repeated,iae,state,source)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (nid,ts,round(load,2),round(volt,1),int(night),int(rep),iae,state,"SIMULADOR"))
    c.commit(); c.close()

def upsert_telemetry(payload):
    init_db()
    nid=payload.get("node_id","SJL-001")
    c=connect()
    row=c.execute("SELECT baseline_kw FROM nodes WHERE node_id=?",(nid,)).fetchone()
    if not row:
        c.close(); raise ValueError("Nodo no existe")
    base=row[0]; load=float(payload["load_kw"]); volt=float(payload["voltage_v"])
    night=bool(payload.get("night")); rep=bool(payload.get("repeated"))
    iae,state,reason,rec=classify_iae(load,volt,night,rep,base); ts=now_iso()
    c.execute("""UPDATE nodes SET load_kw=?,voltage_v=?,night=?,repeated=?,iae=?,state=?,reason=?,recommendation=?,source='WOKWI-LAB',last_seen=? WHERE node_id=?""",
              (round(load,2),round(volt,1),int(night),int(rep),iae,state,reason,rec,ts,nid))
    c.execute("""INSERT INTO readings(node_id,ts,load_kw,voltage_v,night,repeated,iae,state,source)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
              (nid,ts,round(load,2),round(volt,1),int(night),int(rep),iae,state,"WOKWI-LAB"))
    c.commit(); c.close()
    return {"node_id":nid,"iae":iae,"state":state}
