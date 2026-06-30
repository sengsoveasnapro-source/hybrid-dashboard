import streamlit as st
import requests
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time # ការពារការគាំងពេលចុច Refresh ឬលុប

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
    th:nth-child(3), td:nth-child(3) { text-align: center; }
    
    /* Custom Styling for Command Buttons */
    div.stButton > button { font-weight: bold; border-radius: 6px; }
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

# 🚀 Helper Functions ការពារការចេញអក្សរ nan ពេល Database ទទេ
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

# ==========================================
# ផ្នែកទី ១៖ សំណើសុំសិទ្ធិថ្មី 
# ==========================================
st.subheader("🔔 សំណើសុំសិទ្ធិថ្មី (Pending Approvals)")

if not licenses_df.empty and 'is_active' in licenses_df.columns:
    pending_df = licenses_df[licenses_df['is_active'] == False]
    
    if not pending_df.empty:
        for index, row in pending_df.iterrows():
            acc = row.get('account_number', 'Unknown')
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.warning(f"⚠️ មានសំណើថ្មីពីគណនីលេខ៖ **{acc}**")
            
            if col2.button(f"✅ អនុម័ត (Approve)", key=f"approve_{acc}", use_container_width=True):
                supabase.table("mt5_licenses").update({"is_active": True}).eq("account_number", acc).execute()
                st.success(f"បានអនុម័តគណនី {acc} រួចរាល់!")
                time.sleep(1)
                st.rerun()
                
            if col3.button(f"🗑️ បដិសេធ (Reject)", key=f"reject_{acc}", type="primary", use_container_width=True):
                supabase.table("mt5_licenses").delete().eq("account_number", acc).execute()
                st.error(f"បានបដិសេធ និងលុបគណនី {acc} ចោលរួចរាល់!")
                time.sleep(1)
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
    if "ONLINE" in str(status_text).upper():
        return f'<span style="color: #00FFA3; font-weight: bold;">🟢 {status_text}</span>'
    elif "OFFLINE" in str(status_text).upper() or "FAILED" in str(status_text).upper():
        return f'<span style="color: #FF3366; font-weight: bold;">🔴 {status_text}</span>'
    elif "STANDBY" in str(status_text).upper() or "PAUSED" in str(status_text).upper() or "WAITING" in str(status_text).upper() or "LOCKED" in str(status_text).upper():
        return f'<span style="color: #FFAA00; font-weight: bold;">🟡 {status_text}</span>'
    else:
        return status_text

