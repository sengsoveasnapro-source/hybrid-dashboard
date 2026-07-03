import streamlit as st
import requests
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time 

# ==========================================
# ភ្ជាប់ទៅកាន់ Supabase
# ==========================================
SUPABASE_URL = "https://bqozwahxwhnpnasixxps.supabase.co"
SUPABASE_KEY = "sb_publishable_haSMxbZUbxaV65oU4QaOQQ_HrwTS3Tl" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Hybrid Control Center", page_icon="⚡", layout="wide")

# Custom UI Styling
st.markdown("""
    <style>
    .stApp { background-color: #060a0f; color: #E0E6ED; } 
    h1, h2, h3 { color: #00E5FF !important; font-weight: 900; } 
    div[data-testid="stMetricValue"] { color: #00FFA3 !important; font-size: 28px; } 
    .dataframe { border: 1px solid #1a2639; width: 100%; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ MASTER CONTROL CENTER")

# Load Data
@st.cache_data(ttl=5)
def load_all_licenses():
    res = supabase.table("user_licenses").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

licenses_df = load_all_licenses()

def fetch_live_data():
    endpoint = f"{SUPABASE_URL}/rest/v1/bot_status?select=*"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        r = requests.get(endpoint, headers=headers, timeout=5)
        return r.json() if r.status_code == 200 else []
    except: return []

live_df = pd.DataFrame(fetch_live_data())

# Helper Functions
def safe_float(val):
    try:
        if pd.isna(val) or val is None: return 0.0
        return float(val)
    except: return 0.0

def safe_int(val):
    try:
        if pd.isna(val) or val is None: return 0
        return int(float(val))
    except: return 0

tab1, tab2 = st.tabs(["📊 UNIFIED LIVE SYSTEMS", "🔑 LICENSE MANAGEMENT CENTER"])

# ==========================================
# TAB 1: LIVE SYSTEMS
# ==========================================
with tab1:
    st.subheader("💻 ប្រព័ន្ធកំពុងដំណើរការ")
    if not licenses_df.empty:
        active_df = licenses_df[licenses_df['is_active'] == True]
        display_data = []
        for i, row in enumerate(active_df.iterrows(), 1):
            r = row[1]
            acc = str(r.get('account_number', ''))
            match = live_df[live_df['vps_name'].astype(str) == acc] if not live_df.empty else pd.DataFrame()
            status = match.iloc[0]['status'] if not match.empty else "OFFLINE"
            display_data.append({
                "No.": i,
                "ID": acc,
                "Name": r.get('owner_name', 'N/A'),
                "Status": status,
                "Balance": match.iloc[0]['balance'] if not match.empty else 0
            })
        st.table(pd.DataFrame(display_data))
        
        st.write("---")
        with st.expander("⚙️ កែប្រែឈ្មោះអតិថិជន"):
            target = st.selectbox("ជ្រើសរើសគណនី:", active_df['account_number'])
            new_name = st.text_input("ឈ្មោះថ្មី:")
            if st.button("រក្សាទុកឈ្មោះថ្មី"):
                supabase.table("user_licenses").update({"owner_name": new_name}).eq("account_number", target).execute()
                st.rerun()

# ==========================================
# TAB 2: LICENSE MANAGEMENT (Table View)
# ==========================================
with tab2:
    st.subheader("🔑 LICENSE MANAGEMENT CENTER")
    search = st.text_input("🔍 ស្វែងរកអតិថិជន:", placeholder="វាយលេខ Account ឬឈ្មោះ...")
    
    df_show = licenses_df.copy()
    if search:
        df_show = df_show[df_show['account_number'].astype(str).str.contains(search) | 
                          df_show['owner_name'].astype(str).str.contains(search, case=False, na=False)]
    
    # បង្ហាញជាតារាងស្អាត
    table_data = []
    for i, row in df_show.iterrows():
        table_data.append({
            "No.": i+1,
            "ID": row.get('account_number'),
            "Name": row.get('owner_name'),
            "Status": "✅ ACTIVE" if row.get('is_active') else "🟡 PENDING"
        })
    st.table(pd.DataFrame(table_data))
    
    # ប៊ូតុងបញ្ជាសម្រាប់ Approve/Revoke
    st.write("---")
    st.markdown("### ⚡ សកម្មភាពរហ័ស")
    target_acc = st.text_input("បញ្ចូល ID ដើម្បី Approve/Revoke:")
    col1, col2 = st.columns(2)
    if col1.button("✅ Approve"):
        supabase.table("user_licenses").update({"is_active": True}).eq("account_number", target_acc).execute()
        st.rerun()
    if col2.button("🚫 Revoke"):
        supabase.table("user_licenses").update({"is_active": False}).eq("account_number", target_acc).execute()
        st.rerun()

if st.button("🔄 REFRESH DATA"):
    st.rerun()