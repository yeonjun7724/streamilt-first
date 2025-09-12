# app.py
# ----------------------------------------------------
# Streamlit 지도 시각화 튜토리얼 (단계별, 함수 없음)
# - Mapbox 배경지도 강제 사용
# - PathLayer 가시성 강화, 부재 시 즉시 경고
# ----------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import json
import os

st.set_page_config(page_title="Streamlit 지도 시각화 튜토리얼", layout="wide")

# ★★★ 반드시 본인 토큰으로 교체 ★★★
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWVnZHNyZmsxMTVpMmtzZzMzMTU5ZGFyIn0.esI42zH2s8c_Dy26yj4uHw"
MAP_STYLE = "mapbox://styles/mapbox/light-v11"

# Mapbox 강제 적용 (배경지도 필수)
pdk.settings.mapbox_api_key = MAPBOX_TOKEN

# 토큰 미교체 시 바로 알림
if MAPBOX_TOKEN.endswith("_입력"):
    st.error("Mapbox API 키를 MAPBOX_TOKEN에 입력하세요. (배경지도 필수 요구 사항)")
    st.stop()

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
_ = st.sidebar.checkbox("샘플 데이터 사용(업로드가 없을 때 자동)", value=(upl is None))

if upl is not None:
    name = upl.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(upl)
    else:
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
        layers=[scatter],
        initial_view_state=view,
        map_provider="mapbox",      # ★ Mapbox 강제
        map_style=MAP_STYLE,
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
        layers=[scatter],
        initial_view_state=view,
        map_provider="mapbox",
        map_style=MAP_STYLE,
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
        layers=[heat],
        initial_view_state=view,
        map_provider="mapbox",
        map_style=MAP_STYLE
    )
    st.pydeck_chart(deck, use_container_width=True)
    st.stop()

# ---------------- STEP 5: 경로 ----------------
if STEP.startswith("5)"):
    st.subheader("⑤ 경로(PathLayer) 추가")
    base = pdk.Layer(
        "ScatterplotLayer",
        data=df_view,
        get_position='[lon, lat]',
        get_radius=radius,
        get_fill_color=[255,140,0,120],
        pickable=True
    )
    layers = [base]

    if df_paths is None:
        st.warning("paths_sample.json 파일이 폴더에 없습니다. 샘플 경로를 보려면 파일을 넣어주세요.")
    elif "path_coords" not in df_paths.columns:
        st.warning("paths_sample.json에 'path_coords' 열이 없습니다. [[lon,lat], ...] 리스트를 가진 'path_coords'가 필요합니다.")
    else:
        # 가시성 강화: 픽셀 단위 최소/최대 폭 지정
        path = pdk.Layer(
            "PathLayer",
            data=df_paths.dropna(subset=["path_coords"]),
            get_path="path_coords",
            get_color=[0,102,255,220],
            width_scale=1,
            width_min_pixels=3,
            width_max_pixels=8,
            pickable=True
        )
        layers.append(path)

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view,
        map_provider="mapbox",
        map_style=MAP_STYLE
    )
    st.pydeck_chart(deck, use_container_width=True)
