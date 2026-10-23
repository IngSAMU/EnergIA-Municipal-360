from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core import (
    STATUS_ORDER,
    connect,
    get_nodes_per_district,
    init_db,
    rebuild_nodes,
    simulate_tick,
)


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="EnergIA Municipal 360",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# COLORES Y ETIQUETAS
# ============================================================

STATE_COLORS = {
    "NORMAL": "#16a34a",
    "OBSERVACION": "#eab308",
    "ATENCION": "#f97316",
    "PRIORIDAD ALTA": "#dc2626",
}

MAP_COLORS = {
    "NORMAL": "#16a34a",
    "OBSERVACION": "#eab308",
    "ATENCION": "#f97316",
    "PRIORIDAD ALTA": "#dc2626",
    "SIMULADO": "#7e22ce",
    "ROBO SIMULADO": "#2563eb",
}

REFERENCE_LABELS = {
    "PUBLICO_REAL": "Referencia pública real",
    "REFERENCIA_ZONAL": "Zona estratégica referencial",
    "SIMULADO_MUNICIPAL": "Nodo municipal simulado",
    "SINTETICO_RIESGO": "Escenario sintético de fiscalización",
}

STATE_DISPLAY = {
    "TODOS": "TODOS",
    "NORMAL": "🟢 NORMAL",
    "OBSERVACION": "🟡 OBSERVACIÓN",
    "ATENCION": "🟠 ATENCIÓN",
    "PRIORIDAD ALTA": "🔴 PRIORIDAD ALTA",
}

DISTRICT_ORDER = [
    "San Juan de Lurigancho",
    "San Juan de Miraflores",
    "Villa María del Triunfo",
    "La Victoria",
    "Ate",
    "Cercado de Lima",
    "Callao",
    "Ventanilla",
    "San Miguel",
    "Santa Anita",
]


# ============================================================
# BASE DE DATOS
# ============================================================

init_db()


