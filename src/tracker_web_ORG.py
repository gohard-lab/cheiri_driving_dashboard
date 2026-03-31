import uuid
import streamlit as st
import requests
from supabase import create_client, Client
from streamlit_javascript import st_javascript
from datetime import datetime, timezone, timedelta

@st.cache_resource
def get_supabase_client():
    url = "https://gkzbiacodysnrzbpvavm.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdremJpYWNvZHlzbnJ6YnB2YXZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM1NzE2MTgsImV4cCI6MjA4OTE0NzYxOH0.Lv5uVeNZOyo21tgyl2jjGcESoLl_iQTJYp4jdCwuYDU"
    return create_client(url, key)

def get_real_client_ip():
    """세션 상태를 이용해 IP 추출 과정에서의 무한 루프를 방지합니다."""
    if "cached_ip" in st.session_state:
        return st.session_state.cached_ip

    try:
        # 🚨 key 인자를 추가하여 위젯 충돌을 방지합니다.
        js_code = "await fetch('https://api.ipify.org?format=json').then(r => r.json()).then(d => d.ip)"
        client_ip = st_javascript(js_code, key="ip_tracker_js")
        
        if client_ip == 0 or not client_ip:
            return None # LOADING 대신 None 반환하여 메인 화면이 뜨게 함
        
        st.session_state.cached_ip = client_ip
        return client_ip
    except:
        return "Unknown"


# 1. 💡 세션 ID를 발급/조회하는 함수 추가 (log_app_usage 함수 위쪽에 배치)
def get_or_create_session_id():
    if 'session_id' not in st.session_state:
        # 접속 시 최초 1회만 고유 ID 생성 (예: 'a1b2c3d4...')
        st.session_state['session_id'] = uuid.uuid4().hex
    return st.session_state['session_id']


def log_app_usage(app_name="unknown_app", action="page_view", details=None):
    real_ip = get_real_client_ip()
    
    # IP가 아직 로딩 중이면 로그 기록을 일단 건너뜁니다 (화면 멈춤 방지)
    if not real_ip:
        return False

    try:
        client = get_supabase_client()
        if not client:
            return False

        loc_data = {}
        if real_ip not in ["Unknown"]:
            try:
                res = requests.get(f"http://ip-api.com/json/{real_ip}?fields=status,country,regionName,city,lat,lon", timeout=1)
                loc_data = res.json() if res.status_code == 200 else {}
            except: pass

        current_session = get_or_create_session_id()

        user_agent = st.context.headers.get("User-Agent", "Unknown") if hasattr(st, "context") else "Unknown"
        kst = timezone(timedelta(hours=9))
        korea_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

        log_data = {
            "session_id": current_session,
            "app_name": app_name,
            "action": action,
            "timestamp": korea_time,
            "country": loc_data.get('country', "Unknown"),
            "region": loc_data.get('regionName', "Unknown"),
            "city": loc_data.get('city', "Unknown"),
            "lat": loc_data.get('lat', 0.0),
            "lon": loc_data.get('lon', 0.0),
            "ip_address": real_ip,
            "details": details if details else {},
            "user_agent": user_agent
        }
        client.table('usage_logs').insert(log_data, returning='minimal').execute()
        return True
    except Exception as e:
        print(f"🚨 트래커 에러: {e}")
        return False