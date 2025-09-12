# app.py
# ----------------------------------------------------
# Streamlit 지도 시각화 (단계별, 함수 없음)
# - OSM TileLayer 항상 켜짐(백그라운드 필수)
# - 경로 단계: Mapbox Directions API로 선택 포인트들을 실제 경로로 이어서 PathLayer로 표시
# - 포인트 샘플: 서울 25개 자치구 중심 좌표(point_sample.json)
# ----------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import json, os, requests

st.set_page_config(page_title="Streamlit 지도 시각화 — Step-by-Step", layout="wide")

# ===== Mapbox Directions (경로 생성에만 사용) =====
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWVnZHNyZmsxMTVpMmtzZzMzMTU5ZGFyIn0.esI42zH2s8c_Dy26yj4uHw"  # 본인 토큰으로 교체
if MAPBOX_TOKEN.endswith("_입력"):
    st.warning("경로 생성을 위해 MAPBOX_TOKEN을 본인 키로 교체하세요. (OSM 배경지도는 토큰 없이 작동)")

# ===== 단계 선택 =====
st.sidebar.markdown("### 강의 단계 (STEP)")
STEP = st.sidebar.selectbox(
    "시연 단계",
    [
        "1) 데이터 로드 & 미리보기",
        "2) 산점 지도",
        "3) 성능 제어(표본·반경·불투명도)",
        "4) 히트맵 전환",
        "5) 경로(PathLayer, Mapbox Directions)"
    ],
    index=0
)

# ===== 데이터 불러오기 =====
upl = st.sidebar.file_uploader("CSV / JSON / GEOJSON", type=["csv","json","geojson"])
use_seoul_sample = st.sidebar.checkbox("서울 25개 자치구 샘플 사용(point_sample.json)", value=(upl is None))

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
elif use_seoul_sample:
    # 같은 폴더에 point_sample.json이 있으면 우선 사용
    try:
        with open("point_sample.json","r",encoding="utf-8") as f:
            df = pd.DataFrame(json.load(f))
    except:
        # 실행 디렉토리에 없으면, 다운로드한 파일을 같은 폴더로 옮겨 두면 자동 인식됩니다.
        st.info("point_sample.json을 프로젝트 폴더에 두면 서울 25개 자치구 샘플을 사용합니다.")
        rng = np.random.default_rng(7)
        df = pd.DataFrame({
            "lat": 37.55 + 0.05*rng.standard_normal(500),
            "lon": 126.98 + 0.06*rng.standard_normal(500),
            "weight": rng.integers(1,5,500),
            "label": "sample"
        })
else:
    # 기존 CSV 샘플 호환(있을 때만)
    try:
        df = pd.read_csv("points_sample.csv")
    except:
        rng = np.random.default_rng(7)
        df = pd.DataFrame({
            "lat": 37.55 + 0.1*rng.random(2000),
            "lon": 126.97 + 0.1*rng.random(2000),
            "weight": rng.integers(1,5,2000),
            "label": "random"
        })

# 열 표준화 + 유효성
df = df.rename(columns={c.lower():"lat" if c.lower() in ["lat","latitude","위도"]
                                   else "lon" if c.lower() in ["lon","lng","longitude","경도"]
                                   else c for c in df.columns})
df = df.dropna(subset=["lat","lon"])
df = df[(df["lat"].between(-90,90)) & (df["lon"].between(-180,180))]

# ===== 경로 샘플(선택 파일 유지 호환) =====
df_paths = None
if os.path.exists("paths_sample.json"):
    try:
        with open("paths_sample.json","r",encoding="utf-8") as f:
            df_paths = pd.DataFrame(json.load(f))
    except Exception as e:
        st.warning(f"paths_sample.json 읽기 오류: {e}")

# ===== 공통 뷰포트 =====
st.title("Streamlit 지도 시각화 — Step-by-Step")
if len(df) == 0:
    st.error("표시할 점 데이터가 없습니다.")
    st.stop()

mid_lat, mid_lon = df["lat"].median(), df["lon"].median()
zoom_guess = 11 if df["lat"].std()<0.2 and df["lon"].std()<0.2 else 9
view = pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=zoom_guess, bearing=0, pitch=0)

# ===== OSM 배경 타일 (항상 켜짐) =====
osm = pdk.Layer(
    "TileLayer",
    data="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    minZoom=0, maxZoom=19, tileSize=256, opacity=1.0
)

# ===== STEP 1: 미리보기 =====
if STEP.startswith("1)"):
    st.subheader("① 데이터 미리보기")
    st.dataframe(df.head(25), use_container_width=True)
    st.stop()

