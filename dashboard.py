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
    # 2. GLOBAL DATA FETCH 
    # ==========================================
    try:
        # Fetching all potential columns. If they don't exist yet, it will fail gracefully to the except block.
        perf_res = supabase.table("property_performance").select("*").eq("parent_company_id", comp_id).order("record_date", desc=True).execute()
        
        if perf_res.data:
            df_perf = pd.DataFrame(perf_res.data)
            total_coin_in = df_perf['coin_in'].sum()
            total_table_drop = df_perf['table_drop'].sum()
            total_marketing = df_perf['marketing_spend'].sum()
            has_data = True
        else:
            total_coin_in, total_table_drop, total_marketing = 0.0, 0.0, 0.0
            has_data = False
            df_perf = pd.DataFrame()
    except:
        total_coin_in, total_table_drop, total_marketing = 0.0, 0.0, 0.0
        has_data = False
        df_perf = pd.DataFrame()

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

    # --- TAB 1: MASTER OVERVIEW & INGESTION ---
    with tabs[0]:
        st.markdown("### Floor Performance Snapshot")
        st.caption("Aggregated predictive demand across all active departments.")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Gross Coin-In", f"${total_coin_in:,.0f}")
        
        if "Hotel Premium" in active_modules: c2.metric("Forecasted ADR", "$0.00", "Awaiting Pace Data")
        else: c2.metric("Forecasted ADR", "🔒 Locked", "Requires Hotel Module")
            
        if "F&B Premium" in active_modules: c3.metric("F&B Covers", "0", "Awaiting POS Data")
        else: c3.metric("F&B Covers", "🔒 Locked", "Requires F&B Module")
            
        c4.metric("Attributed Media Spend", f"${total_marketing:,.0f}")

        st.write("\n")

        # --- THE UNIVERSAL DATA INGESTION ENGINE ---
        with st.expander("📂 Property Ledger & Daily Data Ingestion", expanded=not has_data):
            tab_manual, tab_csv, tab_ledger = st.tabs(["✍️ Manual Daily Entry", "📥 Bulk CSV Upload", "📋 View Database"])
            
            # 1. MANUAL ENTRY FORM
            with tab_manual:
                st.markdown("##### Log Yesterday's Operations")
                with st.form("manual_entry_form"):
                    entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1))
                    
                    st.markdown("**🎰 Casino & Marketing** (Core)")
                    mc1, mc2, mc3 = st.columns(3)
                    m_coin = mc1.number_input("Coin-In ($)", min_value=0.0, step=1000.0)
                    m_table = mc2.number_input("Table Drop ($)", min_value=0.0, step=1000.0)
                    m_spend = mc3.number_input("Marketing Spend ($)", min_value=0.0, step=100.0)

                    # Dynamic fields based on subscriptions
                    m_rooms, m_adr, m_covers, m_fbrev, m_tix, m_entrev = 0, 0.0, 0, 0.0, 0, 0.0
                    
                    if "Hotel Premium" in active_modules:
                        st.divider()
                        st.markdown("**🏨 Hotel Operations**")
                        hc1, hc2 = st.columns(2)
                        m_rooms = hc1.number_input("Rooms Sold", min_value=0, step=1)
                        m_adr = hc2.number_input("Average Daily Rate (ADR $)", min_value=0.0, step=10.0)
                        
                    if "F&B Premium" in active_modules:
                        st.divider()
                        st.markdown("**🍔 Food & Beverage**")
                        fc1, fc2 = st.columns(2)
                        m_covers = fc1.number_input("Total Covers", min_value=0, step=1)
                        m_fbrev = fc2.number_input("Gross F&B Revenue ($)", min_value=0.0, step=500.0)

                    if "Entertainment Premium" in active_modules:
                        st.divider()
                        st.markdown("**🎫 Entertainment & Shows**")
                        ec1, ec2 = st.columns(2)
                        m_tix = ec1.number_input("Tickets Scanned", min_value=0, step=1)
                        m_entrev = ec2.number_input("Box Office Revenue ($)", min_value=0.0, step=500.0)

                    st.write("\n")
                    if st.form_submit_button("Save Daily Log to Ledger", type="primary", use_container_width=True):
                        try:
                            # Build the dynamic payload
                            payload = {
                                "parent_company_id": comp_id,
                                "record_date": str(entry_date),
                                "coin_in": m_coin,
                                "table_drop": m_table,
                                "marketing_spend": m_spend
                            }
                            if "Hotel Premium" in active_modules:
                                payload["rooms_sold"] = m_rooms
                                payload["adr"] = m_adr
                            if "F&B Premium" in active_modules:
                                payload["fb_covers"] = m_covers
                                payload["fb_revenue"] = m_fbrev
                            if "Entertainment Premium" in active_modules:
                                payload["tickets_sold"] = m_tix
                                payload["ent_revenue"] = m_entrev

                            supabase.table("property_performance").upsert([payload]).execute()
                            st.success(f"Data for {entry_date} securely logged.")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Save failed. Ensure database columns exist. Error: {e}")

            # 2. BULK CSV UPLOAD
            with tab_csv:
                st.markdown("##### 📥 Upload Historical Reports")
                st.caption("Accepted columns: `date`, `coin_in`, `table_drop`, `marketing_spend`, `rooms_sold`, `adr`, `fb_covers`, `fb_revenue`, `tickets_sold`, `ent_revenue`")
                with st.form("ledger_upload_form"):
                    dash_file = st.file_uploader("Drop CSV Here", type=["csv"], label_visibility="collapsed")
                    if st.form_submit_button("Process Bulk Data", use_container_width=True):
                        if dash_file:
                            try:
                                df_new = pd.read_csv(dash_file)
                                df_new.columns = df_new.columns.str.strip().str.lower().str.replace(' ', '_')
                                
                                # Clean currency formats
                                for col in df_new.columns:
                                    if col != 'date':
                                        df_new[col] = df_new[col].replace('[\$,]', '', regex=True).astype(float)

                                records = []
                                for _, row in df_new.iterrows():
                                    if 'date' in df_new.columns and pd.notna(row['date']):
                                        # Map columns dynamically if they exist in the CSV
                                        rec = {"parent_company_id": comp_id, "record_date": str(row['date'])}
                                        for c in ['coin_in', 'table_drop', 'marketing_spend', 'rooms_sold', 'adr', 'fb_covers', 'fb_revenue', 'tickets_sold', 'ent_revenue']:
                                            if c in df_new.columns:
                                                rec[c] = row[c]
                                        records.append(rec)

                                if records:
                                    supabase.table("property_performance").upsert(records).execute()
                                    st.success("Ledger Updated Successfully!")
                                    time.sleep(1.5)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error processing CSV: {e}")
                        else:
                            st.error("Please attach a CSV file first.")

            # 3. VIEW DATABASE
            with tab_ledger:
                if has_data:
                    st.dataframe(df_perf, use_container_width=True, hide_index=True)
                else:
                    st.info("No ledger data found.")

    # --- TAB 2: THE BRAINS (CORE AI & MARKETING) ---
    current_tab_index = 1
    if "Core AI & Marketing" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🧠 O2O Attribution & Adstock Engine")
            st.markdown("Calculate closed-loop ROI by correlating digital media decay with physical floor performance.")
            
            # 1. Operational Baselines
            st.markdown("#### Month-to-Date Reconciled Ledgers")
            bc1, bc2, bc3, bc4 = st.columns(4)
            
            bc1.metric("Gross Coin-In", f"${total_coin_in:,.0f}")
            bc2.metric("Table Drop", f"${total_table_drop:,.0f}")
            bc3.metric("Attributed Media Spend", f"${total_marketing:,.0f}")
            
            if total_marketing > 0:
                roas = (total_coin_in + total_table_drop) / total_marketing
                bc4.metric("O2O Blended ROAS", f"{roas:.1f}x")
            else:
                bc4.metric("O2O Blended ROAS", "0.0x", "Requires Media Spend")
            
            st.divider()

            # 2. Interactive Adstock Modeler
            st.markdown("#### Dynamic Media Mix Modeling")
            
            if not has_data:
                st.info("👋 Upload or enter your daily ledger on the Master Overview tab to activate the AI charting engine.")
            else:
                col_controls, col_chart = st.columns([1, 3])
                
                with col_controls:
                    st.markdown("##### Attribution Controls")
                    decay_rate = st.slider("Adstock Decay Rate (λ)", min_value=0.1, max_value=0.9, value=0.5, step=0.1)
                    spend_spike = st.number_input("Inject Ad Spend Spike ($)", min_value=0, max_value=50000, value=15000, step=1000)
                    spike_day = st.slider("Day of Campaign Launch", 1, 30, 5)
                
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
                    
                    base_traffic = np.random.normal(5000, 200, 30) 
                    correlated_traffic = base_traffic + (adstock * 0.15) 
                    
                    df_mmm = pd.DataFrame({
                        "Day": days,
                        "Raw Ad Spend": daily_spend,
                        "Effective Adstock Curve": adstock,
                        "Simulated Floor Traffic": correlated_traffic
                    }).set_index("Day")

                    st.markdown("##### Marketing Carryover vs. Floor Traffic")
                    st.line_chart(df_mmm[["Effective Adstock Curve", "Simulated Floor Traffic"]], height=350, use_container_width=True)

        current_tab_index += 1

    # --- OTHER TABS ---
    if "Hotel Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🏨 Hotel Revenue Engine")
            st.info("Pace models and occupancy physics initializing...")
        current_tab_index += 1

    if "F&B Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🍔 F&B Operational Engine")
            st.info("POS data integrations and cover forecasting initializing...")
        current_tab_index += 1

    if "Entertainment Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🎫 Entertainment Engine")
            st.info("Ticket velocity and crossover metrics initializing...")
        current_tab_index += 1

    # --- TAB: SETTINGS ---
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
