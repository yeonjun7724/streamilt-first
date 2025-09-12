# app.py
# ----------------------------------------------------
# Streamlit 지도 시각화 (단계별, 함수 없음)
# - OSM 타일을 TileLayer로 항상 깔기(백그라운드 필수 조건 충족)
# - PathLayer에 "경로 설정" UI(선택/두께/투명도/색상) 실제 동작
# ----------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import json, os

st.set_page_config(page_title="Streamlit 지도 시각화 — Step-by-Step", layout="wide")

# ---------------- 단계 선택 ----------------
st.sidebar.markdown("### 강의 단계 (STEP)")
STEP = st.sidebar.selectbox(
    "시연 단계",
    [
        "1) 데이터 로드 & 미리보기",
        "2) 산점 지도",
        "3) 성능 제어(표본·반경·불투명도)",
        "4) 히트맵 전환",
        "5) 경로(PathLayer) 추가"
    ], index=0
)

# ---------------- 데이터 불러오기 ----------------
upl = st.sidebar.file_uploader("CSV / JSON / GEOJSON", type=["csv","json","geojson"])
_ = st.sidebar.checkbox("샘플 데이터 사용(업로드 없을 때 자동)", value=(upl is None))

if upl is not None:
    name = upl.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(upl)
    else:
        # JSON/GeoJSON 처리 (NDJSON 포함)
        try:
            df = pd.read_json(upl, lines=False)
        except ValueError:
            upl.seek(0)
            df = pd.read_json(upl, lines=True)
        except Exception:
            upl.seek(0)
            data = json.load(upl)
            if isinstance(data, dict) and "features" in data:
                rows = []
                for feat in data["features"]:
                    geom = feat.get("geometry", {})
                    props = feat.get("properties", {}) or {}
                    if geom.get("type") == "Point":
                        lon, lat = geom.get("coordinates", [None, None])
                        rows.append({"lat": lat, "lon": lon, **props})
                df = pd.DataFrame(rows)
            else:
                df = pd.DataFrame(data)
else:
    try:
        df = pd.read_csv("points_sample.csv")
    except:
        rng = np.random.default_rng(7)
        df = pd.DataFrame({
            "lat": 37.55 + 0.1*rng.random(3000),
            "lon": 126.97 + 0.1*rng.random(3000),
            "weight": rng.integers(1,5,3000),
            "category": rng.choice(["cafe","restaurant","hotel","park"],3000)
        })

# 열 표준화 & 유효성
df = df.rename(columns={c.lower():"lat" if c.lower() in ["lat","latitude","위도"]
                                   else "lon" if c.lower() in ["lon","lng","longitude","경도"]
                                   else c for c in df.columns})
df = df.dropna(subset=["lat","lon"])
df = df[(df["lat"].between(-90,90)) & (df["lon"].between(-180,180))]

# 경로 데이터(선택)
df_paths = None
if os.path.exists("paths_sample.json"):
    try:
        with open("paths_sample.json","r",encoding="utf-8") as f:
            df_paths = pd.DataFrame(json.load(f))
    except Exception as e:
        st.warning(f"paths_sample.json 읽기 오류: {e}")

# ---------------- STEP 1: 미리보기 ----------------
st.title("Streamlit 지도 시각화 — Step-by-Step")
if STEP.startswith("1)"):
    st.subheader("① 데이터 미리보기")
    st.dataframe(df.head(10), use_container_width=True)
    st.stop()

# ---------------- 공통 뷰포트 ----------------
if len(df) == 0:
    st.error("표시할 점 데이터가 없습니다. 파일을 확인하세요.")
    st.stop()

mid_lat, mid_lon = df["lat"].median(), df["lon"].median()
zoom_guess = 11 if df["lat"].std()<0.2 and df["lon"].std()<0.2 else 6
view = pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=zoom_guess, bearing=0, pitch=0)

# ---------------- OSM 배경 타일 (항상 켜짐) ----------------
# OpenStreetMap 타일을 TileLayer로 추가(키/토큰 불필요)
osm = pdk.Layer(
    "TileLayer",
    data="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    minZoom=0,
    maxZoom=19,
    tileSize=256,
    opacity=1.0
)

# ---------------- STEP 2: 산점 ----------------
if STEP.startswith("2)"):
    st.subheader("② 산점 지도")
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_radius=40,
        get_fill_color=[255,140,0,180],
        pickable=True
    )
    deck = pdk.Deck(
        layers=[osm, scatter],          # ← 항상 OSM을 첫 레이어로
        initial_view_state=view,
        map_provider=None,              # ← 외부 베이스맵 안 씀
        map_style=None,
        tooltip={"text":"lat: {lat}\nlon: {lon}"}
    )
    st.pydeck_chart(deck, use_container_width=True)
    st.stop()