def load_nodes() -> pd.DataFrame:

    c = connect()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM nodes
        ORDER BY district, node_id
        """,
        c,
    )

    c.close()

    if df.empty:
        return df

    df["reference_label"] = (
        df["reference_type"]
        .map(REFERENCE_LABELS)
        .fillna(df["reference_type"])
    )

    # --------------------------------------------------------
    # COLOR CARTOGRÁFICO
    #
    # Azul   = robo simulado
    # Morado = nodo municipal simulado
    # Resto  = color del semáforo
    # --------------------------------------------------------

    df["map_group"] = df.apply(
        lambda r: (
            "ROBO SIMULADO"
            if r["reference_type"] == "SINTETICO_RIESGO"
            else
            "SIMULADO"
            if r["reference_type"] == "SIMULADO_MUNICIPAL"
            else
            r["state"]
        ),
        axis=1,
    )

    df["marker_size"] = df["iae"].apply(
        lambda x: 11 + min(int(x), 100) * 0.07
    )

    return df


def load_history(node_id: str) -> pd.DataFrame:

    c = connect()

    history = pd.read_sql_query(
        """
        SELECT
            ts,
            load_kw,
            voltage_v,
            iae,
            state,
            source
        FROM readings
        WHERE node_id = ?
        ORDER BY id DESC
        LIMIT 160
        """,
        c,
        params=(node_id,),
    )

    c.close()

    if not history.empty:

        history = history.iloc[::-1].copy()

        history["ts"] = pd.to_datetime(
            history["ts"],
            errors="coerce",
            utc=True,
        )

    return history


df = load_nodes()


# ============================================================
# BARRA LATERAL
# ============================================================

st.sidebar.title("⚡ EnergIA Municipal 360")

st.sidebar.caption(
    "Centro de Inteligencia Energética Territorial"
)

st.sidebar.info(
    "🟣 Morado = nodo municipal simulado. "
    "🔵 Azul = Robo de electricidad (SIMULADO). "
    "Los casos azules corresponden únicamente a "
    "escenarios sintéticos del ejercicio."
)


# ============================================================
# ADMINISTRACIÓN
# ============================================================

with st.sidebar.expander(
    "⚙️ Administración",
    expanded=True,
):

    current = get_nodes_per_district()

    density = st.selectbox(
        "Nodos por distrito",
        [10, 20, 30],
        index=[10, 20, 30].index(current),
        help=(
            "10 = 100 nodos totales; "
            "20 = 200 nodos totales; "
            "30 = 300 nodos totales."
        ),
    )

    st.caption(
        f"Configuración actual: "
        f"{current} nodos por distrito = "
        f"{current * 10} nodos totales."
    )

    if st.button(
        "Aplicar cantidad de nodos",
        use_container_width=True,
    ):

        if density != current:

            rebuild_nodes(density)

            st.session_state.clear()

            st.rerun()

        else:

            st.info(
                "La cantidad seleccionada ya está aplicada."
            )

    if st.button(
        "🔄 Nueva ronda simulada",
        use_container_width=True,
    ):

        simulate_tick()

        st.rerun()


# ============================================================
# RESTABLECER FILTROS
# ============================================================

if st.sidebar.button(
    "🧹 Restablecer filtros",
    use_container_width=True,
):

    for key in [
        "fd",
        "fc",
        "fs",
        "fr",
        "node_sel",
    ]:

        st.session_state.pop(
            key,
            None,
        )

    st.rerun()


# ============================================================
# FILTRO MUNICIPIO
# ============================================================

district_options = (
    ["TODOS"]
    +
    [
        d
        for d in DISTRICT_ORDER
        if d in set(df["district"])
    ]
)

district = st.sidebar.selectbox(
    "Municipio / distrito",
    district_options,
    key="fd",
)

s1 = (
    df
    if district == "TODOS"
    else df[df["district"] == district]
)


# ============================================================
# FILTRO TIPO DE PUNTO
# ============================================================

category_options = (
    ["TODOS"]
    +
    sorted(
        s1["category"]
        .dropna()
        .unique()
        .tolist()
    )
)

if st.session_state.get("fc") not in category_options:
    st.session_state["fc"] = "TODOS"


category = st.sidebar.selectbox(
    "Tipo de punto",
    category_options,
    key="fc",
    format_func=lambda x: (
        "🔵 ROBO DE ELECTRICIDAD (SIMULADO)"
        if x == "Robo de electricidad (SIMULADO)"
        else x
    ),
)

st.sidebar.caption(
    '🔵 "Robo de electricidad (SIMULADO)" '
    "se usa únicamente para escenarios sintéticos."
)


s2 = (
    s1
    if category == "TODOS"
    else s1[s1["category"] == category]
)


# ============================================================
# FILTRO ESTADO - SEMÁFORO
# ============================================================

state_options = (
    ["TODOS"]
    +
    [
        s
        for s in STATUS_ORDER
        if s in set(s2["state"])
    ]
)

if st.session_state.get("fs") not in state_options:
    st.session_state["fs"] = "TODOS"


state = st.sidebar.selectbox(
    "Estado — Semáforo",
    state_options,
    key="fs",
    format_func=lambda x: STATE_DISPLAY.get(
        x,
        x,
    ),
)


s3 = (
    s2
    if state == "TODOS"
    else s2[s2["state"] == state]
)


# ============================================================
# FILTRO ORIGEN
# ============================================================

reference_options = (
    ["TODOS"]
    +
    sorted(
        s3["reference_label"]
        .dropna()
        .unique()
        .tolist()
    )
)

if st.session_state.get("fr") not in reference_options:
    st.session_state["fr"] = "TODOS"


reference = st.sidebar.selectbox(
    "Origen del punto",
    reference_options,
    key="fr",
)


filtered = (
    s3
    if reference == "TODOS"
    else s3[
        s3["reference_label"]
        == reference
    ]
)


# ============================================================
# TÍTULO
# ============================================================

st.title(
    "⚡ EnergIA Municipal 360"
)

st.subheader(
    "Centro de Inteligencia Energética Territorial "
    "— Lima y Callao"
)


st.markdown(
    """
    <div class="notice">

    <b>Modelo municipal de priorización.</b>

    Los centros comerciales, estaciones, mercados,
    corredores comerciales y zonas industriales son
    referencias de alta demanda potencial.

    Los nodos morados corresponden a simulaciones
    municipales.

    Los nodos azules representan
    <b>Robo de electricidad (SIMULADO)</b>,
    exclusivamente para demostrar escenarios de
    fiscalización.

    No constituyen una acusación sobre una ubicación real.

    </div>
    """,
    unsafe_allow_html=True,
)


st.caption(
    f"Mostrando {len(filtered)} de {len(df)} nodos · "
    f"Municipio: {district} · "
    f"Tipo: {category} · "
    f"Estado: {STATE_DISPLAY.get(state, state)} · "
    f"Origen: {reference}"
)


# ============================================================
# SIN RESULTADOS
# ============================================================

if filtered.empty:

    st.warning(
        "No existen nodos para la combinación "
        "de filtros seleccionada. "
        "Selecciona TODOS o restablece los filtros."
    )

    st.stop()


# ============================================================
# KPIs EJECUTIVOS
# ============================================================

municipalities = int(
    filtered["district"].nunique()
)

high = int(
    (
        filtered["state"]
        == "PRIORIDAD ALTA"
    ).sum()
)

attention = int(
    (
        filtered["state"]
        == "ATENCION"
    ).sum()
)

observation = int(
    (
        filtered["state"]
        == "OBSERVACION"
    ).sum()
)

theft_sim = int(
    (
        filtered["reference_type"]
        == "SINTETICO_RIESGO"
    ).sum()
)

night_alerts = int(
    (
        (filtered["night"] == 1)
        &
        (filtered["iae"] >= 40)
    ).sum()
)


k1, k2, k3, k4, k5, k6, k7 = st.columns(7)


k1.metric(
    "Municipios",
    municipalities,
)

k2.metric(
    "Nodos",
    len(filtered),
)

k3.metric(
    "🔴 Prioridad alta",
    high,
)

k4.metric(
    "🟠 Atención",
    attention,
)

k5.metric(
    "🟡 Observación",
    observation,
)

k6.metric(
    "🔵 Robo simulado",
    theft_sim,
)

k7.metric(
    "🌙 Alertas nocturnas",
    night_alerts,
)


st.divider()


# ============================================================
# MAPA + DISTRIBUCIÓN DE ESTADOS
# ============================================================

left, right = st.columns([1.65, 1])

with left:
    st.markdown("### 🗺️ Mapa interactivo de puntos de interés")

    with st.container(border=True):
        st.markdown("#### 🚦 Leyenda de monitoreo")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("🟢 **Normal**")
            st.markdown("🟡 **Observación**")

        with c2:
            st.markdown("🟠 **Atención**")
            st.markdown("🔴 **Prioridad alta**")

        with c3:
            st.markdown("🟣 **Nodo municipal simulado**")
            st.markdown("🔵 **Robo de electricidad (SIMULADO)**")

        st.caption(
            "Los nodos se muestran dispersos de forma irregular. "
            "Las coordenadas son referenciales para fines de simulación."
        )

    fig = px.scatter_map(
        filtered,
        lat="lat",
        lon="lon",
        color="map_group",
        color_discrete_map=MAP_COLORS,
        size="marker_size",
        size_max=22,
        hover_name="site_name",
        hover_data={
            "node_id": True,
            "district": True,
            "category": True,
            "reference_label": True,
            "state": True,
            "load_kw": ":.2f",
            "voltage_v": ":.1f",
            "iae": True,
            "map_group": False,
            "marker_size": False,
            "lat": False,
            "lon": False,
        },
        center={
            "lat": -12.045,
            "lon": -77.035,
        },
        zoom=9,
        height=570,
    )

    fig.update_layout(
        map_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision="energia360-final",
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
        },
        key="mapa",
    )



# ============================================================
# PANEL DERECHO
# ============================================================

with right:

    st.markdown(
        "### 🚦 Distribución por estado"
    )


    state_summary = (
        filtered
        .groupby(
            "state",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "Nodos"
            }
        )
    )


    state_summary["Orden"] = (
        state_summary["state"]
        .apply(
            lambda x: (
                STATUS_ORDER.index(x)
                if x in STATUS_ORDER
                else 999
            )
        )
    )


    state_summary = (
        state_summary
        .sort_values("Orden")
    )


    state_chart = px.bar(
        state_summary,

        x="state",

        y="Nodos",

        color="state",

        color_discrete_map=STATE_COLORS,

        text="Nodos",
    )


    state_chart.update_layout(
        showlegend=False,

        xaxis_title="",

        yaxis_title="Cantidad de nodos",

        margin=dict(
            l=0,
            r=0,
            t=20,
            b=0,
        ),

        height=310,
    )


    st.plotly_chart(
        state_chart,
        width="stretch",
    )


    # ========================================================
    # ALERTAS POR MUNICIPIO
    # ========================================================

    st.markdown(
        "### 🏙️ Alertas por municipio"
    )


    alerts = (
        filtered[
            filtered["iae"] >= 40
        ]
        .groupby(
            "district",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "Alertas"
            }
        )
        .sort_values(
            "Alertas",
            ascending=False,
        )
    )


    if alerts.empty:

        st.success(
            "No hay alertas IAE ≥ 40 "
            "en la selección actual."
        )

    else:

        alert_chart = px.bar(
            alerts,

            x="Alertas",

            y="district",

            orientation="h",

            text="Alertas",
        )


        alert_chart.update_layout(
            showlegend=False,

            xaxis_title="Alertas",

            yaxis_title="",

            margin=dict(
                l=0,
                r=0,
                t=10,
                b=0,
            ),

            height=260,
        )


        st.plotly_chart(
            alert_chart,
            width="stretch",
        )


st.divider()


# ============================================================
# TOP 10 PUNTOS PARA VERIFICACIÓN
# ============================================================

st.markdown(
    "### 🚨 Top 10 puntos que requieren verificación"
)


top = (
    filtered
    .sort_values(
        [
            "iae",
            "night",
            "repeated",
        ],

        ascending=[
            False,
            False,
            False,
        ],
    )
    .head(10)
    .copy()
)


top_table = pd.DataFrame(
    {

        "Nodo":
            top["node_id"],

        "Distrito":
            top["district"],

        "Punto":
            top["site_name"],

        "Tipo":
            top["category"],

        "IAE":
            top["iae"],

        "Estado":
            top["state"].map(
                lambda x:
                    STATE_DISPLAY.get(
                        x,
                        x,
                    )
            ),

        "Motivo":
            top["reason"],

        "Acción sugerida":
            top["recommendation"],
    }
)


st.dataframe(
    top_table,
    hide_index=True,
    width="stretch",
)


st.divider()


# ============================================================
# TABLA GENERAL + DETALLE
# ============================================================

table_col, detail_col = st.columns(
    [1.55, 1]
)


with table_col:

    st.markdown(
        "### 📋 Nodos monitoreados"
    )


    general_table = pd.DataFrame(
        {

            "Nodo":
                filtered["node_id"],

            "Punto":
                filtered["site_name"],

            "Municipio":
                filtered["district"],

            "Tipo de punto":
                filtered["category"],

            "Origen":
                filtered["reference_label"],

            "Carga kW":
                filtered["load_kw"].round(2),

            "Tensión V":
                filtered["voltage_v"].round(1),

            "IAE":
                filtered["iae"],

            "Estado":
                filtered["state"].map(
                    lambda x:
                        STATE_DISPLAY.get(
                            x,
                            x,
                        )
                ),
        }
    )


    st.dataframe(
        general_table,
        hide_index=True,
        width="stretch",
        height=470,
    )


# ============================================================
# DETALLE DEL NODO
# ============================================================

with detail_col:

    st.markdown(
        "### 🔎 Detalle del nodo"
    )


    node_options = (
        filtered["node_id"]
        .tolist()
    )


    if (
        st.session_state.get("node_sel")
        not in node_options
    ):

        st.session_state["node_sel"] = (
            node_options[0]
        )


    selected_node = st.selectbox(
        "Seleccionar nodo",
        node_options,
        key="node_sel",
    )


    row = (
        filtered[
            filtered["node_id"]
            == selected_node
        ]
        .iloc[0]
    )


    st.markdown(
        f"**Punto:** "
        f"{row['site_name']}"
    )

    st.markdown(
        f"**Municipio:** "
        f"{row['district']}"
    )

    st.markdown(
        f"**Tipo:** "
        f"{row['category']}"
    )

    st.markdown(
        f"**Origen:** "
        f"{row['reference_label']}"
    )

    st.markdown(
        f"**Estado:** "
        f"{STATE_DISPLAY.get(row['state'], row['state'])}"
    )


    d1, d2, d3 = st.columns(3)


    d1.metric(
        "Carga",
        f"{row['load_kw']:.2f} kW",
    )


    d2.metric(
        "Tensión",
        f"{row['voltage_v']:.1f} V",
    )


    d3.metric(
        "IAE",
        f"{int(row['iae'])}/100",
    )


    st.markdown(
        f"**Motivo:** "
        f"{row['reason']}"
    )


    st.markdown(
        f"**Acción sugerida:** "
        f"{row['recommendation']}"
    )


    if int(row["night"]) == 1:

        st.warning(
            "🌙 Actividad nocturna detectada."
        )


    if int(row["repeated"]) == 1:

        st.warning(
            "🔁 Patrón repetitivo detectado."
        )


st.divider()


# ============================================================
# HISTORIAL DEL NODO
# ============================================================

st.markdown(
    "### 📈 Historial del nodo seleccionado"
)


history = load_history(
    selected_node
)


if history.empty:

    st.info(
        "Aún no hay historial suficiente "
        "para este nodo."
    )


else:

    hist_left, hist_right = st.columns(2)


    with hist_left:

        load_chart = px.line(
            history,

            x="ts",

            y="load_kw",

            markers=True,

            title="Carga eléctrica",
        )


        load_chart.update_layout(
            xaxis_title="",

            yaxis_title="kW",

            margin=dict(
                l=0,
                r=0,
                t=45,
                b=0,
            ),

            height=320,
        )


        st.plotly_chart(
            load_chart,
            width="stretch",
        )


    with hist_right:

        iae_chart = px.line(
            history,

            x="ts",

            y="iae",

            markers=True,

            title=(
                "Índice de Anomalía "
                "Energética (IAE)"
            ),
        )


        iae_chart.update_yaxes(
            range=[0, 100]
        )


        iae_chart.update_layout(
            xaxis_title="",

            yaxis_title="IAE",

            margin=dict(
                l=0,
                r=0,
                t=45,
                b=0,
            ),

            height=320,
        )


        st.plotly_chart(
            iae_chart,
            width="stretch",
        )


# ============================================================
# NOTA FINAL
# ============================================================

st.caption(
    "EnergIA Municipal 360 — prototipo académico. "
    "Las ubicaciones y consumos sintéticos se emplean "
    "para demostración. Un patrón anómalo prioriza una "
    "verificación; no constituye por sí solo prueba de "
    "robo, fraude o infracción."
)