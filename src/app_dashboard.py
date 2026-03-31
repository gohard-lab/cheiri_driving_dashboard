import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import time
import os
from datetime import date, timedelta
from tracker_web import log_app_usage
from dotenv import load_dotenv
from supabase import create_client

# current_dir = os.path.dirname(os.path.abspath(__file__))
# # env_path = os.path.join(current_dir, "..", ".env")
# # load_dotenv(dotenv_path=env_path, override=True)

# # 현재 폴더에서 .env 파일을 찾도록 수정
# env_path = os.path.join(current_dir, ".env")
# load_dotenv(dotenv_path=env_path, override=True)


# 1. 세션 상태(session_state) 초기화
if "distance" not in st.session_state:
    st.session_state.distance = 0.0
if "fuel_used" not in st.session_state:
    st.session_state.fuel_used = 0.0
if "charge_amount" not in st.session_state:
    st.session_state.charge_amount = 0.0

@st.cache_resource
def get_viewer_supabase():
    # url = os.getenv("SUPABASE_URL")
    # key = os.getenv("SUPABASE_KEY")
    
    # if not url or not key:
    #     st.error("💡 본인의 Supabase 주소와 키를 .env 파일에 세팅해 주세요!")
    #     st.stop()
    # ---------------------------------------------------------
    # 🔑 스마트 키 불러오기 (Cloud Secrets 우선, 없으면 로컬 .env)
    # ---------------------------------------------------------
    if "supabase" in st.secrets:
        # 1. Streamlit Cloud 배포 환경일 경우 (Secrets 탭에서 가져옴)
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    else:
        # 2. 로컬 PC 테스트 환경일 경우 (.env 파일에서 가져옴)
        load_dotenv()
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    # 키가 둘 다 없을 때만 에러 발생
    if not url or not key:
        st.error("🚨 본인의 Supabase 주소와 키를 세팅해 주세요!")
        st.stop()
                
    return create_client(url, key)

# 콤보박스 값 변경 시 실행될 콜백 함수
def on_expense_category_change():
    selected_category = st.session_state.expense_category
    
    usage_details = json.dumps({"selected_category": selected_category}, ensure_ascii=False)
    log_app_usage("driving_dashboard_web", "category_combobox_changed", details=usage_details)
    
    if selected_category == "기타":
        st.session_state.distance = 0.0
        st.session_state.fuel_used = 0.0
        st.session_state.charge_amount = 0.0


@st.dialog("⭐ Support Polymath Developer Automation Tool")
def show_star_popup_web():
    # 팝업 노출 트래커 기록
    log_app_usage("driving_dashboard_web", "star_prompt_displayed", details={"ui": "streamlit_dialog"})
    
    st.warning(
        "💡 유용하게 사용하셨나요? 소스코드만 날름 가져가는 분들이 많습니다. "
        "개발자의 땀과 노력에 대한 최소한의 예의로 깃허브 Star⭐를 부탁드립니다!\n\n"
        "Did you find this useful? Please show some basic courtesy for the developer's hard work by leaving a GitHub Star⭐."
    )
    
    # 깃허브 Star 유도 버튼
    st.link_button("👉 깃허브로 이동하여 Star 누르기", "https://github.com/gohard-lab/driving_dashboard")