if not licenses_df.empty and 'is_active' in licenses_df.columns:
    active_df = licenses_df[licenses_df['is_active'] == True]
    
    if not active_df.empty:
        display_list = []
        total_bal, total_eq, total_prof = 0.0, 0.0, 0.0
        total_buy_pos, total_buy_lots = 0, 0.0
        total_sell_pos, total_sell_lots = 0, 0.0
        total_active_nodes, total_network_lots = 0, 0.0
        total_today_lots = 0.0
        
        for index, row in active_df.iterrows():
            acc = str(row.get('account_number', ''))
            name = row.get('client_name', 'Auto Registered')
            
            # កំណត់តម្លៃដើម
            bal, eq, prof, status, last_sync = 0.0, 0.0, 0.0, "OFFLINE (គ្មានសេវា)", "-"
            total_pos, today_lots, total_lots_db = 0, 0.0, 0.0
            buy_count, buy_lots, sell_count, sell_lots = 0, 0.0, 0, 0.0
            cycle_volume = 0.0
            t1, t2, t3, t4, t5, t6, t7 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
            
            if not live_df.empty and 'vps_name' in live_df.columns:
                match = live_df[live_df['vps_name'].astype(str) == acc]
                if not match.empty:
                    m_data = match.iloc[0]
                    bal = safe_float(m_data.get('balance'))
                    eq = safe_float(m_data.get('equity'))
                    prof = safe_float(m_data.get('profit'))
                    
                    status = str(m_data.get('status', 'ONLINE'))
                    if status.lower() == 'nan': status = 'OFFLINE (គ្មានសេវា)'
                        
                    last_sync = str(m_data.get('last_updated', '-'))
                    if last_sync.lower() == 'nan': last_sync = '-'
                    
                    total_pos = safe_int(m_data.get('total_pos'))
                    today_lots = safe_float(m_data.get('today_lots'))
                    
                    # 🚀 ទាញយកឱ្យត្រូវនឹង Column Database
                    buy_count = safe_int(m_data.get('long_nodes'))
                    buy_lots = safe_float(m_data.get('long_lots'))
                    sell_count = safe_int(m_data.get('short_nodes'))
                    sell_lots = safe_float(m_data.get('short_lots'))
                    cycle_volume = safe_float(m_data.get('cycle_volume'))
                    total_lots_db = safe_float(m_data.get('Total_lots'))
                    
                    t1 = safe_float(m_data.get('t_1'))
                    t2 = safe_float(m_data.get('t_2'))
                    t3 = safe_float(m_data.get('t_3'))
                    t4 = safe_float(m_data.get('t_4'))
                    t5 = safe_float(m_data.get('t_5'))
                    t6 = safe_float(m_data.get('t_6'))
                    t7 = safe_float(m_data.get('t_7'))
            
            total_bal += bal; total_eq += eq; total_prof += prof
            total_buy_pos += buy_count; total_buy_lots += buy_lots
            total_sell_pos += sell_count; total_sell_lots += sell_lots
            total_active_nodes += total_pos; total_today_lots += today_lots
            total_network_lots += total_lots_db
            
            formatted_status = format_status(status)
            
            # កាត់ពេលវេលាអាប់ដេតឱ្យស្អាត (លុប T និងខ្ទង់ទសភាគវិនាទីចេញ)
            clean_time = last_sync.split('.')[0].replace('T', ' ') if last_sync != '-' else '-'

            display_list.append({
                "ID": acc,
                "Name": name,
                "Status": formatted_status,
                "Balance": f"${bal:,.2f}",
                "Float P/L": f"${prof:,.2f}",
                "Active Nodes": total_pos,
                "Today Lots": f"{today_lots:.2f}",
                "Total Lots": f"{total_lots_db:.2f}",
                "Long Nodes": buy_count,
                "Long Lots": f"{buy_lots:.2f}",
                "Short Nodes": sell_count,
                "Short Lots": f"{sell_lots:.2f}",
                "T-1": f"{t1:.2f}", 
                "T-2": f"{t2:.2f}", 
                "T-3": f"{t3:.2f}", 
                "T-4": f"{t4:.2f}",
                "T-5": f"{t5:.2f}", 
                "T-6": f"{t6:.2f}", 
                "T-7": f"{t7:.2f}",
                "អាប់ដេត": clean_time
            })
            
        colA, colB, colC = st.columns(3)
        colA.metric("💰 ទឹកប្រាក់សរុប (Net Balance)", f"${total_bal:,.2f}")
        colB.metric("🛡️ សមតុល្យរួម (Live Equity)", f"${total_eq:,.2f}")
        colC.metric("📈 ប្រាក់ចំណេញរួម (Float P/L)", f"${total_prof:,.2f}")
        
        colD, colE, colH = st.columns(3)
        colD.metric("Active Nodes", total_active_nodes)
        colE.metric("Today Lots", f"{total_today_lots:.2f}")
        colH.metric("Total Lots", f"{total_network_lots:.2f}")
        
        st.write("")
        df_to_display = pd.DataFrame(display_list)
        st.write(df_to_display.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # ==========================================
        # ផ្នែកទី ៣៖ ប្រព័ន្ធបញ្ជាពីចម្ងាយ (REMOTE CONTROL)
        # ==========================================
        st.write("---")
        st.subheader("🎮 ប្រព័ន្ធបញ្ជាពីចម្ងាយ (REMOTE COMMAND CENTER)")
        
        rc_col1, rc_col2 = st.columns([1, 2])
        with rc_col1:
            cmd_target = st.selectbox("🎯 ជ្រើសរើសលេខគណនី (Bot) គោលដៅ៖", active_df['account_number'], key="remote_acc_select")
        
        with rc_col2:
            st.write("⚡ **ផ្ទាំងបញ្ជាបន្ទាន់ (Action Panel):**")
            b1, b2, b3 = st.columns(3)
            
            if b1.button("⏸ ផ្អាក (Pause Trading)", use_container_width=True):
                try:
                    supabase.table("mt5_licenses").update({"bot_command": "PAUSE"}).eq("account_number", cmd_target).execute()
                    st.success(f"✅ បានបញ្ជូនបញ្ជា PAUSE ទៅកាន់គណនី {cmd_target} រួចរាល់! វានឹងឈប់ចូល Order ថ្មី។")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ បរាជ័យក្នុងការបញ្ជូនបញ្ជា: {e}")
                    
            if b2.button("▶️ បន្ត (Resume Trading)", use_container_width=True):
                try:
                    supabase.table("mt5_licenses").update({"bot_command": "NONE"}).eq("account_number", cmd_target).execute()
                    st.success(f"✅ បានបញ្ជូនបញ្ជា RESUME ទៅកាន់គណនី {cmd_target} រួចរាល់! វានឹងបន្តទិញលក់ធម្មតាវិញ។")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ បរាជ័យក្នុងការបញ្ជូនបញ្ជា: {e}")
                    
            if b3.button("🛑 បិទអូឌ័រទាំងអស់ (Close All)", type="primary", use_container_width=True):
                try:
                    supabase.table("mt5_licenses").update({"bot_command": "CLOSE_ALL"}).eq("account_number", cmd_target).execute()
                    st.error(f"🚨 បានបញ្ជូនបញ្ជា CLOSE ALL ទៅកាន់គណនី {cmd_target}! រាល់ Order ទាំងអស់កំពុងត្រូវបានបិទ។")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ បរាជ័យក្នុងការបញ្ជូនបញ្ជា: {e}")

        # ==========================================
        # កែប្រែឈ្មោះ និង ដកសិទ្ធិ
        # ==========================================
        st.write("")
        with st.expander("⚙️ កែប្រែឈ្មោះ ឬ ដកគណនី (Manage Clients)"):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                target_acc = st.selectbox("ជ្រើសរើសលេខគណនី", active_df['account_number'], key="manage_acc")
                new_name = st.text_input("ប្តូរឈ្មោះចំណាំ (ជម្រើស)", placeholder="ឈ្មោះថ្មី...")
            with c2:
                st.write(""); st.write("")
                if st.button("🚫 បិទសិទ្ធិ (Revoke Access)", use_container_width=True):
                    supabase.table("mt5_licenses").update({"is_active": False}).eq("account_number", target_acc).execute()
                    st.success(f"បានបិទសិទ្ធិគណនី {target_acc} រួចរាល់!")
                    time.sleep(1)
                    st.rerun()
                if st.button("📝 រក្សាទុកឈ្មោះថ្មី", use_container_width=True) and new_name:
                    supabase.table("mt5_licenses").update({"client_name": new_name}).eq("account_number", target_acc).execute()
                    st.success(f"បានប្តូរឈ្មោះទៅជា {new_name} រួចរាល់!")
                    time.sleep(1)
                    st.rerun()
            with c3:
                st.write(""); st.write("")
                if st.button("🗑️ លុបគណនី (Remove)", type="primary", use_container_width=True):
                    supabase.table("mt5_licenses").delete().eq("account_number", target_acc).execute()
                    st.error(f"បានលុបគណនី {target_acc} ចេញពីប្រព័ន្ធទាំងស្រុង!")
                    time.sleep(1)
                    st.rerun()

    else:
        st.info("មិនទាន់មានគណនីណាត្រូវបានអនុញ្ញាតនៅឡើយទេ។")
else:
    st.info("ប្រព័ន្ធកំពុងរង់ចាំការតភ្ជាប់...")

st.write("---")

# ==========================================
# 🔥 ផ្នែកថ្មី៖ ទាញយកទិន្នន័យពី GITHUB RELEASES
# ==========================================
st.subheader("📥 កំណែអាប់ដេតថ្មីៗ (System Updates)")

@st.cache_data(ttl=3600) 
def get_github_releases():
    url = "https://api.github.com/repos/sengsoveasnapro-source/hybrid-dashboard/releases"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return None
    return None

releases = get_github_releases()

if releases:
    for release in releases[:3]: 
        version = release.get("tag_name", "Unknown Version")
        title = release.get("name", "No Title")
        date_str = release.get("published_at", "")
        body = release.get("body", "មិនមានព័ត៌មានលម្អិតទេ")
        
        pub_date = "Unknown Date"
        if date_str:
            try:
                pub_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%d %b %Y - %H:%M")
            except:
                pub_date = date_str

        with st.expander(f"📦 ជំនាន់: {version} | {title} - ({pub_date})"):
            st.markdown(body)
            
            assets = release.get("assets", [])
            if assets:
                st.write("**ឯកសារសម្រាប់ទាញយក:**")
                for asset in assets:
                    file_name = asset.get("name")
                    download_url = asset.get("browser_download_url")
                    st.markdown(f"⬇️ [{file_name}]({download_url})")
else:
    st.info("មិនមានកំណែអាប់ដេតថ្មី ឬមិនអាចភ្ជាប់ទៅកាន់ GitHub បានទេ។")

st.write("---")

col_R1, col_R2, col_R3 = st.columns([1, 2, 1])
with col_R2:
    if st.button("🔄 REFRESH DATA", use_container_width=True):
        st.rerun()

st.caption("DEV CONTACT: 0967205522 | Hybrid Control Center v2.0")