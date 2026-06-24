import streamlit as st
import pandas as pd
import numpy as np
import time
import plotly.graph_objects as go
import plotly.express as px
from database import supabase
from datetime import date, timedelta

def render():
    profile = st.session_state.user_profile
    user_role = profile.get('global_role', 'User')

    # ==========================================
    # 1. FETCH CLIENT CONTEXT & SUBSCRIPTIONS
    # ==========================================
    try:
        access_res = supabase.table("user_property_access").select("parent_company_id, parent_companies(company_name, total_owed)").eq("user_email", profile['email']).execute()
        if not access_res.data:
            st.error("No company link found. Contact Support.")
            return
        
        comp_id = access_res.data[0]['parent_company_id']
        comp_name = access_res.data[0]['parent_companies']['company_name']
        comp_owed = float(access_res.data[0]['parent_companies']['total_owed'] or 0.0)

        all_mods_res = supabase.table("system_modules").select("*").execute()
        all_modules = {m['module_name']: m for m in all_mods_res.data} if all_mods_res.data else {}

        subs_res = supabase.table("company_subscriptions").select("agreed_price, billing_frequency, system_modules(module_name)").eq("parent_company_id", comp_id).eq("status", "Active").execute()
        
        active_modules = []
        active_subs_details = []
        if subs_res.data:
            for s in subs_res.data:
                mod_name = s['system_modules']['module_name']
                active_modules.append(mod_name)
                active_subs_details.append({
                    "Module": mod_name,
                    "Price": float(s['agreed_price']),
                    "Frequency": s['billing_frequency']
                })
                
        inv_res = supabase.table("invoices").select("*").eq("parent_company_id", comp_id).eq("status", "Pending").execute()
        pending_invoices = inv_res.data if inv_res.data else []
        
    except Exception as e:
        st.error(f"Failed to load workspace data: {e}")
        return

    # ==========================================
    # 2. GLOBAL DATA FETCH
    # ==========================================
    try:
        perf_res = supabase.table("property_performance").select("*").eq("parent_company_id", comp_id).order("record_date", desc=True).execute()
        if perf_res.data:
            df_perf = pd.DataFrame(perf_res.data)
            # Safely cast columns to numeric to avoid string concatenation bugs
            for col in ['coin_in', 'table_drop', 'marketing_spend', 'actual_traffic', 'ad_clicks', 'attendance']:
                if col in df_perf.columns:
                    df_perf[col] = pd.to_numeric(df_perf[col], errors='coerce').fillna(0)
            
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
            st.error(f"Save failed: {e}")

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
    
    if "Core AI & Marketing" in active_modules: tab_titles.append("🧠 Core AI Model")
    if "Hotel Premium" in active_modules: tab_titles.append("🏨 Hotel Engine")
    if "F&B Premium" in active_modules: tab_titles.append("🍔 F&B Engine")
    if "Entertainment Premium" in active_modules: tab_titles.append("🎫 Entertainment")
    
    tab_titles.append("⚙️ Settings")

    tabs = st.tabs(tab_titles)

    # --- TAB 1: MASTER OVERVIEW ---
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

    # --- TAB 2: CORE AI & MARKETING (LEGACY PORT) ---
    current_tab_index = 1
    if "Core AI & Marketing" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🧠 FloorCast Core AI & Marketing")
            
            ai_tabs = st.tabs(["📊 Attribution & Adstock", "🔮 Scenario Simulator", "🔬 Experiment Vault"])
            
            # --- 2A: ATTRIBUTION & ADSTOCK ---
            with ai_tabs[0]:
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
                        
                        if st.form_submit_button("🚀 Commit to Forensic Vault", type="primary", use_container_width=True):
                            payload = {
                                "coin_in": m_coin, "table_drop": m_table, "marketing_spend": m_spend,
                                "actual_traffic": m_traffic, "new_members": m_members, "attendance": m_event,
                                "ad_clicks": m_clicks, "ad_impressions": m_imps, "active_promo": m_promo.strip() if m_promo else None,
                                "experiment_tag": m_tag.strip() if m_tag else None, "rain_mm": m_rain, "snow_cm": m_snow
                            }
                            save_daily_log(entry_date, payload)

                if has_data and not df_perf.empty:
                    st.divider()
                    st.markdown("#### 🌊 Offline-to-Online Attribution Contribution")
                    
                    # Synthesize Legacy Waterfall Data
                    total_guests = df_perf['actual_traffic'].sum() if 'actual_traffic' in df_perf.columns else 0
                    digital_clicks = df_perf['ad_clicks'].sum() if 'ad_clicks' in df_perf.columns else 0
                    event_attendance = df_perf['attendance'].sum() if 'attendance' in df_perf.columns else 0
                    
                    # Mocking the coefficient math for the visualizer until we build the calibration settings panel
                    digital_lift = digital_clicks * 0.05 
                    gravity_lift = event_attendance * 0.25
                    organic_base = total_guests - digital_lift - gravity_lift
                    if organic_base < 0: organic_base = total_guests * 0.6
                    
                    w_col, s_col = st.columns([1.5, 1])
                    with w_col:
                        fig_water = go.Figure(go.Waterfall(
                            orientation = "v",
                            measure = ["relative", "relative", "relative", "total"],
                            x = ["Organic (Base)", "Online Signal", "Event Gravity", "Total Floor Traffic"],
                            y = [organic_base, digital_lift, gravity_lift, total_guests],
                            decreasing = {"marker":{"color":"#EF4444"}},
                            increasing = {"marker":{"color":"#2563EB"}},
                            totals = {"marker":{"color":"#F59E0B"}}
                        ))
                        fig_water.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white")
                        st.plotly_chart(fig_water, use_container_width=True)
                        
                    with s_col:
                        st.markdown("##### Signal Correlation")
                        if digital_clicks > 0:
                            fig_corr = px.scatter(
                                df_perf, x='ad_clicks', y='actual_traffic', 
                                labels={'ad_clicks': 'Digital Signal (Clicks)', 'actual_traffic': 'Property Traffic'},
                                color_discrete_sequence=['#2563EB']
                            )
                            fig_corr.update_layout(height=300, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
                            st.plotly_chart(fig_corr, use_container_width=True)
                        else:
                            st.info("Awaiting Ad Clicks data to generate correlation.")

            # --- 2B: SCENARIO SIMULATOR ---
            with ai_tabs[1]:
                st.markdown("#### 🛠️ Configure Scenario Parameters")
                with st.container(border=True):
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    with sc1:
                        sim_date = st.date_input("Target Date", value=date.today() + timedelta(days=14))
                        sim_season = st.selectbox("Season", ["Winter (Jan-Feb)", "Spring (Mar-Jun)", "Summer (Jul-Aug)", "Autumn (Sep-Nov)", "Peak (Dec)"])
                    with sc2:
                        sim_event = st.number_input("Event Attendance", value=0, step=500, key="sim_ev")
                        sim_clicks = st.number_input("Planned Ad Clicks", value=1000, step=100, key="sim_cl")
                    with sc3:
                        sim_imps = st.number_input("Planned Impressions", value=50000, step=5000, key="sim_im")
                        sim_rain = st.slider("Rain (mm)", 0, 50, 0, key="sim_rn")
                    with sc4:
                        sim_snow = st.slider("Snow (cm)", 0, 30, 0, key="sim_sn")
                        test_lift_pct = st.number_input("Apply Proven Exp Lift %", value=0.0, step=0.5)

                    if st.button("🚀 Run Seasonal Projection", use_container_width=True):
                        # Legacy Math Port
                        lifetime_baseline = 1500 # Default
                        season_mult = {"Winter (Jan-Feb)": 0.85, "Spring (Mar-Jun)": 1.05, "Summer (Jul-Aug)": 1.15, "Autumn (Sep-Nov)": 1.20, "Peak (Dec)": 1.35}.get(sim_season, 1.0)
                        seasonal_base = lifetime_baseline * season_mult
                        
                        digital_lift = (sim_clicks * 0.05) + (sim_imps * 0.0002)
                        gravity_lift = sim_event * 0.25
                        friction = (sim_rain * -12) + (sim_snow * -45)
                        test_impact = seasonal_base * (test_lift_pct / 100)
                        
                        proj_guests = max(0, seasonal_base + digital_lift + gravity_lift + friction + test_impact)
                        proj_rev = proj_guests * 112.50 # Avg coin in
                        
                        st.divider()
                        r1, r2, r3, r4 = st.columns(4)
                        r1.metric("Seasonal Base", f"{seasonal_base:,.0f}")
                        r2.metric("Digital & Gravity Lift", f"{(digital_lift + gravity_lift):,.0f}")
                        r3.metric("AI Traffic Projection", f"{proj_guests:,.0f}", delta=f"{test_impact:+.0f} from Test" if test_impact != 0 else None)
                        r4.metric("Proj. Revenue", f"${proj_rev:,.0f}")

            # --- 2C: EXPERIMENT VAULT ---
            with ai_tabs[2]:
                ev_res = supabase.table("experiment_registry").select("*").eq("parent_company_id", comp_id).execute()
                
                v_res, v_man = st.tabs(["📊 Performance Results", "⚙️ Manage Registry"])
                with v_man:
                    st.markdown("##### 🏗️ Provision New Experiment")
                    with st.form("new_experiment_form", clear_on_submit=True):
                        e1, e2 = st.columns(2)
                        with e1:
                            n_name = st.text_input("Experiment Name", placeholder="e.g. March Car Promo")
                        with e2:
                            n_a = st.text_input("Control Tag (Version A)", value="Control")
                            n_b = st.text_input("Test Tag (Version B)", value="Test_V1")
                        
                        if st.form_submit_button("🚀 Deploy to Registry"):
                            if n_name and n_a and n_b:
                                supabase.table("experiment_registry").insert({
                                    "parent_company_id": comp_id, "test_name": n_name,
                                    "version_a_tag": n_a.strip(), "version_b_tag": n_b.strip()
                                }).execute()
                                st.success("Experiment live.")
                                st.rerun()
                                
                    if ev_res.data:
                        st.markdown("##### 📂 Active Registry")
                        for exp in ev_res.data:
                            c1, c2 = st.columns([4,1])
                            c1.write(f"🔬 **{exp['test_name']}** ({exp['version_a_tag']} vs {exp['version_b_tag']})")
                            if c2.button("Delete", key=f"d_{exp['id']}"):
                                supabase.table("experiment_registry").delete().eq("id", exp['id']).execute()
                                st.rerun()

                with v_res:
                    if ev_res.data and has_data:
                        exp_dict = {e['test_name']: e for e in ev_res.data}
                        sel_exp = st.selectbox("Select Active Experiment:", list(exp_dict.keys()))
                        active = exp_dict[sel_exp]
                        tag_a, tag_b = active['version_a_tag'], active['version_b_tag']
                        
                        df_perf['experiment_tag'] = df_perf['experiment_tag'].astype(str).str.strip()
                        df_a = df_perf[df_perf['experiment_tag'] == tag_a]
                        df_b = df_perf[df_perf['experiment_tag'] == tag_b]
                        
                        if not df_a.empty and not df_b.empty:
                            vol_a, vol_b = df_a['actual_traffic'].mean(), df_b['actual_traffic'].mean()
                            vol_lift = ((vol_b - vol_a) / vol_a) * 100 if vol_a > 0 else 0
                            
                            st.markdown(f"#### 🔎 Unified Audit: {tag_a} vs {tag_b}")
                            st.metric("Total Volume Lift", f"{vol_lift:+.1f}% vs Control", help=f"Average traffic: {tag_a} ({vol_a:.0f}) vs {tag_b} ({vol_b:.0f})")
                        else:
                            st.warning(f"Data Missing: Ensure ledger entries are explicitly tagged as '{tag_a}' or '{tag_b}'.")
                    else:
                        st.info("No experiments registered or ledger data is empty.")

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
        current_tab_index += 1

    # --- TAB 6: SETTINGS (The SaaS Portal) ---
    with tabs[-1]:
        st.markdown("### ⚙️ Account Management & Settings")
        
        with st.expander("💳 Billing & Active Subscriptions", expanded=True):
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.markdown("##### Your Active Modules")
                if active_subs_details:
                    st.dataframe(pd.DataFrame(active_subs_details), use_container_width=True, hide_index=True)
                else:
                    st.info("No premium modules active.")
            with b_col2:
                st.markdown("##### Account Balance")
                owed_color = "#EF4444" if comp_owed > 0 else "#10B981"
                st.markdown(f"<h3 style='margin:0; color:{owed_color};'>${comp_owed:,.2f}</h3>", unsafe_allow_html=True)
                
                if pending_invoices:
                    st.markdown("**Pending Invoices:**")
                    for inv in pending_invoices:
                        st.markdown(f"- Due: **{inv['due_date']}** | Amount: **${inv['invoice_amount']:,.2f}**")
                else:
                    st.success("All invoices are currently settled.")

        with st.expander("📂 Master Ledger Database & Bulk Upload"):
            t_data, t_csv = st.tabs(["📋 View Raw Database", "📥 Bulk CSV Upload"])
            with t_data:
                if has_data: st.dataframe(df_perf, use_container_width=True, hide_index=True)
                else: st.info("No ledger data found.")
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
                                    if col not in ['date', 'active_promo', 'experiment_tag']: df_new[col] = df_new[col].replace('[\$,]', '', regex=True).astype(float)
                                records = []
                                for _, row in df_new.iterrows():
                                    if 'date' in df_new.columns and pd.notna(row['date']):
                                        rec = {"parent_company_id": comp_id, "record_date": str(row['date'])}
                                        target_cols = ['coin_in', 'table_drop', 'marketing_spend', 'actual_traffic', 'new_members', 'attendance', 'ad_clicks', 'ad_impressions', 'active_promo', 'experiment_tag', 'rain_mm', 'snow_cm', 'rooms_sold', 'adr', 'fb_covers', 'fb_revenue', 'tickets_sold', 'ent_revenue']
                                        for c in target_cols:
                                            if c in df_new.columns: rec[c] = row[c]
                                        records.append(rec)
                                if records:
                                    supabase.table("property_performance").upsert(records).execute()
                                    st.success("Master Ledger Updated!")
                                    time.sleep(1.5)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Upload failed: {e}")

        missing_modules = [m for m in all_modules.keys() if m not in active_modules]
        if missing_modules:
            st.divider()
            st.markdown("#### 🚀 Upgrade Center")
            st.caption("Request activation for premium operational modules.")
            upsell_cols = st.columns(len(missing_modules) if len(missing_modules) < 4 else 3)
            for i, mod_name in enumerate(missing_modules):
                with upsell_cols[i % 3]:
                    st.markdown(f"""
                    <div style='background-color: #F8FAFC; padding: 1.5rem; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px;'>
                        <h5 style='margin-top: 0; color: #0F172A;'>🔒 {mod_name}</h5>
                        <p style='color: #64748B; font-size: 0.9rem;'>{all_modules[mod_name]['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Request Activation", key=f"req_{mod_name}", type="secondary", use_container_width=True):
                        try:
                            supabase.table("module_requests").insert({"parent_company_id": comp_id, "module_name": mod_name, "requested_by": profile['email']}).execute()
                            st.success(f"Request sent! We will contact you regarding {mod_name}.")
                        except Exception as e:
                            st.error(f"Request failed. Error: {e}")
