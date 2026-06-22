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
    # 2. TOP NAVIGATION BAR
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
    # 3. DYNAMIC TAB GENERATOR
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
        c1.metric("Predicted Floor Traffic", "12,450", "+4% vs Last Week")
        
        if "Hotel Premium" in active_modules: c2.metric("Forecasted ADR", "$214.50", "+$12.00")
        else: c2.metric("Forecasted ADR", "🔒 Locked", "Requires Hotel Module")
            
        if "F&B Premium" in active_modules: c3.metric("F&B Covers (Est)", "1,840", "-2%")
        else: c3.metric("F&B Covers", "🔒 Locked", "Requires F&B Module")
            
        c4.metric("Active Marketing Campaigns", "3", "ROI tracking live")

    # --- TAB 2: THE BRAINS (CORE AI & MARKETING) ---
    current_tab_index = 1
    if "Core AI & Marketing" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🧠 O2O Attribution & Adstock Engine")
            st.markdown("Calculate closed-loop ROI by correlating digital media decay with physical floor performance.")
            
            # 1. Operational Baselines
            st.markdown("#### Month-to-Date Reconciled Ledgers")
            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric("Gross Coin-In", "$185,040,398", "+2.4% MoM")
            bc2.metric("Table Drop", "$19,654,460", "+1.1% MoM")
            bc3.metric("Attributed Media Spend", "$124,500", "Meta + Search")
            bc4.metric("O2O Blended ROAS", "14.2x", "Highly Efficient")
            
            st.divider()

            # 2. Interactive Adstock Modeler
            st.markdown("#### Dynamic Media Mix Modeling")
            
            col_controls, col_chart = st.columns([1, 3])
            
            with col_controls:
                st.markdown("##### Attribution Controls")
                decay_rate = st.slider("Adstock Decay Rate (λ)", min_value=0.1, max_value=0.9, value=0.5, step=0.1, help="The percentage of ad impact that carries over to the next day.")
                spend_spike = st.number_input("Inject Ad Spend Spike ($)", min_value=0, max_value=50000, value=15000, step=1000)
                spike_day = st.slider("Day of Campaign Launch", 1, 30, 5)
            
            with col_chart:
                # Generate a 30-day baseline simulation
                days = np.arange(1, 31)
                daily_spend = np.zeros(30)
                daily_spend[spike_day-1] = spend_spike  # Inject the selected spend
                
                # Calculate Adstock (The mathematical carryover of the ad spend)
                adstock = np.zeros(30)
                for i in range(30):
                    if i == 0:
                        adstock[i] = daily_spend[i]
                    else:
                        adstock[i] = daily_spend[i] + (adstock[i-1] * decay_rate)
                
                # Simulate correlated floor traffic based on the Adstock momentum
                base_traffic = np.random.normal(5000, 200, 30) # Baseline casino traffic
                correlated_traffic = base_traffic + (adstock * 0.15) # Traffic bump from adstock
                
                # Build the DataFrame for charting
                df_mmm = pd.DataFrame({
                    "Day": days,
                    "Raw Ad Spend": daily_spend,
                    "Effective Adstock Curve": adstock,
                    "Physical Floor Traffic": correlated_traffic
                }).set_index("Day")

                st.markdown("##### Marketing Carryover vs. Floor Traffic")
                # Plotting the Adstock curve against the Traffic
                st.line_chart(df_mmm[["Effective Adstock Curve", "Physical Floor Traffic"]], height=350, use_container_width=True)
                
            st.caption("Visualizing the 'memory' of digital ad spend. As the effective Adstock curve decays, observe the delayed, correlated impact on physical footfall entering the property.")

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
