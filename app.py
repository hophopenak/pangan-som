import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from difflib import get_close_matches
import plotly.express as px

# ===========================
# 1️⃣ Konfigurasi Halaman
# ===========================
st.set_page_config(
    page_title="Dashboard Ketahanan Pangan Sumatera",
    layout="wide",
    page_icon="🌾"
)

# ---- CUSTOM CSS ----
st.markdown("""
<style>
.main-title {text-align:center; font-size:40px; color:#2d6a4f; font-weight:bold;}
.sub-header {text-align:center; font-size:18px; color:#40916c; margin-bottom:20px;}
[data-testid="stSidebar"] {background-color: #f1faee;}
.dataframe th {background-color:#40916c; color:white; text-align:center;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>📊 Dashboard Ketahanan Pangan Pulau Sumatera</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Analisis klasterisasi ketahanan pangan kabupaten/kota se-Sumatera</p>", unsafe_allow_html=True)

# ===========================
# 2️⃣ Load Data
# ===========================
@st.cache_data
def load_data():

    # Load file
    gdf = gpd.read_file("Sumatera.shp")
    df_cluster = pd.read_excel("hasil_cluster_som.xlsx")

    # --- CLEANING ---
    def clean_name(x):
        if pd.isna(x):
            return ""
        x = str(x).upper().replace("KABUPATEN","").replace("KOTA","").strip()
        return " ".join(x.split())

    gdf["NAME_CLEAN"] = gdf["NAME_2"].apply(clean_name)
    df_cluster["Kab_CLEAN"] = df_cluster["Kabupaten/Kota"].apply(clean_name)

    # --- MERGE AWAL ---
    merged = gdf.merge(
        df_cluster,
        left_on="NAME_CLEAN",
        right_on="Kab_CLEAN",
        how="left"
    )

    # --- FUZZY MATCHING UNTUK YG TIDAK KETEMU ---
    unmatched = merged[merged["Cluster"].isna()]

    for idx, row in unmatched.iterrows():
        match = get_close_matches(row["NAME_CLEAN"], df_cluster["Kab_CLEAN"], n=1, cutoff=0.75)
        if match:
            matched_row = df_cluster[df_cluster["Kab_CLEAN"] == match[0]].iloc[0]
            for col in df_cluster.columns:
                merged.at[idx, col] = matched_row[col]

    # --- LABEL KATEGORI ---
    kategori_dict = {
        0: "Sangat Tahan",
        1: "Agak Tahan",
        2: "Agak Rentan",
        3: "Rentan",
        4: "Tahan",
        5: "Sangat Rentan"
    }

    if "Kategori_Ketahanan_Pangan" not in merged.columns:
        merged["Kategori_Ketahanan_Pangan"] = merged["Cluster"].map(kategori_dict)

    return merged

sumatera = load_data()

# ===========================
# 3️⃣ Sidebar
# ===========================
st.sidebar.header("🔍 Filter dan Informasi")

provinsi_list = sorted(sumatera["NAME_1"].unique())
selected_provinsi = st.sidebar.selectbox("Pilih Provinsi", provinsi_list)

filtered_data = sumatera[sumatera["NAME_1"] == selected_provinsi]

st.sidebar.markdown("---")
st.sidebar.write("**Indikator Utama**")
st.sidebar.markdown("""
- 🟢 IKP – Indeks Ketahanan Pangan  
- 🌾 Produktivitas Padi & Produksi Padi  
- 💰 PDRB – ekonomi daerah  
- 👥 RLS, UHH, TPAK, P0, PPK
""")
st.sidebar.markdown("---")

# ===========================
# 4️⃣ Warna Per Cluster
# ===========================
color_dict = {
    0:"#f4a261",     # Sangat Tahan
    1:"#52b69a",     # Agak Tahan
    2:"#2d6a4f",     # Agak Rentan
    3:"#d62828",     # Rentan
    4:"#f4d35e",     # Tahan
    5:"#264653"      # Sangat Rentan
}

# ===========================
# 5️⃣ Ringkasan Cluster + Metrics + Pie Chart
# ===========================
st.subheader(f"📈 Ringkasan Cluster {selected_provinsi}")

col_metrics = st.columns(4)
col_metrics[0].metric("IKP Rata-rata", f"{filtered_data['IKP'].mean():.2f}")
col_metrics[1].metric("Produktivitas Padi", f"{filtered_data['Produktivitas_Padi'].mean():.2f} ku/ha")
col_metrics[2].metric("Produksi Padi", f"{filtered_data['Produksi_Padi'].sum():,.0f} ton")
col_metrics[3].metric("PDRB", f"{filtered_data['PDRB'].sum():,.0f}")

# Ringkasan cluster tabel
cluster_summary = (
    filtered_data.groupby("Cluster")
    .agg(
        Jumlah_Kabupaten=("NAME_2", "count"),
        IKP_Rata2=("IKP", "mean"),
        Produktivitas_Rata2=("Produktivitas_Padi", "mean"),
        Produksi_Padi_Rata2=("Produksi_Padi", "mean"),
        PDRB_Rata2=("PDRB", "mean")
    )
    .reset_index()
)

cluster_labels = {
    0:"Sangat Tahan",
    1:"Agak Tahan",
    2:"Agak Rentan",
    3:"Rentan",
    4:"Tahan",
    5:"Sangat Rentan"
}

cluster_summary["Kategori"] = cluster_summary["Cluster"].map(cluster_labels)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("#### Tabel Ringkasan Cluster")
    
    def highlight_cat(val):
        color_map = {
            "Sangat Tahan": "#264653",
            "Rentan": "#d62828",
            "Agak Tahan": "#52b69a",
            "Tahan": "#f4d35e",
            "Sangat Rentan": "#264653",
            "Agak Rentan": "2d6a4f"
        }
        return f"background-color: {color_map.get(val, '#ffffff')}; color:white; font-weight:bold;"

    st.dataframe(
        cluster_summary.style.applymap(highlight_cat, subset=["Kategori"]),
        height=400
    )

with col2:
    st.markdown("#### Distribusi Cluster")
    pie_df = cluster_summary[["Kategori", "Jumlah_Kabupaten"]]
    fig = px.pie(
        pie_df,
        values="Jumlah_Kabupaten",
        names="Kategori",
        title="Distribusi Cluster",
        color="Kategori",
        color_discrete_map=color_dict
    )
    fig.update_traces(textinfo="percent+label", pull=[0.03]*len(pie_df))
    st.plotly_chart(fig, use_container_width=True)

# ===========================
# 6️⃣ Peta Klaster
# ===========================
st.subheader(f"🗺️ Peta Ketahanan Pangan Provinsi {selected_provinsi}")

center = filtered_data.geometry.centroid.unary_union.centroid

m = folium.Map(
    location=[center.y, center.x],
    zoom_start=7,
    tiles="CartoDB positron"
)

folium.GeoJson(
    filtered_data,
    style_function=lambda feature: {
        "fillColor": color_dict.get(feature["properties"].get("Cluster"), "#cccccc"),
        "color": "black",
        "weight": 0.8,
        "fillOpacity": 0.75
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["NAME_2", "Cluster", "Kategori_Ketahanan_Pangan"],
        aliases=["Daerah", "Cluster", "Kategori"],
        localize=True
    )
).add_to(m)

st_folium(m, width=980, height=600)

# ===========================
# 7️⃣ Tabel Data Kabupaten/Kota
# ===========================
with st.expander("📋 Lihat Data Kabupaten/Kota"):
    st.dataframe(
        filtered_data[
            ["NAME_1", "NAME_2", "Cluster", "Kategori_Ketahanan_Pangan", "IKP", "Produksi_Padi", "PDRB"]
        ],
        use_container_width=True,
        height=400

    )
