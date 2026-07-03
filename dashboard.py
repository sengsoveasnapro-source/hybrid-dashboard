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

# Custom Styles
st.markdown("""
    <style>
    .stApp { background-color: #060a0f; color: #E0E6ED; } 
    h1, h2, h3 { color: #00E5FF !important; font-weight: 900; text-shadow: 0px 0px 10px rgba(0, 229, 255, 0.4); } 
    div[data-testid="stMetricValue"] { color: #00FFA3 !important; font-size: 32px; font-weight: bold; text-shadow: 0px 0px 10px rgba(0, 255, 163, 0.4); } 
    div[data-testid="stMetricLabel"] { color: #FFAA00 !important; font-size: 14px; font-weight: bold; } 
    p, span, label, div { color: #E0E6ED; }
    .dataframe { border: 1px solid #1a2639; }
    .stAlert { background-color: #0A111E !important; border: 1px solid #00E5FF !important; }
    th:nth-child(3), td:nth-child(3) { text-align: center; }
    div.stButton > button { font-weight: bold; border-radius: 6px; }
    
    /* Card design for License Management */
    .license-card {
        background-color: #0b1118;
        border: 1px solid #1a2639;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ MASTER CONTROL CENTER")
st.write("---")

# ==========================================
# DATA LOADING
# ==========================================
try:
    res = supabase.table("user_licenses").select("*").execute()
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

# ==========================================
# CREATING TABS (បង្កើត TAB ថ្មី)
# ==========================================
tab_dashboard, tab_license_center = st.tabs(["📊 UNIFIED LIVE SYSTEMS", "🔑 LICENSE MANAGEMENT CENTER"])

# ==========================================
# 📊 TAB 1: UNIFIED LIVE SYSTEMS (ផ្ទាំងចាស់របស់បង)
# ==========================================
with tab_dashboard:
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
                name = row.get('owner_name', row.get('client_name', 'Auto Registered'))
                
                bal, eq, prof, status, last_sync = 0.0, 0.0, 0.0, "OFFLINE (គ្មានសេវា)", "-"
                total_pos, today_lots, total_lots_db = 0, 0.0, 0.0
                buy_count, buy_lots, sell_count, sell_lots = 0, 0.0, 0, 0.0
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
                        buy_count = safe_int(m_data.get('long_nodes'))
                        buy_lots = safe_float(m_data.get('long_lots'))
                        sell_count = safe_int(m_data.get('short_nodes'))
                        sell_lots = safe_float(m_data.get('short_lots'))
                        total_lots_db = safe_float(m_data.get('total_lots'))
                        
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
                clean_time = last_sync.split('.')[0].replace('T', ' ') if last_sync != '-' else '-'

                display_list.append({
                    "ID": acc, "Name": name, "Status": formatted_status,
                    "Balance": f"${bal:,.2f}", "Float P/L": f"${prof:,.2f}", "Active Nodes": total_pos,
                    "Today Lots": f"{today_lots:.2f}", "Total Lots": f"{total_lots_db:.2f}",
                    "T-1": f"{t1:.2f}", "T-2": f"{t2:.2f}", "T-3": f"{t3:.2f}", "T-4": f"{t4:.2f}",
                    "អាប់ដេត": clean_time
                })
                
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
                cmd_target = st.selectbox("🎯 ជ្រើសរើសលេខគណនី (Bot) គោលដៅ៖", active_df['account_number'], key="remote_acc_select")
            with rc_col2:
                st.write("⚡ **ផ្ទាំងបញ្ជាបន្ទាន់ (Action Panel):**")
                b1, b2, b3 = st.columns(3)
                if b1.button("⏸ ផ្អាក (Pause Trading)", use_container_width=True):
                    supabase.table("user_licenses").update({"bot_command": "PAUSE"}).eq("account_number", cmd_target).execute()
                    st.success(f"✅ បានបញ្ជូនបញ្ជា PAUSE ទៅគណនី {cmd_target}!")
                    time.sleep(0.5); st.rerun()
                if b2.button("▶️ បន្ត (Resume Trading)", use_container_width=True):
                    supabase.table("user_licenses").update({"bot_command": "NONE"}).eq("account_number", cmd_target).execute()
                    st.success(f"✅ បានបញ្ជូនបញ្ជា RESUME ទៅគណនី {cmd_target}!")
                    time.sleep(0.5); st.rerun()
                if b3.button("🛑 បិទអូឌ័រទាំងអស់ (Close All)", type="primary", use_container_width=True):
                    supabase.table("user_licenses").update({"bot_command": "CLOSE_ALL"}).eq("account_number", cmd_target).execute()
                    st.error(f"🚨 បានបញ្ជូនបញ្ជា CLOSE ALL ទៅគណនី {cmd_target}!")
                    time.sleep(0.5); st.rerun()
        else:
            st.info("មិនទាន់មានគណនីណាត្រូវបានអនុញ្ញាតនៅឡើយទេ។")
    else:
        st.info("ប្រព័ន្ធកំពុងរង់ចាំការតភ្ជាប់...")

# ==============================================================================
# 🔑 TAB 2: LICENSE MANAGEMENT CENTER (មជ្ឈមណ្ឌលគ្រប់គ្រងទិន្នន័យអាជ្ញាប័ណ្ណថ្មី)
# ==============================================================================
with tab_license_center:
    st.subheader("🔑 LICENSE & DATA ANALYTICS EMPIRE")
    st.write("---")
    
    # ------------------------------------------
    # 📈 ផ្នែកទី ១៖ PROFIT ANALYTICS & DRAWDOWN ALERTS
    # ------------------------------------------
    st.markdown("### 📈 Profit Analytics & Drawdown Shield")
    col_chart, col_alert = st.columns([2, 1])
    
    with col_chart:
        if not live_df.empty and 'profit' in live_df.columns and 'vps_name' in live_df.columns:
            # រៀបចំទិន្នន័យគណនីដែលចំណេញច្រើនជាងគេ
            analytics_df = live_df[['vps_name', 'balance', 'equity', 'profit']].copy()
            analytics_df['profit'] = analytics_df['profit'].apply(safe_float)
            analytics_df['balance'] = analytics_df['balance'].apply(safe_float)
            analytics_df['equity'] = analytics_df['equity'].apply(safe_float)
            
            top_earners = analytics_df.sort_values(by='profit', ascending=False).head(5)
            st.caption("🏆 គណនីកំពូលរកប្រាក់ចំណេញបានច្រើនជាងគេ (Top 5 Profit Leaders)")
            st.bar_chart(data=top_earners, x='vps_name', y='profit', use_container_width=True)
            
    with col_alert:
        st.caption("🚨 Drawdown Risk Alerts (Floating > 15%)")
        danger_found = False
        if not live_df.empty and 'balance' in live_df.columns:
            for _, b_row in analytics_df.iterrows():
                bal = b_row['balance']
                eq = b_row['equity']
                if bal > 0:
                    dd_pct = ((bal - eq) / bal) * 100
                    if dd_pct >= 15.0: # ប្រកាសអាសន្នបើ Drawdown ធំជាង 15%
                        st.error(f"⚠️ **Account ID: {b_row['vps_name']}**<br>Drawdown ខ្ពស់ខ្លាំង: **{dd_pct:.1f}%**", icon="🔥")
                        danger_found = True
        if not danger_found:
            st.success("✅ គ្រប់គណនីទាំងអស់មានសុវត្ថិភាពល្អ (No Drawdown Risk).")

    st.write("---")
    
    # ------------------------------------------
    # 🔍 ផ្នែកទី ២៖ QUICK SEARCH SYSTEM
    # ------------------------------------------
    st.markdown("### 🔍 Quick Search Customer Database")
    search_q = st.text_input(" Filter ស្វែងរកអតិថិជនភ្លាមៗ (វាយបញ្ចូលលេខ Account ID ឬ ឈ្មោះអតិថិជន):", placeholder="ស្វែងរកទីនេះ...")

    # ------------------------------------------
    # 📋 ផ្នែកទី ៣៖ LIVE TABLE & ONE-CLICK APPROVE/REVOKE & CLV
    # ------------------------------------------
    st.write("")
    if not licenses_df.empty:
        # តម្រងស្វែងរក (Search Filter)
        if search_q:
            filtered_licenses = licenses_df[
                licenses_df['account_number'].astype(str).str.contains(search_q) | 
                licenses_df['owner_name'].astype(str).sidebar.str.contains(search_q, case=False)
            ]
        else:
            filtered_licenses = licenses_df

        st.markdown(f"📊 លទ្ធផលរកឃើញ៖ **{len(filtered_licenses)} គណនី**")
        
        # បង្កើតផ្ទាំងកាតសម្រាប់គ្រប់គ្រងម្ដងមួយជួរ (Modern Rows Style)
        for idx, row in filtered_licenses.iterrows():
            acc_id = row.get('account_number', 'Unknown')
            owner = row.get('owner_name', 'Unknown User')
            hwid = row.get('hwid', 'No HWID Bound')
            is_active = row.get('is_active', False)
            exp_date = row.get('expiry_date', None)
            
            # 🚀 គណនា Customer Lifetime Value (CLV) - ចំនួនខែដែលគាត់បានបង់លុយរត់ Bot
            # សន្មតគណនាពីកាលបរិច្ឆេទថ្ងៃនេះ ទៅថ្ងៃផុតកំណត់ (ឬអាចបង្ហាញទិន្នន័យកិច្ចសន្យា)
            if exp_date:
                try:
                    expiry = datetime.strptime(str(exp_date), "%Y-%m-%d").date()
                    today = datetime.now().date()
                    remaining_days = (expiry - today).days
                    months_value = max(1, round(remaining_days / 30))
                    clv_badge = f"⏳ សល់សិទ្ធិ: **{remaining_days} ថ្ងៃ** (~ {months_value} ខែ)"
                except:
                    clv_badge = "⏱️ មិនទាន់កំណត់ថ្ងៃផុតកំណត់"
            else:
                clv_badge = "♾️ អាជ្ញាប័ណ្ណអចិន្ត្រៃយ៍ (Lifetime)"

            # បង្កើត Container បែប Card
            with st.container():
                st.markdown(f"""
                <div class="license-card">
                    <span style="font-size:18px; color:#00E5FF;">👤 <b>{owner}</b></span> | 🆔 Exness Account: <b>{acc_id}</b><br>
                    <span style="font-size:12px; color:#5a718c;">🖥️ Hardware ID (HWID): {hwid}</span><br>
                    💰 ស្ថានភាពទូទាត់សេវាកម្ម៖ {clv_badge}
                </div>
                """, unsafe_allow_html=True)
                
                # ប៊ូតុងបញ្ជា One-Click Approve / Revoke 
                c_status, c_action_approve, c_action_revoke = st.columns([2, 1, 1])
                
                if is_active:
                    c_status.markdown("🟢 **ស្ថានភាពបច្ចុប្បន្ន:** <span style='color:#00FFA3; font-weight:bold;'>ACTIVE (កំពុងរត់)</span>", unsafe_allow_html=True)
                else:
                    c_status.markdown("🟡 **ស្ថានភាពបច្ចុប្បន្ន:** <span style='color:#FFAA00; font-weight:bold;'>PENDING (រង់ចាំការអនុញ្ញាត)</span>", unsafe_allow_html=True)
                
                # ប៊ូតុង Approve
                if c_action_approve.button("✅ Approve / បើកសិទ្ធិ", key=f"btn_app_{acc_id}_{idx}", use_container_width=True, disabled=is_active):
                    supabase.table("user_licenses").update({"is_active": True}).eq("account_number", acc_id).execute()
                    st.success(f"បានបើកសិទ្ធិគណនី {acc_id} ជោគជ័យ!")
                    time.sleep(0.5); st.rerun()
                    
                # ប៊ូតុង Revoke
                if c_action_revoke.button("🚫 Revoke / បិទសិទ្ធិ", key=f"btn_rev_{acc_id}_{idx}", type="primary", use_container_width=True, disabled=not is_active):
                    supabase.table("user_licenses").update({"is_active": False}).eq("account_number", acc_id).execute()
                    st.error(f"បានផ្តាច់សិទ្ធិគណនី {acc_id} រួចរាល់!")
                    time.sleep(0.5); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("មិនទាន់មានទិន្នន័យអាជ្ញាប័ណ្ណនៅក្នុងតារាង `user_licenses` ទេ។")

# ==========================================
# 🔄 ផ្នែក REFRESH ខាងក្រោមគេបង្អស់
# ==========================================
st.write("---")
col_R1, col_R2, col_R3 = st.columns([1, 2, 1])
with col_R2:
    if st.button("🔄 REFRESH LIVE ARCHITECTURE", use_container_width=True):
        st.rerun()

st.caption("DEV CONTACT: 0967205522 | Hybrid Control Center v3.0 Pro")