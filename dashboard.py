import streamlit as st
import pandas as pd
import numpy as np
import time
from database import supabase
from datetime import date, timedelta

def render():
    profile = st.session_state.user_profile
    user_role = profile.get('global_role', 'User')

    # ==========================================
    # 1. FETCH CLIENT CONTEXT & SUBSCRIPTIONS
    # ==========================================
    try:
        access_res = supabase.table("user_property_access").select("parent_company_id, parent_companies(company_name)").eq("user_email", profile['email']).execute()
        if not access_res.data:
            st.error("No company link found. Contact Support.")
            return
        
        comp_id = access_res.data[0]['parent_company_id']
        comp_name = access_res.data[0]['parent_companies']['company_name']

        all_mods_res = supabase.table("system_modules").select("*").execute()
        all_modules = {m['module_name']: m for m in all_mods_res.data} if all_mods_res.data else {}

        subs_res = supabase.table("company_subscriptions").select("system_modules(module_name)").eq("parent_company_id", comp_id).eq("status", "Active").execute()
        active_modules = [s['system_modules']['module_name'] for s in subs_res.data] if subs_res.data else []
        
    except Exception as e:
        st.error(f"Failed to load workspace data: {e}")
        return

    # ==========================================
    # 2. GLOBAL DATA FETCH & HELPER FUNCTION
    # ==========================================
    try:
        perf_res = supabase.table("property_performance").select("*").eq("parent_company_id", comp_id).order("record_date", desc=True).execute()
        if perf_res.data:
            df_perf = pd.DataFrame(perf_res.data)
            total_coin_in = df_perf['coin_in'].sum() if 'coin_in' in df_perf.columns else 0.0
            total_table_drop = df_perf['table_drop'].sum() if 'table_drop' in df_perf.columns else 0.0
            total_marketing = df_perf['marketing_spend'].sum() if 'marketing_spend' in df_perf.columns else 0.0
            has_data = True
        else:
            total_coin_in, total_table_drop, total_marketing = 0.0, 0.0, 0.0
            has_data = False
            df_perf = pd.DataFrame()
    except Exception:
        total_coin_in, total_table_drop, total_marketing = 0.0, 0.0, 0.0
        has_data = False
        df_perf = pd.DataFrame()

    # SMART UPSERT FUNCTION
    def save_daily_log(entry_date, payload):
        try:
            existing = supabase.table("property_performance").select("id").eq("parent_company_id", comp_id).eq("record_date", str(entry_date)).execute()
            if existing.data:
                supabase.table("property_performance").update(payload).eq("id", existing.data[0]['id']).execute()
            else:
                payload["parent_company_id"] = comp_id
                payload["record_date"] = str(entry_date)
                supabase.table("property_performance").insert(payload).execute()
            st.success(f"Ledger for {entry_date} securely updated.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error(f"Save failed. Ensure database columns exist. Error: {e}")

    # ==========================================
    # 3. TOP NAVIGATION BAR
    # ==========================================
    nav_c1, nav_c2, nav_c3 = st.columns([6, 2, 1])
    with nav_c1: 
        st.markdown(f"<h3 style='margin-top: 10px; color:#111827;'>🎰 FloorCast OS <span style='color: #6B7280; font-weight: 400; font-size: 1.2rem;'>| {comp_name}</span></h3>", unsafe_allow_html=True)
    with nav_c2: 
        st.markdown(f"<p style='margin-top: 15px; color:#6B7280; font-size: 0.9rem; text-align: right;'>👤 {profile.get('first_name', '')} ({user_role})</p>", unsafe_allow_html=True)
    with nav_c3:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ==========================================
    # 4. DYNAMIC TAB GENERATOR
    # ==========================================
    tab_titles = ["📊 Master Overview"]
    
    if "Core AI & Marketing" in active_modules: 
        tab_titles.append("🧠 Core AI Model")
    if "Hotel Premium" in active_modules: 
        tab_titles.append("🏨 Hotel Engine")
    if "F&B Premium" in active_modules: 
        tab_titles.append("🍔 F&B Engine")
    if "Entertainment Premium" in active_modules: 
        tab_titles.append("🎫 Entertainment")
    
    tab_titles.append("⚙️ Settings")

    tabs = st.tabs(tab_titles)

    # --- TAB 1: MASTER OVERVIEW & BULK UPLOAD ---
    with tabs[0]:
        st.markdown("### Floor Performance Snapshot")
        st.caption("Aggregated predictive demand across all active departments.")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Gross Coin-In", f"${total_coin_in:,.0f}")
        
        if "Hotel Premium" in active_modules: 
            c2.metric("Forecasted ADR", "$0.00", "Awaiting Pace Data")
        else: 
            c2.metric("Forecasted ADR", "🔒 Locked", "Requires Hotel Module")
            
        if "F&B Premium" in active_modules: 
            c3.metric("F&B Covers", "0", "Awaiting POS Data")
        else: 
            c3.metric("F&B Covers", "🔒 Locked", "Requires F&B Module")
            
        c4.metric("Attributed Media Spend", f"${total_marketing:,.0f}")

        st.write("\n")
        
        with st.expander("📂 Master Ledger Database & Bulk Upload"):
            t_data, t_csv = st.tabs(["📋 View Raw Database", "📥 Bulk CSV Upload"])
            
            with t_data:
                if has_data: 
                    st.dataframe(df_perf, use_container_width=True, hide_index=True)
                else: 
                    st.info("No ledger data found.")
                    
            with t_csv:
                st.caption("Accepted columns: `date`, `coin_in`, `table_drop`, `marketing_spend`, `actual_traffic`, `new_members`, `attendance`, `ad_clicks`, `ad_impressions`, `active_promo`, `experiment_tag`, `rain_mm`, `snow_cm`, `rooms_sold`, `adr`, `fb_covers`, `fb_revenue`, `tickets_sold`, `ent_revenue`")
                with st.form("bulk_upload_form"):
                    dash_file = st.file_uploader("Drop Multi-Department CSV Here", type=["csv"], label_visibility="collapsed")
                    if st.form_submit_button("Process Bulk Data", use_container_width=True, type="primary"):
                        if dash_file:
                            try:
                                df_new = pd.read_csv(dash_file)
                                df_new.columns = df_new.columns.str.strip().str.lower().str.replace(' ', '_')
                                
                                for col in df_new.columns:
                                    if col not in ['date', 'active_promo', 'experiment_tag']: 
                                        df_new[col] = df_new[col].replace('[\$,]', '', regex=True).astype(float)
                                        
                                records = []
                                for _, row in df_new.iterrows():
                                    if 'date' in df_new.columns and pd.notna(row['date']):
                                        rec = {"parent_company_id": comp_id, "record_date": str(row['date'])}
                                        target_cols = [
                                            'coin_in', 'table_drop', 'marketing_spend', 'actual_traffic', 'new_members', 
                                            'attendance', 'ad_clicks', 'ad_impressions', 'active_promo', 'experiment_tag', 
                                            'rain_mm', 'snow_cm', 'rooms_sold', 'adr', 'fb_covers', 'fb_revenue', 'tickets_sold', 'ent_revenue'
                                        ]
                                        for c in target_cols:
                                            if c in df_new.columns: 
                                                rec[c] = row[c]
                                        records.append(rec)
                                        
                                if records:
                                    supabase.table("property_performance").upsert(records).execute()
                                    st.success("Master Ledger Updated!")
                                    time.sleep(1.5)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Upload failed: {e}")

    # --- TAB 2: CORE AI & MARKETING ---
    current_tab_index = 1
    if "Core AI & Marketing" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🧠 O2O Attribution & Adstock Engine")
            
            with st.expander("✍️ Log Daily Casino & Marketing Ledger", expanded=not has_data):
                with st.form("casino_entry_form"):
                    entry_date = st.date_input("Audit Date", value=date.today() - timedelta(days=1), key="d_cas")
                    
                    st.markdown("##### Financials & Floor Traffic")
                    f1, f2, f3, f4 = st.columns(4)
                    m_coin = f1.number_input("Coin-In ($)", min_value=0.0, step=1000.0)
                    m_table = f2.number_input("Table Drop ($)", min_value=0.0, step=1000.0)
                    m_traffic = f3.number_input("Actual Traffic", min_value=0, step=1)
                    m_members = f4.number_input("New Members", min_value=0, step=1)
                    
                    st.markdown("##### Digital Signal & Marketing")
                    d1, d2, d3, d4 = st.columns(4)
                    m_spend = d1.number_input("Marketing Spend ($)", min_value=0.0, step=100.0)
                    m_clicks = d2.number_input("Ad Clicks", min_value=0, step=1)
                    m_imps = d3.number_input("Social Impressions", min_value=0, step=1)
                    m_event = d4.number_input("Event Attendance", min_value=0, step=1)
                    
                    st.markdown("##### Environmental Context & Experiments")
                    c1, c2, c3, c4 = st.columns(4)
                    m_promo = c1.text_input("Active Promotion", placeholder="e.g. Unity Bonus")
                    m_tag = c2.text_input("Experiment Tag", placeholder="e.g. Control")
                    m_rain = c3.number_input("Rain (mm)", min_value=0.0, step=1.0)
                    m_snow = c4.number_input("Snow (cm)", min_value=0.0, step=1.0)
                    
                    st.write("\n")
                    if st.form_submit_button("🚀 Commit to Forensic Vault", type="primary", use_container_width=True):
                        payload = {
                            "coin_in": m_coin,
                            "table_drop": m_table,
                            "marketing_spend": m_spend,
                            "actual_traffic": m_traffic,
                            "new_members": m_members,
                            "attendance": m_event,
                            "ad_clicks": m_clicks,
                            "ad_impressions": m_imps,
                            "active_promo": m_promo.strip() if m_promo else None,
                            "experiment_tag": m_tag.strip() if m_tag else None,
                            "rain_mm": m_rain,
                            "snow_cm": m_snow
                        }
                        save_daily_log(entry_date, payload)

            st.divider()
            
            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric("Gross Coin-In", f"${total_coin_in:,.0f}")
            bc2.metric("Table Drop", f"${total_table_drop:,.0f}")
            bc3.metric("Attributed Media Spend", f"${total_marketing:,.0f}")
            
            if total_marketing > 0:
                roas = (total_coin_in + total_table_drop) / total_marketing
                bc4.metric("O2O Blended ROAS", f"{roas:.1f}x")
            else:
                bc4.metric("O2O Blended ROAS", "0.0x", "Requires Spend")
            
            st.divider()

            st.markdown("#### Dynamic Media Mix Modeling")
            if not has_data:
                st.info("👋 Log your daily casino ledger above to activate the AI charting engine.")
            else:
                col_controls, col_chart = st.columns([1, 3])
                with col_controls:
                    decay_rate = st.slider("Adstock Decay Rate (λ)", 0.1, 0.9, 0.5, 0.1)
                    spend_spike = st.number_input("Inject Spend Spike ($)", 0, 50000, 15000, 1000)
                    spike_day = st.slider("Day of Launch", 1, 30, 5)
                    
                with col_chart:
                    days = np.arange(1, 31)
                    daily_spend = np.zeros(30)
                    daily_spend[spike_day-1] = spend_spike
                    
                    adstock = np.zeros(30)
                    for i in range(30):
                        if i == 0:
                            adstock[i] = daily_spend[i]
                        else:
                            adstock[i] = daily_spend[i] + (adstock[i-1] * decay_rate)
                            
                    correlated_traffic = np.random.normal(5000, 200, 30) + (adstock * 0.15) 
                    df_mmm = pd.DataFrame({
                        "Day": days, 
                        "Effective Adstock": adstock, 
                        "Simulated Traffic": correlated_traffic
                    }).set_index("Day")
                    
                    st.line_chart(df_mmm[["Effective Adstock", "Simulated Traffic"]], height=350, use_container_width=True)

        current_tab_index += 1

    # --- TAB 3: HOTEL ENGINE ---
    if "Hotel Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🏨 Hotel Revenue Engine")
            
            with st.expander("✍️ Log Daily Hotel Ledger", expanded=True):
                with st.form("hotel_entry_form"):
                    entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_hot")
                    hc1, hc2 = st.columns(2)
                    m_rooms = hc1.number_input("Rooms Sold", min_value=0, step=1)
                    m_adr = hc2.number_input("Average Daily Rate (ADR $)", min_value=0.0, step=10.0)
                    if st.form_submit_button("Save Hotel Data", type="primary"):
                        save_daily_log(entry_date, {"rooms_sold": m_rooms, "adr": m_adr})
            
            st.info("Pace models and occupancy physics visualizing...")
        current_tab_index += 1

    # --- TAB 4: F&B ENGINE ---
    if "F&B Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🍔 F&B Operational Engine")
            
            with st.expander("✍️ Log Daily F&B Ledger", expanded=True):
                with st.form("fb_entry_form"):
                    entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_fb")
                    fc1, fc2 = st.columns(2)
                    m_covers = fc1.number_input("Total Covers", min_value=0, step=1)
                    m_fbrev = fc2.number_input("Gross F&B Revenue ($)", min_value=0.0, step=500.0)
                    if st.form_submit_button("Save F&B Data", type="primary"):
                        save_daily_log(entry_date, {"fb_covers": m_covers, "fb_revenue": m_fbrev})

            st.info("POS data integrations and cover forecasting visualizing...")
        current_tab_index += 1

    # --- TAB 5: ENTERTAINMENT ENGINE ---
    if "Entertainment Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🎫 Entertainment Engine")
            
            with st.expander("✍️ Log Daily Entertainment Ledger", expanded=True):
                with st.form("ent_entry_form"):
                    entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_ent")
                    ec1, ec2 = st.columns(2)
                    m_tix = ec1.number_input("Tickets Scanned", min_value=0, step=1)
                    m_entrev = ec2.number_input("Box Office Revenue ($)", min_value=0.0, step=500.0)
                    if st.form_submit_button("Save Entertainment Data", type="primary"):
                        save_daily_log(entry_date, {"tickets_sold": m_tix, "ent_revenue": m_entrev})

            st.info("Ticket velocity and crossover metrics visualizing...")
        current_tab_index += 1

    # --- TAB 6: SETTINGS ---
    with tabs[-1]:
        st.markdown("### Property Settings")
        missing_modules = [m for m in all_modules.keys() if m not in active_modules]
        if missing_modules:
            st.divider()
            st.markdown("#### 🚀 Unlock More Power")
            upsell_cols = st.columns(len(missing_modules) if len(missing_modules) < 4 else 3)
            for i, mod_name in enumerate(missing_modules):
                with upsell_cols[i % 3]:
                    st.markdown(f"""
                    <div style='background-color: #F3F4F6; padding: 1.5rem; border-radius: 8px; border: 1px dashed #D1D5DB;'>
                        <h5 style='margin-top: 0;'>🔒 {mod_name}</h5>
                        <p style='color: #6B7280; font-size: 0.9rem;'>{all_modules[mod_name]['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
