import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import random, datetime, io

# (선택) 인코딩 자동 감지를 위해 chardet 사용
try:
    import chardet
    HAS_CHARDET = True
except Exception:
    HAS_CHARDET = False

st.set_page_config(page_title="Streamlit 데모", layout="centered")

# 사이드바 메뉴 정의 — 파일 업로드와 로또를 분리
menu = st.sidebar.radio(
    "데모 카테고리 선택",
    ("텍스트·마크다운", "데이터프레임·메트릭", "위젯", "차트", "파일 업로드", "로또")
)

# 1) 텍스트·마크다운
if menu == "텍스트·마크다운":
    st.title("이것은 타이틀 입니다 😎")      # 가장 큰 제목
    st.header("헤더를 입력할 수 있어요! ✨")  # 섹션 구분
    st.subheader("이것은 subheader 입니다")   # 소제목
    st.caption("캡션을 한 번 넣어 봤습니다")  # 작은 글씨

    sample_code = '''
def function():
    print("hello, world")
'''
    st.code(sample_code, language="python")
    st.text("일반적인 텍스트")
    st.markdown("**굵게**, :green[강조], 수식 :green[$\\sqrt{x^2+y^2}=1$]")
    st.latex(r"\sqrt{x^2+y^2}=1")

# 2) 데이터프레임·메트릭
elif menu == "데이터프레임·메트릭":
    df = pd.DataFrame({
        "first column": [1, 2, 3, 4],
        "second column": [10, 20, 30, 40],
    })
    st.dataframe(df)   # 대화형 표
    st.table(df)       # 정적 표
    st.metric(label="온도", value="10°C", delta="1.2°C")

# 3) 위젯
elif menu == "위젯":
    if st.button("버튼을 눌러보세요"):
        st.write("버튼이 눌렸습니다!")

    agree = st.checkbox("동의 하십니까?")
    if agree:
        st.write("동의 감사합니다 🙌")

    mbti = st.radio("당신의 MBTI는?", ("ISTJ", "ENFP", "선택지 없음"))
    st.write("선택:", mbti)

# 4) 차트
elif menu == "차트":
    data = pd.DataFrame({
        "이름": ["영식", "철수", "영희"],
        "나이": [22, 31, 25],
        "몸무게": [75.5, 80.2, 55.1],
    })

    # Matplotlib
    fig, ax = plt.subplots()
    ax.bar(data["이름"], data["나이"])
    st.pyplot(fig)

    # Seaborn
    fig2, ax2 = plt.subplots()
    sns.barplot(x="이름", y="나이", data=data, ax=ax2)
    st.pyplot(fig2)

# 5) 파일 업로드 — UTF-8 에러 대비 (인코딩 자동 감지 + 수동 선택)
elif menu == "파일 업로드":
    st.write("CSV 또는 Excel 파일을 업로드하세요.")
    file = st.file_uploader("파일 선택 (csv / xls / xlsx)", type=["csv", "xls", "xlsx"])

    # 인코딩 선택 UI
    enc_options = ["auto (권장)", "utf-8", "utf-8-sig", "cp949(한글)", "euc-kr", "iso-8859-1"]
    enc_choice = st.selectbox("텍스트 인코딩", enc_options, index=0, help="CSV에서 글자가 깨질 때 다른 인코딩으로 바꿔보세요.")

    def autodetect_encoding(raw_bytes: bytes) -> str:
        """chardet로 추정, 실패 시 안전한 기본값 반환"""
        if not HAS_CHARDET:
            return "utf-8"
        result = chardet.detect(raw_bytes)
        enc = (result.get("encoding") or "utf-8").lower()
        # 흔한 한글 인코딩 보정
        if enc in ["euc-kr", "x-euc-kr"]:
            enc = "cp949"
        return enc

    if file is not None:
        filename = file.name.lower()
        try:
            if filename.endswith(".csv"):
                raw = file.read()
                # 파일을 여러 번 읽을 수 있도록 BytesIO로 감싸기
                raw_io = io.BytesIO(raw)

                # 인코딩 결정
                if enc_choice.startswith("auto"):
                    encoding = autodetect_encoding(raw)
                else:
                    # UI 선택값을 pandas에 맞게 매핑
                    mapping = {
                        "utf-8": "utf-8",
                        "utf-8-sig": "utf-8-sig",
                        "cp949(한글)": "cp949",
                        "euc-kr": "euc-kr",
                        "iso-8859-1": "iso-8859-1",
                    }
                    encoding = mapping.get(enc_choice, "utf-8")

                # 1차 시도
                try:
                    df_up = pd.read_csv(io.BytesIO(raw_io.getvalue()), encoding=encoding)
                except UnicodeDecodeError:
                    # 2차 시도: 한글 CSV에서 가장 흔한 cp949로 자동 폴백
                    df_up = pd.read_csv(io.BytesIO(raw_io.getvalue()), encoding="cp949", errors="replace")

            else:
                # Excel은 인코딩 개념이 없이 바이너리 포맷
                df_up = pd.read_excel(file)

            st.success("파일이 성공적으로 로드되었습니다 ✅")
            st.dataframe(df_up, use_container_width=True)
            st.download_button(
                "CSV로 다운로드",
                data=df_up.to_csv(index=False),
                file_name="uploaded.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"파일을 읽는 중 문제가 발생했습니다: {e}")

# 6) 로또
elif menu == "로또":
    st.write("버튼을 눌러 행운의 번호를 생성하세요 🎲")

    def generate_lotto():
        nums = set()
        while len(nums) < 6:
            nums.add(random.randint(1, 45))
        return sorted(nums)

    if st.button("로또 번호 생성"):
        for i in range(1, 6):
            st.write(f"{i}. 행운의 번호: {generate_lotto()}")
        st.write("생성된 시각:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))