import streamlit as st
import pandas as pd
import numpy as np
from database import supabase

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
    # We fetch the data up here so ALL tabs can use it
    try:
        perf_res = supabase.table("property_performance").select("coin_in, table_drop, marketing_spend").eq("parent_company_id", comp_id).execute()
        
        if perf_res.data:
            df_perf = pd.DataFrame(perf_res.data)
            total_coin_in = df_perf['coin_in'].sum()
            total_table_drop = df_perf['table_drop'].sum()
            total_marketing = df_perf['marketing_spend'].sum()
            has_data = True
        else:
            total_coin_in = 0.0
            total_table_drop = 0.0
            total_marketing = 0.0
            has_data = False
    except:
        total_coin_in = 0.0
        total_table_drop = 0.0
        total_marketing = 0.0
        has_data = False

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
        st.caption("Aggregated predictive demand across all departments.")
        
        c1, c2, c3, c4 = st.columns(4)
        
        # Cleaned up placeholders - now shows 0 if no data
        c1.metric("Current Gross Coin-In", f"${total_coin_in:,.0f}")
        
        if "Hotel Premium" in active_modules: c2.metric("Forecasted ADR", "$0.00", "Awaiting Hotel Data")
        else: c2.metric("Forecasted ADR", "🔒 Locked", "Requires Hotel Module")
            
        if "F&B Premium" in active_modules: c3.metric("F&B Covers", "0", "Awaiting POS Data")
        else: c3.metric("F&B Covers", "🔒 Locked", "Requires F&B Module")
            
        c4.metric("Attributed Media Spend", f"${total_marketing:,.0f}")

    # --- TAB 2: THE BRAINS (CORE AI & MARKETING) ---
    current_tab_index = 1
    if "Core AI & Marketing" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🧠 O2O Attribution & Adstock Engine")
            st.markdown("Calculate closed-loop ROI by correlating digital media decay with physical floor performance.")
            
            # 1. Operational Baselines (Now 100% Honest)
            st.markdown("#### Month-to-Date Reconciled Ledgers")
            bc1, bc2, bc3, bc4 = st.columns(4)
            
            bc1.metric("Gross Coin-In", f"${total_coin_in:,.0f}")
            bc2.metric("Table Drop", f"${total_table_drop:,.0f}")
            bc3.metric("Attributed Media Spend", f"${total_marketing:,.0f}")
            
            # Prevent division by zero for ROAS
            if total_marketing > 0:
                roas = (total_coin_in + total_table_drop) / total_marketing
                bc4.metric("O2O Blended ROAS", f"{roas:.1f}x")
            else:
                bc4.metric("O2O Blended ROAS", "0.0x", "Requires Media Spend")
            
            st.divider()

            # 2. Interactive Adstock Modeler
            st.markdown("#### Dynamic Media Mix Modeling")
            
            if not has_data:
                st.info("👋 Upload your daily ledger in the Settings tab to activate the AI charting engine.")
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
                    
                    # Still using simulated traffic for the visualizer until we build the correlation math
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