# ---------------- STEP 3: 성능 제어 ----------------
right = st.sidebar
max_n = min(50000, len(df))
sample_n = right.slider("표본 수",500,max(1000,max_n),min(3000,max_n),step=500)
radius = right.slider("반경(px)",5,200,40,step=5)
opacity = right.slider("불투명도(%)",10,100,70,step=5)/100

if "category" in df.columns:
    cats = ["<전체>"]+sorted(pd.Series(df["category"].dropna()).astype(str).unique())
    sel = right.selectbox("카테고리", cats, index=0)
else:
    sel = "<전체>"

df_view = df.copy()
if sel!="<전체>" and "category" in df_view.columns:
    df_view = df_view[df_view["category"].astype(str)==sel]
df_view = df_view.sample(sample_n,random_state=42) if len(df_view)>sample_n else df_view

if STEP.startswith("3)"):
    st.subheader("③ 성능 제어")
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df_view,
        get_position='[lon, lat]',
        get_radius=radius,
        get_fill_color=[255,140,0,int(255*opacity)],
        pickable=True
    )
    deck = pdk.Deck(
        layers=[osm, scatter],
        initial_view_state=view,
        map_provider=None,
        map_style=None,
        tooltip={"text":"lat: {lat}\nlon: {lon}"}
    )
    st.pydeck_chart(deck, use_container_width=True)
    st.stop()

# ---------------- STEP 4: 히트맵 ----------------
if STEP.startswith("4)"):
    st.subheader("④ 히트맵 전환")
    df_h = df_view.assign(_w=df_view["weight"] if "weight" in df_view.columns else 1)
    heat = pdk.Layer(
        "HeatmapLayer",
        data=df_h,
        get_position='[lon, lat]',
        get_weight="_w",
        radiusPixels=radius
    )
    deck = pdk.Deck(
        layers=[osm, heat],
        initial_view_state=view,
        map_provider=None,
        map_style=None
    )
    st.pydeck_chart(deck, use_container_width=True)
    st.stop()

# ---------------- STEP 5: 경로 ----------------
if STEP.startswith("5)"):
    st.subheader("⑤ 경로(PathLayer) 추가")

    # ===== 경로 설정창(실제 동작) =====
    if df_paths is None:
        st.warning("paths_sample.json 파일이 폴더에 없습니다. 샘플 경로를 보려면 파일을 넣어주세요.")
        selectable_ids = []
    elif "path_coords" not in df_paths.columns:
        st.warning("paths_sample.json에 'path_coords' 열이 없습니다. [[lon,lat], ...] 리스트가 필요합니다.")
        selectable_ids = []
    else:
        # id 열이 없으면 임시 id 부여
        if "id" not in df_paths.columns:
            df_paths["id"] = [f"route-{i+1}" for i in range(len(df_paths))]
        selectable_ids = ["<전체>"] + df_paths["id"].astype(str).tolist()

    col1, col2, col3 = st.columns([1.5,1,1])
    with col1:
        chosen = st.selectbox("경로 선택", selectable_ids, index=0 if selectable_ids else None)
    with col2:
        width_px = st.slider("선 두께(px)", 1, 12, 5)
    with col3:
        color_hex = st.color_picker("선 색상", "#0066FF")
    # hex → rgba
    color_hex = color_hex.lstrip("#")
    color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0,2,4))
    opacity_px = st.slider("선 투명도(%)", 20, 100, 90, step=5)
    rgba = [color_rgb[0], color_rgb[1], color_rgb[2], int(255 * (opacity_px/100))]

    # 베이스(산점) + 선택 경로 레이어
    base = pdk.Layer(
        "ScatterplotLayer",
        data=df_view,
        get_position='[lon, lat]',
        get_radius=radius,
        get_fill_color=[255,140,0,120],
        pickable=True
    )

    layers = [osm, base]

    # 선택된 경로만 필터링
    if selectable_ids:
        df_paths_view = df_paths.dropna(subset=["path_coords"]).copy()
        if chosen and chosen != "<전체>":
            df_paths_view = df_paths_view[df_paths_view["id"].astype(str) == chosen]

        path = pdk.Layer(
            "PathLayer",
            data=df_paths_view,
            get_path="path_coords",
            get_color=rgba,
            width_scale=1,
            width_min_pixels=width_px,
            width_max_pixels=width_px,
            pickable=True
        )
        layers.append(path)

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view,
        map_provider=None,
        map_style=None
    )
    st.pydeck_chart(deck, use_container_width=True)
