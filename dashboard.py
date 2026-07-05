import streamlit as st
import pandas as pd
import requests
import time
import os
from dotenv import load_dotenv
from supabase import create_client

# ==========================================
# 💵 កំណត់តម្លៃ COMMISSION ពី EXNESS (គិតជាដុល្លារក្នុង ១ ឡូត៍)
# ==========================================
COMMISSION_PER_LOT = 5.0  # 👈 បងអាចប្តូរលេខនេះបាន! (ឧទាហរណ៍៖ បើ Exness ឱ្យ $10 ក្នុង១ឡូត៍ សូមប្តូរទៅ 10.0)

# ==========================================
# 🔒 SECURITY: PASSWORD PROTECTION
# ==========================================
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # ⚠️ បងអាចប្តូរ Password ត្រង់នេះបានតាមចិត្ត
        if st.session_state["password"] == "AAaa112233^^66":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # លុបចេញកុំឱ្យនៅសល់ក្នុងអង្គចងចាំ
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # លើកដំបូងដែលបើក ឱ្យវាបង្ហាញផ្ទាំងសួរ Password
        st.text_input(
            "🔒 ប្រព័ន្ធត្រូវបានចាក់សោរ! សូមបញ្ចូលលេខសម្ងាត់ (Password):", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # បើវាយខុស បង្ហាញអក្សរក្រហម រួចឱ្យវាយម្តងទៀត
        st.text_input(
            "🔒 ប្រព័ន្ធត្រូវបានចាក់សោរ! សូមបញ្ចូលលេខសម្ងាត់ (Password):", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ លេខសម្ងាត់មិនត្រឹមត្រូវទេ! អ្នកមិនមានសិទ្ធិចូលមើលទេ។")
        return False
    else:
        # បើវាយត្រូវ អនុញ្ញាតឱ្យចូល
        return True

# ហៅ Function ឆែក Password បើអត់ត្រូវទេ បញ្ឈប់ការ Run កូដខាងក្រោមទាំងអស់
if not check_password():
    st.stop()


# 🚀 ទាញយកបរិស្ថាន (Environment Variables)
load_dotenv()

# 🛡️ ប្រព័ន្ធការពារ Error: ព្យាយាមអានពី st.secrets មុន បើអត់មាន អានពី .env វិញ
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bqozwahxwhnpnasixxps.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "") # បើប្រើ .env ត្រូវប្រាកដថាមាន Key ក្នុងនោះ

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
            total_today_commission = 0.0 # 👈 អញ្ញាតរាប់ Commission សរុប
            
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
                
                # 💵 គណនា Commission របស់គណនីនេះប្រចាំថ្ងៃនេះ
                today_commission = today_lots * COMMISSION_PER_LOT
                
                total_bal += bal; total_eq += eq; total_prof += prof
                total_today_commission += today_commission # បូកចូល Commission រួម
                
                formatted_status = format_status(status)

                display_list.append({
                    "ល.រ": row_index,
                    "Account ID": acc, "Name": name, "Status": formatted_status,
                    "Balance": f"${bal:,.2f}", "Float P/L": f"${prof:,.2f}", 
                    "Active Nodes": total_pos,
                    "Today Lots": f"{today_lots:.2f}",
                    "🎁 Com ថ្ងៃនេះ": f"${today_commission:,.2f}", # 👈 បង្ហាញ Commission
                    "Total Active Lots": f"{total_lots_db:.2f}",
                    "អាប់ដេត": last_sync
                })
                row_index += 1
                
            # 🚀 បង្ហាញតួលេខធំៗ ៤ នៅខាងលើ
            colA, colB, colC, colD = st.columns(4)
            colA.metric("💰 ទឹកប្រាក់សរុប (Net Balance)", f"${total_bal:,.2f}")
            colB.metric("🛡️ សមតុល្យរួម (Live Equity)", f"${total_eq:,.2f}")
            colC.metric("📈 ប្រាក់ចំណេញអតិថិជន (Float P/L)", f"${total_prof:,.2f}")
            colD.metric("🎁 កម្រៃជើងសារសរុបថ្ងៃនេះ (Est. Com)", f"${total_today_commission:,.2f}") # 👈 ផ្ទាំងថ្មី
            
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
            
            # EDIT NAME SECTION 
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
# 🔑 TAB 2: LICENSE MANAGEMENT CENTER 
# ==============================================================================
with tab_license_center:
    st.subheader("🔑 LICENSE & DATA ANALYTICS EMPIRE")
    st.write("---")
    
    # ------------------------------------------
    # 📈 ក្រាហ្វវិភាគប្រាក់ចំណេញ 
    # ------------------------------------------
    st.markdown("### 📈 Profit Analytics & Drawdown Shield")
    col_chart, col_alert = st.columns([2, 1])
    
    with col_chart:
        if not live_df.empty and 'profit' in live_df.columns and 'vps_name' in live_df.columns:
            analytics_df = live_df[['vps_name', 'balance', 'equity', 'profit']].copy()
            analytics_df['profit'] = analytics_df['profit'].apply(safe_float)
            top_earners = analytics_df.sort_values(by='profit', ascending=False).head(5)
            st.caption("🏆 គណនីកំពូលរកប្រាក់ចំណេញបានច្រើនជាងគេ")
            st.bar_chart(data=top_earners.set_index('vps_name')['profit'], height=220)
            
    with col_alert:
        st.caption("🚨 Drawdown Risk Alerts (> 15%)")
        danger_found = False
        if not live_df.empty and 'balance' in live_df.columns:
            for _, b_row in analytics_df.iterrows():
                bal = safe_float(b_row['balance'])
                eq = safe_float(b_row['equity'])
                if bal > 0:
                    dd_pct = ((bal - eq) / bal) * 100
                    if dd_pct >= 15.0:
                        st.error(f"⚠️ **Account: {b_row['vps_name']}**\nDrawdown: **{dd_pct:.1f}%**")
                        danger_found = True
        if not danger_found:
            st.success("✅ គ្រប់គណនីទាំងអស់មានសុវត្ថិភាពល្អ។")

    st.write("---")
    
    # ------------------------------------------
    # ➕ បន្ថែមអតិថិជនថ្មី (ADD NEW CLIENT)
    # ------------------------------------------
    with st.expander("➕ បន្ថែមអតិថិជនថ្មីចូលប្រព័ន្ធ (Add New Client)"):
        with st.form("add_client_form"):
            col1, col2 = st.columns(2)
            new_acc_id = col1.text_input("លេខ Account ID (ឧទាហរណ៍៖ 12345678)")
            new_client_name = col2.text_input("ឈ្មោះអតិថិជន (ចំណាំទុកមើល)")
            new_hwid = st.text_input("HWID (កូដម៉ាស៊ីនដែលអតិថិជនផ្ញើមក)")
            
            submit_button = st.form_submit_button("រក្សាទុកចូល Database 💾")
            
            if submit_button:
                if new_acc_id and new_client_name:
                    # 💡 បង្កើត ID ថ្មីដោយប្រើ Time (ការពារការជាន់លេខ ID ក្នុង Database)
                    safe_id = int(time.time())
                    
                    new_data = {
                        "id": safe_id,  # 👈 បញ្ចូល ID ដោយផ្ទាល់ដើម្បីកុំឱ្យបុកគ្នា
                        "account_number": new_acc_id,
                        "owner_name": new_client_name,
                        "hwid": new_hwid,
                        "is_active": False  # ដាក់ False សិនដើម្បីឱ្យ Admin ជាអ្នក Approve តាមក្រោយ
                    }
                    try:
                        supabase.table("user_licenses").insert(new_data).execute()
                        st.success(f"✅ បានបន្ថែមអតិថិជន {new_client_name} ចូលក្នុងប្រព័ន្ធដោយជោគជ័យ!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ កំហុសបច្ចេកទេស៖ សូមប្រាកដថាលេខគណនីនេះមិនទាន់មានក្នុងប្រព័ន្ធ។ ({e})")
                else:
                    st.warning("⚠️ សូមបំពេញលេខ Account ID និងឈ្មោះអតិថិជនឱ្យបានត្រឹមត្រូវ!")

    st.write("---")

    # ------------------------------------------
    # 🔍 ស្វែងរក និងគ្រប់គ្រងអតិថិជន 
    # ------------------------------------------
    st.markdown("### 📋 Quick Search & License Database")
    search_q = st.text_input("ស្វែងរកតាមលេខ Account ID ឬ ឈ្មោះអតិថិជន:", placeholder="វាយបញ្ចូលទីនេះ...")

    st.write("")
    if not licenses_df.empty:
        if search_q:
            filtered_licenses = licenses_df[
                licenses_df['account_number'].astype(str).str.contains(search_q) | 
                licenses_df['owner_name'].astype(str).str.contains(search_q, case=False, na=False) |
                licenses_df['client_name'].astype(str).str.contains(search_q, case=False, na=False)
            ]
        else:
            filtered_licenses = licenses_df

        st.markdown(f"📊 លទ្ធផលសរុប៖ **{len(filtered_licenses)} គណនី**")
        
        st.markdown("<hr style='margin: 5px 0px; border: 1px solid #1a2639'>", unsafe_allow_html=True)
        
        # Header Row
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1.5, 2, 2.5, 1.5, 2])
        h_col1.markdown("**No. 🆔 Exness ID**")
        h_col2.markdown("**👤 ឈ្មោះអតិថិជន**")
        h_col3.markdown("**🖥️ HWID / 📂 Table**")
        h_col4.markdown("**📊 ស្ថានភាព**")
        h_col5.markdown("**⚙️ សកម្មភាព (Action)**")
        st.markdown("<hr style='margin: 5px 0px; border: 1px solid #1a2639'>", unsafe_allow_html=True)
        
        # Data Rows
        for row_index, (idx, row) in enumerate(filtered_licenses.iterrows(), start=1):
            acc_id = row.get('account_number', 'Unknown')
            owner = row.get('owner_name', row.get('client_name', 'Unknown User'))
            hwid = str(row.get('hwid', 'No HWID Bound'))[:20] + "..." if row.get('hwid') else "No HWID"
            is_active = row.get('is_active', False)
            tbl_source = row.get('source_table', 'user_licenses')
            
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2.5, 1.5, 2])
            
            c1.markdown(f"<span style='font-size:16px; color:#00E5FF;'><b>{row_index}. {acc_id}</b></span>", unsafe_allow_html=True)
            c2.markdown(f"**{owner}**")
            c3.markdown(f"<span style='font-size:13px; color:#7f8c8d;'>{hwid}<br>📂 {tbl_source}</span>", unsafe_allow_html=True)
            
            if is_active:
                c4.markdown("<span style='color:#00FFA3; font-weight:bold;'>● ACTIVE</span>", unsafe_allow_html=True)
            else:
                c4.markdown("<span style='color:#FFAA00; font-weight:bold;'>● PENDING</span>", unsafe_allow_html=True)
                
            with c5:
                is_button_disabled = bool(is_active == True)
                
                # ប៊ូតុង Approve & Revoke
                btn_c1, btn_c2 = st.columns(2)
                if btn_c1.button("✅ Approve", key=f"app_{acc_id}_{idx}", use_container_width=True, disabled=is_button_disabled):
                    supabase.table(tbl_source).update({"is_active": True}).eq("account_number", acc_id).execute()
                    st.toast("✅ Approved!")
                    time.sleep(0.3)
                    st.rerun()
                if btn_c2.button("🚫 Revoke", key=f"rev_{acc_id}_{idx}", type="primary", use_container_width=True, disabled=(not is_button_disabled)):
                    supabase.table(tbl_source).update({"is_active": False}).eq("account_number", acc_id).execute()
                    st.toast("🚫 Revoked!")
                    time.sleep(0.3)
                    st.rerun()
            
            st.markdown("<hr style='margin: 5px 0px; border-top: 1px solid #1a2639'>", unsafe_allow_html=True)
            
    else:
        st.info("មិនទាន់មានទិន្នន័យអាជ្ញាប័ណ្ណទេ។")

# ==========================================
# 🔄 REFRESH BUTTON
# ==========================================
st.write("---")
col_R1, col_R2, col_R3 = st.columns([1, 2, 1])
with col_R2:
    if st.button("🔄 REFRESH ALL DATA", use_container_width=True):
        st.rerun()