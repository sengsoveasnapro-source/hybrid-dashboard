import streamlit as st
import requests
import pandas as pd

# ==========================================
# កន្លែងភ្ជាប់ទៅកាន់ Supabase
# ==========================================
SUPABASE_URL = "https://bqozwahxwhnpnasixxps.supabase.co"
SUPABASE_KEY = "sb_publishable_haSMxbZUbxaV65oU4QaOQQ_HrwTS3Tl" 

st.set_page_config(page_title="Hybrid Control Center", page_icon="⚡", layout="wide")

# រចនាពណ៌ផ្ទៃខាងក្រោយ (Cyberpunk Theme)
st.markdown("""
    <style>
    .stApp { background-color: #060a0f; color: #a0b2c6; }
    h1, h2, h3 { color: #00e5ff; font-weight: 900; }
    div[data-testid="stMetricValue"] { color: #00ffa3; font-size: 35px; font-weight: bold; }
    div[data-testid="stMetricLabel"] { color: #ffaa00; font-size: 15px; font-weight: bold; }
    .dataframe { border: 1px solid #1a2639; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ MASTER CONTROL CENTER")
st.write("---")

def fetch_data():
    endpoint = f"{SUPABASE_URL}/rest/v1/bot_status?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(endpoint, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
    except:
        return []
    return []

data = fetch_data()

if data:
    df = pd.DataFrame(data)
    
    # បូកសរុបទឹកលុយពីគ្រប់ VPS ទាំងអស់
    total_bal = df['balance'].sum()
    total_eq = df['equity'].sum()
    total_prof = df['profit'].sum()
    
    # បង្ហាញតួលេខធំៗខាងលើ
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 NET BALANCE", f"${total_bal:,.2f}")
    col2.metric("🛡️ LIVE EQUITY", f"${total_eq:,.2f}")
    col3.metric("📈 FLOATING P/L", f"${total_prof:,.2f}")
    
    st.write("---")
    st.subheader("💻 CONNECTED SYSTEMS (LIVE STATUS)")
    
    # រៀបចំតារាងឱ្យស្អាត
    df_display = df[['vps_name', 'status', 'balance', 'equity', 'profit', 'total_pos', 'today_lots', 'last_updated']]
    df_display.columns = ['VPS Name', 'Status', 'Balance ($)', 'Equity ($)', 'Profit ($)', 'Open Nodes', 'Today Volume', 'Last Sync']
    
    # Format កាលបរិច្ឆេទឱ្យស្រួលមើល
    df_display['Last Sync'] = pd.to_datetime(df_display['Last Sync']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ No signals detected. Waiting for systems to come online...")

# ប៊ូតុង Refresh
st.write("")
colA, colB, colC = st.columns([1, 2, 1])
with colB:
    if st.button("🔄 REFRESH DATA", use_container_width=True):
        st.rerun()