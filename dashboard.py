import streamlit as st
import pandas as pd
import requests
import time
from supabase import create_client

# ដក load_dotenv ចេញក៏បាន
# ប្រើ st.secrets ដើម្បីហៅ Key
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Hybrid Control Center", page_icon="⚡", layout="wide")

# Custom UI Styling
st.markdown("""
    <style>
    .stApp { background-color: #060a0f; color: #E0E6ED; } 
    h1, h2, h3 { color: #00E5FF !important; font-weight: 900; text-shadow: 0px 0px 10px rgba(0, 229, 255, 0.4); } 
    div[data-testid="stMetricValue"] { color: #00FFA3 !important; font-size: 30px; font-weight: bold; } 
    div[data-testid="stMetricLabel"] { color: #FFAA00 !important; font-size: 14px; font-weight: bold; } 
    .dataframe { border: 1px solid #1a2639; width: 100%; text-align: left; }
    .dataframe th { background-color: #111a26; color: #00E5FF; padding: 10px; }
    .dataframe td { padding: 10px; border-bottom: 1px solid #1a2639; }
    div.stButton > button { font-weight: bold; border-radius: 6px; }
    
    /* Modern Compact Card Style (លែងសូវប្រើ តែទុកក្រែងចង់ប្រើកន្លែងផ្សេង) */
    .client-card {
        background: linear-gradient(135deg, #0b1118 0%, #111a26 100%);
        border-left: 4px solid #00E5FF;
        border: 1px solid #1a2639;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ MASTER CONTROL CENTER")
st.write("---")

# ==========================================
# 🚀 DATA LOADING & MERGING 
# ==========================================
@st.cache_data(ttl=10)
def load_all_licenses():
    df_list = []
    # ១. ទាញពី Table ថ្មី user_licenses
    try:
        res1 = supabase.table("user_licenses").select("*").execute()
        if res1.data:
            d1 = pd.DataFrame(res1.data)
            d1['source_table'] = 'user_licenses'
            df_list.append(d1)
    except: pass
    
    # ២. ទាញពី Table ចាស់ mt5_licenses 
    try:
        res2 = supabase.table("mt5_licenses").select("*").execute()
        if res2.data:
            d2 = pd.DataFrame(res2.data)
            d2['source_table'] = 'mt5_licenses'
            df_list.append(d2)
    except: pass
    
    if df_list:
        combined_df = pd.concat(df_list, ignore_index=True)
        # លុបទិន្នន័យស្ទួនដោយយក Table ថ្មីជាចម្បង
        combined_df = combined_df.drop_duplicates(subset=['account_number'], keep='first')
        return combined_df
    return pd.DataFrame()

licenses_df = load_all_licenses()

def fetch_live_data():
    endpoint = f"{SUPABASE_URL}/rest/v1/bot_status?select=*"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        r = requests.get(endpoint, headers=headers, timeout=5)
        if r.status_code == 200: return r.json()
    except: return []
    return []

live_df = pd.DataFrame(fetch_live_data())

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
# CREATING TABS
# ==========================================
tab_dashboard, tab_license_center = st.tabs(["📊 UNIFIED LIVE SYSTEMS", "🔑 LICENSE MANAGEMENT CENTER"])

# ==========================================
# 📊 TAB 1: UNIFIED LIVE SYSTEMS
# ==========================================
with tab_dashboard:
    st.subheader("💻 ប្រព័ន្ធកំពុងដំណើរការ (UNIFIED LIVE SYSTEMS)")

    def format_status(status_text):
        if "ONLINE" in str(status_text).upper():
            return f'<span style="color: #00FFA3; font-weight: bold;">🟢 {status_text}</span>'
        elif "OFFLINE" in str(status_text).upper() or "FAILED" in str(status_text).upper():
            return f'<span style="color: #FF3366; font-weight: bold;">🔴 {status_text}</span>'
        else:
            return f'<span style="color: #FFAA00; font-weight: bold;">🟡 {status_text}</span>'

    if not licenses_df.empty and 'is_active' in licenses_df.columns:
        active_df = licenses_df[licenses_df['is_active'] == True]
        
        if not active_df.empty:
            display_list = []
            total_bal, total_eq, total_prof = 0.0, 0.0, 0.0
            
            # បន្ថែមលេខរៀង (No.)
            row_index = 1
            
            for index, row in active_df.iterrows():
                acc = str(row.get('account_number', ''))
                name = row.get('owner_name', row.get('client_name', 'Auto Registered'))
                bal, eq, prof, status, last_sync = 0.0, 0.0, 0.0, "OFFLINE", "-"
                total_pos, today_lots, total_lots_db = 0, 0.0, 0.0
                t1, t2, t3, t4 = 0.0, 0.0, 0.0, 0.0
                
                if not live_df.empty and 'vps_name' in live_df.columns:
                    match = live_df[live_df['vps_name'].astype(str) == acc]
                    if not match.empty:
                        m_data = match.iloc[0]
                        bal = safe_float(m_data.get('balance'))
                        eq = safe_float(m_data.get('equity'))
                        prof = safe_float(m_data.get('profit'))
                        status = str(m_data.get('status', 'ONLINE'))
                        last_sync = str(m_data.get('last_updated', '-')).split('.')[0].replace('T', ' ')
                        total_pos = safe_int(m_data.get('total_pos'))
                        today_lots = safe_float(m_data.get('today_lots'))
                        total_lots_db = safe_float(m_data.get('total_lots'))
                        t1 = safe_float(m_data.get('t_1')); t2 = safe_float(m_data.get('t_2'))
                        t3 = safe_float(m_data.get('t_3')); t4 = safe_float(m_data.get('t_4'))
                
                total_bal += bal; total_eq += eq; total_prof += prof
                formatted_status = format_status(status)

                display_list.append({
                    "ល.រ": row_index,
                    "Account ID": acc, "Name": name, "Status": formatted_status,
                    "Balance": f"${bal:,.2f}", "Float P/L": f"${prof:,.2f}", "Active Nodes": total_pos,
                    "Today Lots": f"{today_lots:.2f}", "Total Lots": f"{total_lots_db:.2f}",
                    "T-1": f"{t1:.2f}", "T-2": f"{t2:.2f}", "T-3": f"{t3:.2f}", "T-4": f"{t4:.2f}",
                    "អាប់ដេត": last_sync
                })
                row_index += 1
                
            colA, colB, colC = st.columns(3)
            colA.metric("💰 ទឹកប្រាក់សរុប (Net Balance)", f"${total_bal:,.2f}")
            colB.metric("🛡️ សមតុល្យរួម (Live Equity)", f"${total_eq:,.2f}")
            colC.metric("📈 ប្រាក់ចំណេញរួម (Float P/L)", f"${total_prof:,.2f}")
            
            st.write("")
            df_to_display = pd.DataFrame(display_list)
            st.write(df_to_display.to_html(escape=False, index=False), unsafe_allow_html=True)
            
            # REMOTE CONTROL SECTION
            st.write("---")
            st.subheader("🎮 ប្រព័ន្ធបញ្ជាពីចម្ងាយ (REMOTE COMMAND CENTER)")
            rc_col1, rc_col2 = st.columns([1, 2])
            with rc_col1:
                cmd_target = st.selectbox("🎯 ជ្រើសរើសគណនីគោលដៅ៖", active_df['account_number'], key="remote_acc_select")
            with rc_col2:
                st.write("⚡ **Action Panel:**")
                b1, b2, b3 = st.columns(3)
                if b1.button("⏸ ផ្អាក (Pause)", use_container_width=True):
                    supabase.table("user_licenses").update({"bot_command": "PAUSE"}).eq("account_number", cmd_target).execute()
                    st.success(f"✅ បានផ្ញើពាក្យបញ្ជា PAUSE ទៅ {cmd_target}"); time.sleep(0.5); st.rerun()
                if b2.button("▶️ បន្ត (Resume)", use_container_width=True):
                    supabase.table("user_licenses").update({"bot_command": "NONE"}).eq("account_number", cmd_target).execute()
                    st.success(f"✅ បានផ្ញើពាក្យបញ្ជា RESUME ទៅ {cmd_target}"); time.sleep(0.5); st.rerun()
                if b3.button("🛑 បិទទាំងអស់ (Close All)", type="primary", use_container_width=True):
                    supabase.table("user_licenses").update({"bot_command": "CLOSE_ALL"}).eq("account_number", cmd_target).execute()
                    st.error(f"🚨 បានផ្ញើពាក្យបញ្ជា CLOSE ALL ទៅ {cmd_target}!"); time.sleep(0.5); st.rerun()
            
            # EDIT NAME SECTION (ទាញមកវិញតាមសំណូមពរ)
            st.write("---")
            st.subheader("✏️ កែប្រែឈ្មោះអតិថិជន (EDIT CLIENT NAME)")
            edit_col1, edit_col2, edit_col3 = st.columns([1, 1.5, 1])
            with edit_col1:
                edit_target = st.selectbox("🎯 ជ្រើសរើសគណនីដើម្បីកែឈ្មោះ៖", licenses_df['account_number'], key="edit_name_select")
            with edit_col2:
                # ទាញឈ្មោះចាស់មកបង្ហាញ
                old_name = licenses_df[licenses_df['account_number'] == edit_target].iloc[0].get('owner_name', '')
                if not old_name:
                    old_name = licenses_df[licenses_df['account_number'] == edit_target].iloc[0].get('client_name', '')
                new_name = st.text_input("📝 បញ្ចូលឈ្មោះថ្មី:", value=old_name, key="new_name_input")
            with edit_col3:
                st.write("") # សម្រាប់តម្រឹមអោយស្មើ Text Input
                st.write("")
                if st.button("💾 រក្សាទុក (Save)", use_container_width=True):
                    if new_name:
                        target_row = licenses_df[licenses_df['account_number'] == edit_target].iloc[0]
                        tbl = target_row['source_table']
                        # Update ទាំង owner_name និង client_name ដើម្បីកុំអោយ Error បើវាអត់មាន Column មួយណា
                        try:
                            supabase.table(tbl).update({"owner_name": new_name}).eq("account_number", edit_target).execute()
                        except: pass
                        try:
                            supabase.table(tbl).update({"client_name": new_name}).eq("account_number", edit_target).execute()
                        except: pass
                        st.success(f"✅ បានប្តូរឈ្មោះទៅជា {new_name} រួចរាល់!"); time.sleep(0.5); st.rerun()

        else:
            st.info("មិនទាន់មានគណនីណាត្រូវបានអនុញ្ញាតនៅឡើយទេ។")
    else:
        st.info("ប្រព័ន្ធកំពុងរង់ចាំទិន្នន័យ...")

# ==============================================================================
# 🔑 TAB 2: LICENSE MANAGEMENT CENTER (រៀបចំថ្មីជាទម្រង់តារាង)
# ==============================================================================
# ==============================================================================
# 🔑 TAB 2: LICENSE MANAGEMENT CENTER (អាប់ដេតថ្មីមានលេខរៀង និងប៊ូតុងលុប)
# ==============================================================================
with tab_license_center:
    st.subheader("🔑 LICENSE & DATA ANALYTICS EMPIRE")
    st.write("---")
    
    # ... (រក្សាទុកកូដក្រាហ្វ និង Alert ដដែល) ...
    
    st.markdown("### 📋 Quick Search & License Database")
    search_q = st.text_input("ស្វែងរកតាមលេខ Account ID ឬ ឈ្មោះអតិថិជន:", placeholder="វាយបញ្ចូលទីនេះ...")

    if not licenses_df.empty:
        if search_q:
            filtered_licenses = licenses_df[
                licenses_df['account_number'].astype(str).str.contains(search_q) | 
                licenses_df['owner_name'].astype(str).str.contains(search_q, case=False, na=False)
            ]
        else:
            filtered_licenses = licenses_df

        st.markdown(f"📊 លទ្ធផលសរុប៖ **{len(filtered_licenses)} គណនី**")
        st.markdown("<hr style='margin: 5px 0px; border: 1px solid #1a2639'>", unsafe_allow_html=True)
        
        # Header Row
        h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([0.5, 1.5, 2, 2.5, 1.5, 1.5])
        h_col1.markdown("**#**") # លេខរៀង
        h_col2.markdown("**🆔 Exness ID**")
        h_col3.markdown("**👤 ឈ្មោះ**")
        h_col4.markdown("**🖥️ HWID**")
        h_col5.markdown("**📊 Status**")
        h_col6.markdown("**⚙️ Action**")
        st.markdown("<hr style='margin: 5px 0px; border: 1px solid #1a2639'>", unsafe_allow_html=True)
        
        # Data Rows
        for idx, row in filtered_licenses.iterrows():
            acc_id = row.get('account_number', 'Unknown')
            owner = row.get('owner_name', 'No Name')
            hwid = str(row.get('hwid', 'N/A'))[:15] + "..."
            is_active = row.get('is_active', False)
            tbl_source = row.get('source_table', 'user_licenses')
            
            c1, c2, c3, c4, c5, c6 = st.columns([0.5, 1.5, 2, 2.5, 1.5, 1.5])
            
            c1.write(f"{idx + 1}") # លេខរៀង
            c2.markdown(f"<b>{acc_id}</b>", unsafe_allow_html=True)
            c3.write(owner)
            c4.write(hwid)
            c5.write("✅" if is_active else "⏳")
            
            with c6:
                btn_cols = st.columns(2)
                # Approve / Revoke Buttons
                is_disabled = bool(is_active == True)
                if btn_cols[0].button("✅", key=f"app_{acc_id}_{idx}", help="Approve", disabled=is_disabled):
                    supabase.table(tbl_source).update({"is_active": True}).eq("account_number", acc_id).execute()
                    st.rerun()
                
                # ប៊ូតុង លុប (Delete)
                if btn_cols[1].button("🗑️", key=f"del_{acc_id}_{idx}", help="លុបចោល"):
                    supabase.table(tbl_source).delete().eq("account_number", acc_id).execute()
                    st.toast(f"🗑️ បានលុប {acc_id} ចេញពីប្រព័ន្ធ!")
                    time.sleep(0.5)
                    st.rerun()

            st.markdown("<hr style='margin: 5px 0px; border-top: 1px solid #1a2639'>", unsafe_allow_html=True)

# ==========================================
# 🔄 REFRESH BUTTON
# ==========================================
st.write("---")
col_R1, col_R2, col_R3 = st.columns([1, 2, 1])
with col_R2:
    if st.button("🔄 REFRESH ALL DATA", use_container_width=True):
        st.rerun()