def main():
    st.set_page_config(page_title="Cheiri's 드라이빙 대시보드", page_icon="🏎️", layout="wide")
    
    if "is_opened" not in st.session_state:
        # show_star_popup_web()
        if log_app_usage("driving_dashboard_web", "app_opened"):
            st.session_state.is_opened = True

    st.title("🏎️ Cheiri's 차 주행 데이터 분석 대시보드")

    # DB와 연결
    supabase = get_viewer_supabase()

    # (안전장치) DB 연결에 실패하면 화면을 멈춤
    if not supabase:
        st.stop()

    # --- 1.5. DB에서 등록된 차량 목록 동적으로 불러오기 ---
    try:
        car_response = supabase.table("driving_records").select("car_model").execute()
        db_cars = list(set([row['car_model'] for row in car_response.data if row['car_model']]))
    except Exception:
        db_cars = []

    default_cars = ["2019 BMW M2 Competition", "2020 Renault Clio"]
    car_options = []
    for car in default_cars + db_cars:
        if car not in car_options and car != "기타 차량":
            car_options.append(car)
    
    car_options.append("기타 차량")

    # --- 2. 사이드바: 입력 인터페이스 ---
    with st.sidebar:
        st.header("📝 새 주행 기록 입력")
        car_model = st.selectbox("차량 선택", car_options)
        
        if car_model == "기타 차량":
            custom_car = st.text_input("차종 직접 입력", placeholder="예: 2024 아이오닉 5")
            final_car_model = custom_car if custom_car else "기타 차량"
        else:
            final_car_model = car_model

        drive_date = st.date_input("주행 날짜", date.today())
        power_type = st.radio("동력원", ["내연기관", "전기차"], horizontal=True)
        category = st.selectbox("지출 분류", 
                                ["주유/충전", "정비/수리", "세차", "튜닝/용품", "기타"], 
                                key="expense_category", 
                                on_change=on_expense_category_change
                                )
        distance = st.number_input("누적/주행 거리 (km)", min_value=0.0, step=10.0, key="distance")

        if power_type == "내연기관":
            fuel_used = st.number_input("주유량 (L)", min_value=0.0, step=5.0, key="fuel_used")
            charge_amount = 0.0
        else:
            fuel_used = 0.0
            charge_amount = st.number_input("충전량 (kWh)", min_value=0.0, step=5.0, key="charge_amount")
            
        cost = st.number_input("금액 (원)", min_value=0, step=1000)
        
        if cost > 0:
            st.caption(f"💸 입력 금액: **{cost:,.0f} 원** ( {total_cost_to_hangul(cost)} )")
        
        memo = st.text_area("메모 (선택사항)", placeholder="상세 내역을 자유롭게 적어주세요.")
        btn_click = st.button("기록 추가하기", type="primary")

    # --- 3. 데이터 저장 로직 ---
    if btn_click:
        if distance >= 0:
            record_data = {
                "car_model": final_car_model,
                "drive_date": drive_date.isoformat(),
                "power_type": power_type,
                "category": category,
                "distance": distance,
                "fuel_used": fuel_used,
                "charge_amount": charge_amount,
                "cost": cost,
                "memo": memo
            }
            try:
                supabase.table("driving_records").insert(record_data, returning="minimal").execute()
                log_app_usage("driving_dashboard_web", "record_added", {"car_model": final_car_model, "category": category, "action": "insert"})
                st.success(f"[{final_car_model}] {category} 기록이 저장되었습니다!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"저장 중 에러가 발생했습니다: {e}")
        else:
            st.warning("거리를 정확히 입력해 주세요.")

    # --- 4. 데이터 시각화 및 기간 필터링 ---
    st.divider()
    
    st.markdown("### 🔍 데이터 조회 조건")
    today = date.today()
    try:
        # default_start = today.replace(year=today.year - 1)
        # 기본 시작일을 오늘로부터 90일(약 3개월) 전으로 설정합니다. (180일로 하시면 6개월이 됩니다)
        default_start = today - timedelta(days=90)

    except ValueError:
        default_start = today.replace(year=today.year - 1, day=28)
        
    if "search_start" not in st.session_state:
        st.session_state.search_start = default_start
    if "search_end" not in st.session_state:
        st.session_state.search_end = today

    with st.form("search_form"):
        col_f1, col_f2 = st.columns([3, 1])
        selected_dates = col_f1.date_input("🗓️ 조회 기간 설정", [st.session_state.search_start, st.session_state.search_end], max_value=today)
        search_btn = col_f2.form_submit_button("🔍 조회하기")

    if search_btn:
        if len(selected_dates) == 2:
            st.session_state.search_start = selected_dates[0]
            st.session_state.search_end = selected_dates[1]
        else:
            st.session_state.search_start = selected_dates[0]
            st.session_state.search_end = selected_dates[0]
        
        log_app_usage("driving_dashboard_web", "date_searched", {"start": st.session_state.search_start.isoformat(), "end": st.session_state.search_end.isoformat()})

    start_date_str = f"{st.session_state.search_start.isoformat()}T00:00:00"
    end_date_str = f"{st.session_state.search_end.isoformat()}T23:59:59"

    try:
        response = supabase.table("driving_records") \
            .select("*") \
            .gte("drive_date", start_date_str) \
            .lte("drive_date", end_date_str) \
            .execute()
        raw_data = response.data
    except Exception as e:
        raw_data = []
        st.error("데이터를 불러오지 못했습니다.")

    if raw_data:
        df = pd.DataFrame(raw_data)
        df['drive_date'] = pd.to_datetime(df['drive_date'])
        df['year_month'] = df['drive_date'].dt.strftime('%Y년 %m월')
        
        if 'power_type' not in df.columns: df['power_type'] = '내연기관'
        if 'charge_amount' not in df.columns: df['charge_amount'] = 0.0
        
        df['power_type'] = df['power_type'].fillna('내연기관')
        df['charge_amount'] = df['charge_amount'].fillna(0.0)
        
        df = df.sort_values('drive_date')
        
        def calculate_efficiency(row):
            if row['power_type'] == '내연기관' and pd.notnull(row.get('fuel_used')) and row.get('fuel_used') > 0:
                return row['distance'] / row['fuel_used']
            elif row['power_type'] == '전기차' and pd.notnull(row.get('charge_amount')) and row.get('charge_amount') > 0:
                return row['distance'] / row['charge_amount']
            return None

        df['efficiency'] = df.apply(calculate_efficiency, axis=1)

        my_car_df = df[df['car_model'] == final_car_model].copy()

        if not my_car_df.empty:
            st.subheader(f"📊 {final_car_model} 주행 통계 ({st.session_state.search_start.strftime('%Y.%m.%d')} ~ {st.session_state.search_end.strftime('%Y.%m.%d')})")
            
            current_power_type = my_car_df['power_type'].iloc[-1]
            eff_label = "연비" if current_power_type == "내연기관" else "전비"
            eff_unit = "km/L" if current_power_type == "내연기관" else "km/kWh"
            
            total_dist = my_car_df['distance'].max()
            total_cost = my_car_df['cost'].sum()
            
            if current_power_type == "내연기관":
                valid_records = my_car_df[my_car_df['fuel_used'] > 0]
                avg_eff = valid_records['distance'].sum() / valid_records['fuel_used'].sum() if not valid_records.empty else 0.0
            else:
                valid_records = my_car_df[my_car_df['charge_amount'] > 0]
                avg_eff = valid_records['distance'].sum() / valid_records['charge_amount'].sum() if not valid_records.empty else 0.0
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("기록상 최고 누적거리", f"{total_dist:,.1f} km")
            col2.metric(f"평균 {eff_label}", f"{avg_eff:.2f} {eff_unit}")
            col3.metric("기록 횟수", f"{len(my_car_df)} 회")
            col4.metric("총 유지비", f"{total_cost:,.0f} 원")

            # 🛠️ [수정됨] 그래프 1: 연비/전비 트렌드 (x축 일자 표시 추가)
            eff_df = my_car_df.dropna(subset=['efficiency'])
            maint_df = my_car_df[my_car_df['category'].isin(['정비/수리', '튜닝/용품'])].copy()
            
            fig_eff = go.Figure()
            
            fig_eff.add_trace(go.Scatter(
                x=eff_df["drive_date"], y=eff_df["efficiency"], 
                mode='lines+markers', name=f'{eff_label} ({eff_unit})',
                line=dict(color='#1f77b4', width=2),
                hovertemplate=f'<b>날짜: %{{x|%Y년 %m월 %d일}}</b><br>{eff_label}: %{{y:.2f}} {eff_unit}<extra></extra>'
            ))

            if not maint_df.empty:
                fig_eff.add_trace(go.Scatter(
                    x=maint_df["drive_date"], 
                    y=[eff_df['efficiency'].min() * 0.9 if not eff_df.empty else 0] * len(maint_df),
                    mode='markers', name='차량 점검/이슈',
                    marker=dict(color='#d62728', size=10, symbol='diamond'),
                    hovertemplate='<b>날짜: %{x|%Y년 %m월 %d일}</b><br>분류: %{customdata[0]}<br>메모: %{text}<extra></extra>',
                    customdata=maint_df[['category']],
                    text=maint_df['memo']
                ))

            fig_eff.update_layout(
                title=f"📈 {eff_label} 트렌드 및 차량 이슈 (화면 고정)", 
                xaxis_title="날짜", 
                yaxis_title=f"{eff_label} ({eff_unit})", 
                hovermode='closest',
                dragmode=False,
                xaxis=dict(tickformat="%Y년 %m월 %d일", fixedrange=True), 
                yaxis=dict(fixedrange=True)
            )
            st.plotly_chart(fig_eff, use_container_width=True, config={'displayModeBar': False})

            # 🛠️ 그래프 2: 월별 유지비 차트 (월별 통계이므로 기존 유지)
            st.markdown("### 💸 월별 유지비 지출 현황 (화면 고정)")
            expense_df = my_car_df[my_car_df['cost'] > 0].copy()
            
            if not expense_df.empty:
                def join_memos(x):
                    memos = [str(i).strip() for i in x if pd.notnull(i) and str(i).strip() != '']
                    if not memos: return "메모 없음"
                    res = ", ".join(memos)
                    return res[:15] + "..." if len(res) > 15 else res

                monthly_exp = expense_df.groupby(['year_month', 'category']).agg({
                    'cost': 'sum', 
                    'memo': join_memos
                }).reset_index()
                
                monthly_exp.columns = ['날짜(월)', '분류', '금액(원)', '메모']

                fig_cost = px.bar(
                    monthly_exp, x='날짜(월)', y='금액(원)', color='분류',
                    labels={'금액(원)': '지출 금액', '날짜(월)': ''},
                    color_discrete_map={'주유/충전': '#2ca02c', '정비/수리': '#d62728', '세차': '#17becf', '튜닝/용품': '#9467bd', '기타': '#7f7f7f'},
                    hover_data=['메모']
                )
                
                fig_cost.update_layout(
                    yaxis=dict(tickformat=",", ticksuffix="원", fixedrange=True),
                    xaxis=dict(fixedrange=True),
                    dragmode=False
                )
                st.plotly_chart(fig_cost, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("해당 기간에 금액 기록이 없어 유지비 차트를 그릴 수 없습니다.")

            # 하단 표 출력
            st.markdown(f"### 📝 주행 및 유지비 기록 (클릭하여 관리)")
            st.caption("👇 표에서 수정/삭제하고 싶은 행의 왼쪽 체크박스를 클릭하세요.")
            
            display_df = my_car_df[['drive_date', 'power_type', 'category', 'distance', 'fuel_used', 'charge_amount', 'efficiency', 'cost', 'memo']].copy()
            display_df.columns = ['날짜', '동력원', '분류', '주행거리(km)', '주유량(L)', '충전량(kWh)', f'효율', '금액(원)', '메모']
            display_df['날짜'] = display_df['날짜'].dt.strftime('%Y년 %m월 %d일')
            
            selection_event = st.dataframe(
                display_df.style.format({'주행거리(km)': '{:.1f}', '주유량(L)': '{:.1f}', '충전량(kWh)': '{:.1f}', '효율': '{:.2f}', '금액(원)': '{:,.0f}'}), 
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun"
            )
            
            # --- 5. 기록 수정 및 삭제 ---
            st.divider()
            st.markdown("### 🛠️ 선택된 기록 관리")
            
            selected_rows = selection_event.selection.rows
            
            if len(selected_rows) > 0:
                selected_idx = selected_rows[0]
                selected_row = my_car_df.iloc[selected_idx]
                rec_id = int(selected_row['id'])
                
                with st.form(key="edit_delete_form"):
                    st.success("선택한 기록의 내용을 수정하거나 삭제할 수 있습니다.")
                    
                    e_col1, e_col2, e_col3 = st.columns(3)
                    edit_date = e_col1.date_input("주행 날짜 수정", selected_row['drive_date'])
                    
                    p_types = ["내연기관", "전기차"]
                    cur_ptype = selected_row['power_type'] if pd.notnull(selected_row.get('power_type')) else "내연기관"
                    edit_ptype = e_col2.selectbox("동력원 수정", p_types, index=p_types.index(cur_ptype))
                    
                    categories = ["주유/충전", "정비/수리", "세차", "튜닝/용품", "기타"]
                    cur_cat = selected_row['category'] if selected_row['category'] in categories else "기타"
                    edit_category = e_col3.selectbox("지출 분류 수정", categories, index=categories.index(cur_cat))
                    
                    e_col4, e_col5, e_col6, e_col7 = st.columns(4)
                    edit_dist = e_col4.number_input("거리 (km) 수정", value=float(selected_row['distance']), step=10.0)
                    edit_fuel = e_col5.number_input("주유량 (L) 수정", value=float(selected_row['fuel_used'] if pd.notnull(selected_row.get('fuel_used')) else 0.0), step=5.0)
                    edit_charge = e_col6.number_input("충전량 (kWh) 수정", value=float(selected_row['charge_amount'] if pd.notnull(selected_row.get('charge_amount')) else 0.0), step=5.0)
                    edit_cost = e_col7.number_input("금액 (원) 수정", value=int(selected_row['cost']), step=1000)
                    
                    if edit_cost > 0:
                        e_col7.caption(f"💸 **{edit_cost:,.0f} 원** ( {total_cost_to_hangul(edit_cost)} )")
                    
                    edit_memo = st.text_area("메모 수정", value=str(selected_row['memo']) if pd.notnull(selected_row['memo']) else "")
                    
                    st.markdown("---")
                    btn_col1, btn_col2 = st.columns([1, 1])
                    btn_update = btn_col1.form_submit_button("💾 이 기록 수정하기", type="primary")
                    confirm_delete = btn_col2.checkbox("🚨 영구 삭제 동의")
                    btn_delete = btn_col2.form_submit_button("🗑️ 선택한 기록 삭제")
                    
                    if btn_update:
                        update_data = {
                            "drive_date": edit_date.isoformat(),
                            "power_type": edit_ptype,
                            "category": edit_category,
                            "distance": edit_dist,
                            "fuel_used": edit_fuel,
                            "charge_amount": edit_charge,
                            "cost": edit_cost,
                            "memo": edit_memo
                        }
                        try:
                            supabase.table("driving_records").update(update_data).eq("id", rec_id).execute()
                            log_app_usage("driving_dashboard_web", "record_edited", {"car_model": final_car_model, "action": "update", "record_id": rec_id})
                            st.success("기록이 성공적으로 수정되었습니다!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"수정 에러: {e}")
                            
                    if btn_delete:
                        if confirm_delete:
                            try:
                                supabase.table("driving_records").delete().eq("id", rec_id).execute()
                                log_app_usage("driving_dashboard_web", "record_deleted", {"car_model": final_car_model, "action": "delete", "record_id": rec_id})
                                st.warning("선택한 기록이 영구적으로 삭제되었습니다.")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"삭제 에러: {e}")
                        else:
                            st.error("삭제를 원하시면 '영구 삭제 동의' 체크박스를 먼저 선택해 주세요.")
            else:
                st.info("👆 위 주행 기록 표에서 수정/삭제하고 싶은 행을 클릭해 주세요.")
        else:
            st.info(f"선택하신 기간 내에 [{final_car_model}]의 주행 기록이 없습니다.")
    else:
        st.info("데이터베이스에 등록된 기록이 없습니다.")

def total_cost_to_hangul(cost):
    if cost == 0: return "0원"
    result = ""
    억 = cost // 100000000
    if 억 > 0:
        result += f"{억}억 "
        cost %= 100000000
    만 = cost // 10000
    if 만 > 0:
        result += f"{만}만 "
    if result == "": return f"{cost}원"
    else: return result + "원"

if __name__ == "__main__":
    main()