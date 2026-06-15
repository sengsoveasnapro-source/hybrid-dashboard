import streamlit as st
import requests
import pandas as pd
from supabase import create_client, Client

# ==========================================
# ភ្ជាប់ទៅកាន់ Supabase
# ==========================================
SUPABASE_URL = "https://bqozwahxwhnpnasixxps.supabase.co"
SUPABASE_KEY = "sb_publishable_haSMxbZUbxaV65oU4QaOQQ_HrwTS3Tl" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Hybrid Control Center", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #060a0f; color: #E0E6ED; } 
    h1, h2, h3 { color: #00E5FF !important; font-weight: 900; text-shadow: 0px 0px 10px rgba(0, 229, 255, 0.4); } 
    div[data-testid="stMetricValue"] { color: #00FFA3 !important; font-size: 35px; font-weight: bold; text-shadow: 0px 0px 10px rgba(0, 255, 163, 0.4); } 
    div[data-testid="stMetricLabel"] { color: #FFAA00 !important; font-size: 15px; font-weight: bold; } 
    p, span, label, div { color: #E0E6ED; }
    .dataframe { border: 1px solid #1a2639; }
    .stAlert { background-color: #0A111E !important; border: 1px solid #00E5FF !important; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ MASTER CONTROL CENTER")
st.write("---")

try:
    res = supabase.table("mt5_licenses").select("*").execute()
    licenses_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
except:
    licenses_df = pd.DataFrame()

def fetch_live_data():
    endpoint = f"{SUPABASE_URL}/rest/v1/bot_status?select=*"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        r = requests.get(endpoint, headers=headers, timeout=5)
        if r.status_code == 200: return r.json()
    except: return []
    return []

live_df = pd.DataFrame(fetch_live_data())

# ==========================================
# ផ្នែកទី ១៖ សំណើសុំសិទ្ធិថ្មី 
# ==========================================
st.subheader("🔔 សំណើសុំសិទ្ធិថ្មី (Pending Approvals)")

if not licenses_df.empty and 'is_active' in licenses_df.columns:
    pending_df = licenses_df[licenses_df['is_active'] == False]
    
    if not pending_df.empty:
        for index, row in pending_df.iterrows():
            acc = row.get('account_number', 'Unknown')
            col1, col2 = st.columns([4, 1])
            col1.warning(f"⚠️ មានសំណើថ្មីពីគណនីលេខ៖ **{acc}**")
            if col2.button(f"✅ អនុម័ត (Approve)", key=f"approve_{acc}"):
                supabase.table("mt5_licenses").update({"is_active": True}).eq("account_number", acc).execute()
                st.rerun()
    else:
        st.success("✅ មិនមានសំណើថ្មីទេបច្ចុប្បន្ន។")
else:
    st.success("✅ មិនមានសំណើថ្មីទេបច្ចុប្បន្ន។")

st.write("---")

# ==========================================
# ផ្នែកទី ២៖ តារាងរួមបញ្ចូលគ្នា
# ==========================================
st.subheader("💻 ប្រព័ន្ធកំពុងដំណើរការ (UNIFIED LIVE SYSTEMS)")

def format_status(status_text):
    """
    Format status text to include icons and green/red text.
    """
    if "ONLINE" in status_text.upper():
        return f'<span style="color: #00FFA3; font-weight: bold;">🟢 {status_text}</span>'
    elif "OFFLINE" in status_text.upper() or "FAILED" in status_text.upper():
        return f'<span style="color: #FF3366; font-weight: bold;">🔴 {status_text}</span>'
    elif "STANDBY" in status_text.upper() or "PAUSED" in status_text.upper() or "WAITING" in status_text.upper():
        return f'<span style="color: #FFAA00; font-weight: bold;">🟡 {status_text}</span>'
    else:
        return status_text

if not licenses_df.empty and 'is_active' in licenses_df.columns:
    active_df = licenses_df[licenses_df['is_active'] == True]
    
    if not active_df.empty:
        display_list = []
        total_bal, total_eq, total_prof = 0.0, 0.0, 0.0
        
        for index, row in active_df.iterrows():
            acc = str(row.get('account_number', ''))
            name = row.get('client_name', 'Auto Registered')
            cmd_status = row.get('bot_command', 'NONE') 
            
            bal, eq, prof, status, last_sync = 0.0, 0.0, 0.0, "OFFLINE (គ្មានសេវា)", "-"
            
            if not live_df.empty and 'vps_name' in live_df.columns:
                match = live_df[live_df['vps_name'].astype(str) == acc]
                if not match.empty:
                    bal = float(match.iloc[0].get('balance', 0))
                    eq = float(match.iloc[0].get('equity', 0))
                    prof = float(match.iloc[0].get('profit', 0))
                    status = str(match.iloc[0].get('status', 'ONLINE'))
                    last_sync = str(match.iloc[0].get('last_updated', '-'))
            
            total_bal += bal; total_eq += eq; total_prof += prof
            
            # Use the format_status function here
            formatted_status = format_status(status)

            display_list.append({
                "លេខគណនី (ID)": acc,
                "ឈ្មោះភ្ញៀវ": name,
                "ស្ថានភាព (Status)": formatted_status,
                "បញ្ជាបច្ចុប្បន្ន": cmd_status,
                "លុយក្នុងកុង": f"${bal:,.2f}",
                "ប្រាក់ចំណេញ": f"${prof:,.2f}",
                "អាប់ដេត": last_sync
            })
            
        colA, colB, colC = st.columns(3)
        colA.metric("💰 ទឹកប្រាក់សរុប", f"${total_bal:,.2f}")
        colB.metric("🛡️ សមតុល្យរួម", f"${total_eq:,.2f}")
        colC.metric("📈 ប្រាក់ចំណេញរួម", f"${total_prof:,.2f}")
        
        st.write("")
        # We need to use st.markdown to render HTML for the color formatting in the dataframe
        df_to_display = pd.DataFrame(display_list)
        st.write(df_to_display.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # ==========================================
        # ផ្នែកទី ៣៖ ប្រព័ន្ធបញ្ជាពីចម្ងាយ (REMOTE CONTROL)
        # ==========================================
        st.write("---")
        st.subheader("🎮 ប្រព័ន្ធបញ្ជាពីចម្ងាយ (REMOTE COMMAND CENTER)")
        
        rc_col1, rc_col2 = st.columns([1, 2])
        with rc_col1:
            cmd_target = st.selectbox("🎯 ជ្រើសរើស Bot គោលដៅ៖", active_df['account_number'])
        
        with rc_col2:
            st.write("⚡ ផ្ទាំងបញ្ជា (Action Panel):")
            b1, b2, b3 = st.columns(3)
            
            if b1.button("⏸ ផ្អាក (Pause Bot)", use_container_width=True):
                supabase.table("mt5_licenses").update({"bot_command": "PAUSE"}).eq("account_number", cmd_target).execute()
                st.success(f"បានបញ្ជូនបញ្ជា PAUSE ទៅកាន់ {cmd_target}")
                
            if b2.button("▶️ បន្ត (Resume Bot)", use_container_width=True):
                supabase.table("mt5_licenses").update({"bot_command": "NONE"}).eq("account_number", cmd_target).execute()
                st.success(f"បានបញ្ជូនបញ្ជា RESUME ទៅកាន់ {cmd_target}")
                
            if b3.button("🛑 បិទអូឌ័រទាំងអស់", type="primary", use_container_width=True):
                supabase.table("mt5_licenses").update({"bot_command": "CLOSE_ALL"}).eq("account_number", cmd_target).execute()
                st.error(f"បានបញ្ជូនបញ្ជា CLOSE ALL ទៅកាន់ {cmd_target} បន្ទាន់!")

        st.write("")
        with st.expander("⚙️ កែប្រែឈ្មោះ ឬ បិទសិទ្ធិ (Manage Clients)"):
            c1, c2 = st.columns(2)
            with c1:
                target_acc = st.selectbox("ជ្រើសរើសលេខគណនី", active_df['account_number'], key="manage_acc")
                new_name = st.text_input("ប្តូរឈ្មោះចំណាំ (ជម្រើស)", placeholder="ឈ្មោះថ្មី...")
            with c2:
                st.write(""); st.write("")
                if st.button("🚫 បិទសិទ្ធិ (Revoke Access)", use_container_width=True):
                    supabase.table("mt5_licenses").update({"is_active": False}).eq("account_number", target_acc).execute()
                    st.success(f"បានបិទសិទ្ធិគណនី {target_acc} រួចរាល់!")
                    st.rerun()
                if st.button("📝 រក្សាទុកឈ្មោះថ្មី", use_container_width=True) and new_name:
                    supabase.table("mt5_licenses").update({"client_name": new_name}).eq("account_number", target_acc).execute()
                    st.success(f"បានប្តូរឈ្មោះទៅជា {new_name} រួចរាល់!")
                    st.rerun()

    else:
        st.info("មិនទាន់មានគណនីណាត្រូវបានអនុញ្ញាតនៅឡើយទេ។")
else:
    st.info("ប្រព័ន្ធកំពុងរង់ចាំការតភ្ជាប់...")

st.write("---")

col_R1, col_R2, col_R3 = st.columns([1, 2, 1])
with col_R2:
    if st.button("🔄 REFRESH DATA", use_container_width=True):
        st.rerun()

st.caption("DEV CONTACT: 0967205522 | Hybrid Control Center v2.0")