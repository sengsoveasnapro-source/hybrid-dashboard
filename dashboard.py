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
# ==========================================
# ប្រព័ន្ធគ្រប់គ្រងភ្ញៀវ (CLIENT LICENSE MANAGEMENT)
# ==========================================
st.markdown("---")
st.header("👥 ប្រព័ន្ធគ្រប់គ្រងអតិថិជន (Client Management)")

# ទាញយកទិន្នន័យភ្ញៀវពី Supabase មកបង្ហាញ
try:
    res = supabase.table("mt5_licenses").select("*").execute()
    if res.data:
        import pandas as pd
        licenses_df = pd.DataFrame(res.data)
        st.dataframe(
            licenses_df[['account_number', 'client_name', 'is_active', 'created_at']], 
            use_container_width=True
        )
    else:
        st.info("មិនទាន់មានទិន្នន័យភ្ញៀវនៅឡើយទេ។")
        licenses_df = None
except Exception as e:
    st.error(f"មិនអាចទាញយកទិន្នន័យបានទេ៖ {e}")
    licenses_df = None

# បង្កើតជួរឈរពីរ ដើម្បីបែងចែកផ្ទាំង "បន្ថែមភ្ញៀវ" និង "បិទ/បើកសិទ្ធិ"
col1, col2 = st.columns(2)

# ផ្ទាំងទី ១៖ សម្រាប់បន្ថែមភ្ញៀវថ្មី
with col1:
    st.subheader("➕ បន្ថែមអតិថិជនថ្មី")
    with st.form("add_client_form"):
        new_acc = st.text_input("លេខគណនី MT5 (Account Number)")
        new_name = st.text_input("ឈ្មោះចំណាំ (Client Name)")
        submit_add = st.form_submit_button("✅ អនុម័តសិទ្ធិ (Approve)")
        
        if submit_add and new_acc and new_name:
            try:
                supabase.table("mt5_licenses").insert({
                    "account_number": new_acc, 
                    "client_name": new_name, 
                    "is_active": True
                }).execute()
                st.success(f"បានបន្ថែម {new_name} ({new_acc}) ដោយជោគជ័យ!")
                st.rerun() # Refresh ទំព័រដើម្បីបង្ហាញទិន្នន័យថ្មី
            except Exception as e:
                st.error("លេខគណនីនេះប្រហែលជាមានរួចហើយ ឬមានបញ្ហាប្រព័ន្ធ។")

# ផ្ទាំងទី ២៖ សម្រាប់បិទ ឬបើកសិទ្ធិភ្ញៀវចាស់
with col2:
    st.subheader("⚙️ គ្រប់គ្រងស្ថានភាព (Status)")
    if licenses_df is not None and not licenses_df.empty:
        with st.form("update_client_form"):
            target_acc = st.selectbox("ជ្រើសរើសលេខគណនី", licenses_df['account_number'])
            new_status = st.radio("កំណត់ស្ថានភាពសិទ្ធិ៖", ["Active (អនុញ្ញាត)", "Revoked (បិទសិទ្ធិ)"])
            submit_update = st.form_submit_button("🔄 ធ្វើបច្ចុប្បន្នភាព")
            
            if submit_update:
                is_active_val = True if new_status == "Active (អនុញ្ញាត)" else False
                supabase.table("mt5_licenses").update({"is_active": is_active_val}).eq("account_number", target_acc).execute()
                st.success(f"បានប្តូរស្ថានភាពសម្រាប់គណនី {target_acc} រួចរាល់!")
                st.rerun()

st.markdown("---")
st.caption("DEV CONTACT: 0967205522 | Hybrid Control Center v1.0")  
      