# ===== STEP 2: 산점 =====
if STEP.startswith("2)"):
    st.subheader("② 산점 지도")
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_radius=80 if "gu" in df.columns else 40,
        get_fill_color=[255,140,0,200],
        pickable=True
    )
    st.pydeck_chart(pdk.Deck(layers=[osm, scatter], initial_view_state=view), use_container_width=True)
    st.stop()

# ===== STEP 3: 성능 제어 =====
right = st.sidebar
max_n = min(20000, len(df))
sample_n = right.slider("표본 수", 25, max(200, max_n), min(500, max_n), step=25)
radius = right.slider("반경(px)", 5, 200, 60 if "gu" in df.columns else 40, step=5)
opacity = right.slider("불투명도(%)", 10, 100, 80, step=5) / 100

if "gu" in df.columns:
    cats = ["<전체>"] + df["gu"].astype(str).unique().tolist()
    sel = right.selectbox("자치구", cats, index=0)
else:
    sel = "<전체>"

df_view = df.copy()
if sel != "<전체>" and "gu" in df_view.columns:
    df_view = df_view[df_view["gu"].astype(str) == sel]
df_view = df_view.sample(sample_n, random_state=42) if len(df_view) > sample_n else df_view

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
    st.pydeck_chart(pdk.Deck(layers=[osm, scatter], initial_view_state=view), use_container_width=True)
    st.stop()

# ===== STEP 4: 히트맵 =====
if STEP.startswith("4)"):
    st.subheader("④ 히트맵 전환")
    df_h = df_view.assign(_w = df_view["weight"] if "weight" in df_view.columns else 1)
    heat = pdk.Layer(
        "HeatmapLayer",
        data=df_h,
        get_position='[lon, lat]',
        get_weight="_w",
        radiusPixels=radius
    )
    st.pydeck_chart(pdk.Deck(layers=[osm, heat], initial_view_state=view), use_container_width=True)
    st.stop()

# ===== STEP 5: 경로 (Mapbox Directions) =====
if STEP.startswith("5)"):
    st.subheader("⑤ 경로(PathLayer, Mapbox Directions)")

    # 경로 설정창 — 선택한 포인트 순서대로 Mapbox Directions 호출
    st.markdown("**경로 설정**: 출발지/경유지/도착지를 순서대로 선택하세요. (최대 5개 권장)")
    # ID/이름 후보 만들기
    if "id" not in df.columns:
        df = df.reset_index().rename(columns={"index":"id"})
    label_col = "gu" if "gu" in df.columns else ("name" if "name" in df.columns else None)
    display = df["id"].astype(str) + ((" — " + df[label_col].astype(str)) if label_col else "")

    selected = st.multiselect("포인트 선택(순서 중요)", display.tolist(), max_selections=5)
    width_px = st.slider("선 두께(px)", 2, 12, 6)
    color_hex = st.color_picker("선 색상", "#0066FF")
    opacity_px = st.slider("선 투명도(%)", 30, 100, 90, step=5)

    # HEX → RGBA
    hx = color_hex.lstrip("#")
    rgb = [int(hx[i:i+2], 16) for i in (0,2,4)]
    rgba = [rgb[0], rgb[1], rgb[2], int(255*(opacity_px/100))]

    layers = [osm]

    # 산점(배경)
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=df_view,
            get_position='[lon, lat]',
            get_radius=60,
            get_fill_color=[255,140,0,120],
            pickable=True
        )
    )

    if selected and not MAPBOX_TOKEN.endswith("_입력"):
        # 선택된 id 순서대로 좌표 나열
        sel_ids = [int(s.split(" — ")[0]) for s in selected]
        coords = df.set_index("id").loc[sel_ids, ["lon","lat"]].to_numpy().tolist()

        # Directions 호출: 최대 5개 좌표(출발;경유…;도착)
        coord_str = ";".join([f"{c[0]},{c[1]}" for c in coords])
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coord_str}"
        params = {"geometries":"geojson","overview":"full","access_token":MAPBOX_TOKEN}
        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            if "routes" in data and data["routes"]:
                line = data["routes"][0]["geometry"]["coordinates"]  # [[lon,lat],...]
                route_df = pd.DataFrame([{"path_coords": line}])
                layers.append(
                    pdk.Layer(
                        "PathLayer",
                        data=route_df,
                        get_path="path_coords",
                        get_color=rgba,
                        width_scale=1,
                        width_min_pixels=width_px,
                        width_max_pixels=width_px,
                        pickable=True
                    )
                )
            else:
                st.warning("Mapbox에서 경로를 찾지 못했습니다. 좌표 간 거리가 너무 가깝거나 도로 연결이 없을 수 있어요.")
        except Exception as e:
            st.error(f"Directions 호출 오류: {e}")
    else:
        if MAPBOX_TOKEN.endswith("_입력"):
            st.info("경로를 보려면 상단 MAPBOX_TOKEN을 본인 키로 바꾸세요.")

    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view), use_container_width=True)
