import streamlit as st
import pandas as pd
import numpy as np
import time
import uuid
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai
from database import supabase
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

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
        
        active_modules = [s['system_modules']['module_name'] for s in subs_res.data] if subs_res.data else []
        active_subs_details = [{"Module": s['system_modules']['module_name'], "Price": float(s['agreed_price']), "Frequency": s['billing_frequency']} for s in subs_res.data] if subs_res.data else []
                
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
            for col in ['coin_in', 'table_drop', 'marketing_spend', 'actual_traffic', 'ad_clicks', 'attendance']:
                if col in df_perf.columns: df_perf[col] = pd.to_numeric(df_perf[col], errors='coerce').fillna(0)
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
    with nav_c1: st.markdown(f"<h3 style='margin-top: 10px; color:#111827;'>🎰 FloorCast OS <span style='color: #6B7280; font-weight: 400; font-size: 1.2rem;'>| {comp_name}</span></h3>", unsafe_allow_html=True)
    with nav_c2: st.markdown(f"<p style='margin-top: 15px; color:#6B7280; font-size: 0.9rem; text-align: right;'>👤 {profile.get('first_name', '')} ({user_role})</p>", unsafe_allow_html=True)
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
        tab_titles.extend(["🎰 Casino", "📈 Marketing", "📋 Reports"])
    if "Brand & Sentiment Premium" in active_modules: tab_titles.append("📢 Brand & Sentiment")
    if "Hotel Premium" in active_modules: tab_titles.append("🏨 Hotel Engine")
    if "F&B Premium" in active_modules: tab_titles.append("🍔 F&B Engine")
    if "Entertainment Premium" in active_modules: tab_titles.append("🎫 Entertainment")
    tab_titles.append("⚙️ Settings")

    tabs = st.tabs(tab_titles)

    # --- TAB 1: MASTER OVERVIEW ---
    with tabs[0]:
        st.markdown("### Floor Performance Snapshot")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Gross Coin-In", f"${total_coin_in:,.0f}")
        c2.metric("Forecasted ADR", "$0.00", "Awaiting Pace Data") if "Hotel Premium" in active_modules else c2.metric("Forecasted ADR", "🔒 Locked", "Requires Hotel Module")
        c3.metric("F&B Covers", "0", "Awaiting POS Data") if "F&B Premium" in active_modules else c3.metric("F&B Covers", "🔒 Locked", "Requires F&B Module")
        c4.metric("Attributed Media Spend", f"${total_marketing:,.0f}")

    # --- THE CORE SUITE (CASINO / MARKETING / REPORTS) ---
    current_tab_index = 1
    if "Core AI & Marketing" in active_modules:
        
        # --- TAB 2: CASINO ---
        with tabs[current_tab_index]:
            st.markdown("### 🎰 Daily Casino Operations")
            
            with st.expander("✍️ Log Daily Casino Ledger", expanded=not has_data):
                with st.form("casino_entry_form"):
                    entry_date = st.date_input("Audit Date", value=date.today() - timedelta(days=1), key="d_cas")
                    
                    st.markdown("##### Financials & Floor Traffic")
                    f1, f2, f3, f4 = st.columns(4)
                    m_coin = f1.number_input("Coin-In ($)", min_value=0.0, step=1000.0)
                    m_table = f2.number_input("Table Drop ($)", min_value=0.0, step=1000.0)
                    m_traffic = f3.number_input("Actual Traffic", min_value=0, step=1)
                    m_members = f4.number_input("New Members", min_value=0, step=1)
                    
                    st.markdown("##### Environmental & Operational Context")
                    c1, c2, c3, c4 = st.columns(4)
                    m_promo = c1.text_input("Active Promotion (e.g. Car Giveaway)")
                    m_event = c2.number_input("Event Attendance", min_value=0, step=1)
                    m_rain = c3.number_input("Rain (mm)", min_value=0.0, step=1.0)
                    m_snow = c4.number_input("Snow (cm)", min_value=0.0, step=1.0)
                    
                    if st.form_submit_button("🚀 Commit to Ledger", type="primary", use_container_width=True):
                        save_daily_log(entry_date, {"coin_in": m_coin, "table_drop": m_table, "actual_traffic": m_traffic, "new_members": m_members, "attendance": m_event, "active_promo": m_promo.strip() if m_promo else None, "rain_mm": m_rain, "snow_cm": m_snow})

            # --- THE NEW FORENSIC LEDGER EDITOR ---
            with st.expander("📂 Historical Ledger Corrections", expanded=False):
                st.markdown("Edit recent entries directly in the table below. To delete a row, select it using the checkbox on the left and press `Delete` on your keyboard. Click Save to sync to the database.")
                
                if has_data and not df_perf.empty:
                    df_edit = df_perf.copy()
                    df_edit['record_date'] = pd.to_datetime(df_edit['record_date']).dt.date
                    edit_cols = ['id', 'record_date', 'coin_in', 'table_drop', 'actual_traffic', 'new_members', 'attendance', 'active_promo', 'rain_mm', 'snow_cm']
                    
                    for c in edit_cols:
                        if c not in df_edit.columns: df_edit[c] = None
                    
                    df_edit = df_edit[edit_cols].head(30) # Show last 30 records to keep UI fast
                    
                    with st.form("ledger_corrections_form", border=False):
                        edited_df = st.data_editor(
                            df_edit,
                            column_config={
                                "id": None, # Hide the UUID from the user
                                "record_date": st.column_config.DateColumn("Date", required=True),
                                "coin_in": st.column_config.NumberColumn("Coin-In ($)", step=100.0),
                                "table_drop": st.column_config.NumberColumn("Table Drop ($)", step=100.0),
                                "actual_traffic": st.column_config.NumberColumn("Traffic", step=1),
                                "new_members": st.column_config.NumberColumn("New Members", step=1),
                                "attendance": st.column_config.NumberColumn("Event Attendance", step=1),
                                "active_promo": st.column_config.TextColumn("Active Promo"),
                                "rain_mm": st.column_config.NumberColumn("Rain (mm)"),
                                "snow_cm": st.column_config.NumberColumn("Snow (cm)"),
                            },
                            num_rows="dynamic",
                            use_container_width=True,
                            hide_index=True,
                            key="interactive_ledger_editor"
                        )
                        
                        if st.form_submit_button("💾 Sync Corrections to Vault", type="primary", use_container_width=True):
                            try:
                                # 1. Detect Deletions
                                orig_ids = set(df_edit['id'].dropna())
                                new_ids = set(edited_df['id'].dropna())
                                deleted_ids = orig_ids - new_ids
                                
                                if deleted_ids:
                                    for d_id in deleted_ids:
                                        supabase.table("property_performance").delete().eq("id", d_id).execute()
                                
                                # 2. Handle Upserts (Edits & New Rows added via grid)
                                upsert_payload = []
                                for _, row in edited_df.iterrows():
                                    rec = {
                                        "parent_company_id": comp_id,
                                        "record_date": str(row['record_date']),
                                        "coin_in": row['coin_in'] if pd.notna(row['coin_in']) else 0,
                                        "table_drop": row['table_drop'] if pd.notna(row['table_drop']) else 0,
                                        "actual_traffic": row['actual_traffic'] if pd.notna(row['actual_traffic']) else 0,
                                        "new_members": row['new_members'] if pd.notna(row['new_members']) else 0,
                                        "attendance": row['attendance'] if pd.notna(row['attendance']) else 0,
                                        "active_promo": row['active_promo'] if pd.notna(row['active_promo']) else None,
                                        "rain_mm": row['rain_mm'] if pd.notna(row['rain_mm']) else 0,
                                        "snow_cm": row['snow_cm'] if pd.notna(row['snow_cm']) else 0
                                    }
                                    if pd.notna(row.get('id')): 
                                        rec['id'] = row['id']
                                    upsert_payload.append(rec)
                                    
                                if upsert_payload:
                                    supabase.table("property_performance").upsert(upsert_payload).execute()
                                    
                                st.success("✅ Ledger Corrections Synchronized.")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Sync failed: {e}")
                else:
                    st.info("No ledger data found to edit.")

            st.divider()
            st.markdown("#### 🔮 Predictive Scenario Simulator")
            st.caption("Forecast future floor traffic based on seasonal physics and weather friction.")
            with st.container(border=True):
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    sim_season = st.selectbox("Season", ["Winter", "Spring", "Summer", "Autumn", "Peak"])
                    sim_rain = st.slider("Rain (mm)", 0, 50, 0, key="sim_rn")
                with sc2:
                    sim_event = st.number_input("Event Attendance", value=0, step=500, key="sim_ev")
                    sim_snow = st.slider("Snow (cm)", 0, 30, 0, key="sim_sn")
                with sc3:
                    test_lift_pct = st.number_input("Apply Proven Exp Lift %", value=0.0, step=0.5)

                if st.button("🚀 Run Seasonal Projection", use_container_width=True):
                    seasonal_base = 1500 * {"Winter": 0.85, "Spring": 1.05, "Summer": 1.15, "Autumn": 1.20, "Peak": 1.35}.get(sim_season, 1.0)
                    gravity_lift = sim_event * 0.25
                    friction = (sim_rain * -12) + (sim_snow * -45)
                    test_impact = seasonal_base * (test_lift_pct / 100)
                    proj_guests = max(0, seasonal_base + gravity_lift + friction + test_impact)
                    
                    st.divider()
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Seasonal Base", f"{seasonal_base:,.0f}")
                    r2.metric("Gravity Lift & Friction", f"{(gravity_lift + friction):,.0f}")
                    r3.metric("AI Traffic Projection", f"{proj_guests:,.0f}", delta=f"{test_impact:+.0f} from Lift")

        current_tab_index += 1

        # --- TAB 3: MARKETING ---
        with tabs[current_tab_index]:
            st.markdown("### 📈 Marketing & Attribution Analytics")
            mkt_tabs = st.tabs(["💰 Monthly Spend & BL-ROAS", "📊 O2O Attribution Visuals", "🔬 Experiment Vault"])
            
            with mkt_tabs[0]:
                st.markdown("#### Monthly Ad Spend & ROI Calculator")
                st.caption("Calculate Brand Lift - Return on Ad Spend (BL-ROAS) based on your monthly digital deployments.")
                
                LTV_BENCHMARK = 1900.00
                
                with st.form("roas_monthly_form", border=True):
                    selected_month = st.date_input("Audit Fiscal Month", value=date.today().replace(day=1))
                    
                    ledger_traffic, ledger_signups, ledger_coin_in = 0, 0, 0.0
                    if not df_perf.empty:
                        df_perf['record_date'] = pd.to_datetime(df_perf['record_date'])
                        m_mask = (df_perf['record_date'].dt.month == selected_month.month) & (df_perf['record_date'].dt.year == selected_month.year)
                        selected_month_df = df_perf.loc[m_mask].copy()
                        if not selected_month_df.empty:
                            ledger_traffic = int(selected_month_df['actual_traffic'].sum()) if 'actual_traffic' in selected_month_df.columns else 0
                            ledger_signups = int(selected_month_df['new_members'].sum()) if 'new_members' in selected_month_df.columns else 0
                            ledger_coin_in = float(selected_month_df['coin_in'].sum()) if 'coin_in' in selected_month_df.columns else 0.0

                    st.markdown("##### 1. Investment & Traffic")
                    c1, c2, c3 = st.columns(3)
                    utm_s = c1.number_input("UTM Sessions", min_value=0, step=100)
                    org_s = c2.number_input("Organic Sessions", min_value=0, step=100)
                    ad_spend = c3.number_input("Total Ad Spend ($)", min_value=0.0, step=500.0)
                    
                    st.markdown("##### 2. Social Engagement")
                    s1, s2, s3 = st.columns(3)
                    likes = s1.number_input("Social Engagement", min_value=0, step=10)
                    shares = s2.number_input("Social Shares", min_value=0, step=5)
                    views = s3.number_input("Reach / Impressions", min_value=0, step=1000)

                    st.markdown("##### 3. Digital Signals & Geo")
                    g1, g2, g3 = st.columns(3)
                    time_site = g1.number_input("Time-on-Site Sessions", min_value=0, step=10)
                    cta_clicks = g2.number_input("Booking CTA Clicks", min_value=0, step=10)
                    geo_lift = g3.number_input("Incremental Geo Traffic", min_value=0, step=10)

                    st.divider()
                    st.markdown(f"""
                        <div style="background: rgba(0, 71, 171, 0.05); padding: 15px; border-radius: 8px; border: 1px solid rgba(0, 71, 171, 0.2); margin-bottom: 20px;">
                            <p style="margin:0; font-size: 0.8rem; color: #0047AB; font-weight: 700; text-transform: uppercase;">Linked Casino Ledger Sync</p>
                            <p style="margin:0; font-size: 0.95rem; color: #1e293b;">
                                Coin-In: <b>${ledger_coin_in:,.2f}</b> | Traffic: <b>{ledger_traffic:,}</b> | Signups: <b>{ledger_signups:,}</b>
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.form_submit_button("🚀 Generate BL-ROAS Audit", use_container_width=True):
                        brand_value = (utm_s * 1.5) + (org_s * 0.5) + (likes * 0.1) + (shares * 0.5) + (geo_lift * 2.0)
                        bl_roas = brand_value / ad_spend if ad_spend > 0 else 0.0
                        enhanced_rev = brand_value + ledger_coin_in + (ledger_signups * LTV_BENCHMARK)
                        
                        try:
                            supabase.table("monthly_roi").upsert({
                                "parent_company_id": comp_id,
                                "report_month": str(selected_month.replace(day=1)),
                                "utm_sessions": utm_s, "organic_sessions": org_s, "ad_spend": ad_spend,
                                "social_likes": likes, "social_shares": shares, "post_views": views,
                                "site_time_sessions": time_site, "booking_clicks": cta_clicks,
                                "geo_lift_traffic": geo_lift, "brand_value": brand_value, 
                                "calculated_bl_roas": bl_roas, "enhanced_revenue": enhanced_rev
                            }).execute()
                            st.success(f"Successfully vaulted BL-ROAS for {selected_month.strftime('%B %Y')}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving ROI data: {e}")

                try:
                    roi_res = supabase.table("monthly_roi").select("*").eq("parent_company_id", comp_id).order("report_month", desc=True).execute()
                    if roi_res.data:
                        df_roi = pd.DataFrame(roi_res.data)
                        curr_row = df_roi.iloc[0]
                        prop_potential = ledger_coin_in + (ledger_signups * LTV_BENCHMARK)
                        
                        report_text = f"""{pd.to_datetime(curr_row['report_month']).strftime('%B %Y')} ROAS Results | {comp_name}
--------------------------------------------------
BRAND HEALTH PERFORMANCE
BL-ROAS = {curr_row['calculated_bl_roas']:.2f}x
Measured Brand Value Generated: ${curr_row['brand_value']:,.2f}

ATTRIBUTED REVENUE IMPACT (ESTIMATED)
• 10% Attribution: ${(prop_potential * 0.1):,.0f}
• 20% Attribution: ${(prop_potential * 0.2):,.0f}
• 30% Attribution: ${(prop_potential * 0.3):,.0f}

ENHANCED TOTAL IMPACT: ${curr_row['enhanced_revenue']:,.0f}"""
                        
                        st.markdown("##### 📄 Executive Summary (SharePoint Ready)")
                        st.text_area("Audit Output Clip:", value=report_text, height=220)

                        st.markdown("##### 📜 Audit History")
                        st.dataframe(df_roi[['report_month', 'ad_spend', 'calculated_bl_roas', 'brand_value', 'enhanced_revenue']], use_container_width=True, hide_index=True)
                except Exception as e:
                    pass

            with mkt_tabs[1]:
                if has_data and not df_perf.empty:
                    w_col, s_col = st.columns([1.5, 1])
                    with w_col:
                        st.markdown("#### 🌊 Offline-to-Online Attribution")
                        total_guests = df_perf['actual_traffic'].sum() if 'actual_traffic' in df_perf.columns else 0
                        gravity_lift = (df_perf['attendance'].sum() * 0.25) if 'attendance' in df_perf.columns else 0
                        digital_lift = total_guests * 0.15 
                        organic_base = total_guests - digital_lift - gravity_lift
                        
                        fig_water = go.Figure(go.Waterfall(orientation="v", measure=["relative", "relative", "relative", "total"], x=["Organic", "Online Signal", "Gravity", "Total Traffic"], y=[organic_base, digital_lift, gravity_lift, total_guests], decreasing={"marker":{"color":"#EF4444"}}, increasing={"marker":{"color":"#2563EB"}}, totals={"marker":{"color":"#F59E0B"}}))
                        fig_water.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white")
                        st.plotly_chart(fig_water, use_container_width=True)
                    with s_col:
                        st.markdown("#### 📈 Adstock Retention Decay")
                        st.caption("Simulated decay visualizer for digital spend momentum.")
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Adstock_Decay_Curve.png/600px-Adstock_Decay_Curve.png", use_container_width=True)
                else:
                    st.info("Awaiting Casino Data to generate Attribution.")

            with mkt_tabs[2]:
                ev_res = supabase.table("experiment_registry").select("*").eq("parent_company_id", comp_id).execute()
                v_res, v_man = st.tabs(["📊 Results", "⚙️ Registry"])
                with v_man:
                    with st.form("new_experiment_form", clear_on_submit=True):
                        e1, e2 = st.columns(2)
                        n_name = e1.text_input("Experiment Name", placeholder="e.g. March Car Promo")
                        n_a, n_b = e2.text_input("Control Tag (Version A)", value="Control"), e2.text_input("Test Tag (Version B)", value="Test_V1")
                        if st.form_submit_button("🚀 Deploy to Registry") and n_name and n_a and n_b:
                            supabase.table("experiment_registry").insert({"parent_company_id": comp_id, "test_name": n_name, "version_a_tag": n_a.strip(), "version_b_tag": n_b.strip()}).execute()
                            st.rerun()
                with v_res:
                    if ev_res.data and has_data:
                        exp_dict = {e['test_name']: e for e in ev_res.data}
                        sel_exp = st.selectbox("Select Active Experiment:", list(exp_dict.keys()))
                        tag_a, tag_b = exp_dict[sel_exp]['version_a_tag'], exp_dict[sel_exp]['version_b_tag']
                        df_perf['experiment_tag'] = df_perf['experiment_tag'].astype(str).str.strip()
                        df_a, df_b = df_perf[df_perf['experiment_tag'] == tag_a], df_perf[df_perf['experiment_tag'] == tag_b]
                        
                        if not df_a.empty and not df_b.empty:
                            vol_a, vol_b = df_a['actual_traffic'].mean(), df_b['actual_traffic'].mean()
                            st.metric("Total Volume Lift", f"{((vol_b - vol_a) / vol_a) * 100 if vol_a > 0 else 0:+.1f}% vs Control", help=f"Average traffic: {tag_a} ({vol_a:.0f}) vs {tag_b} ({vol_b:.0f})")
                        else: st.warning(f"Data Missing: Ensure Casino ledger entries are tagged as '{tag_a}' or '{tag_b}'.")

        current_tab_index += 1

        # --- TAB 4: REPORTS ---
        with tabs[current_tab_index]:
            st.markdown("### 📋 Master Forensic Audit")
            st.caption("Generate an aggregated operational and marketing report for your board or executive team.")
            
            if not has_data or df_perf.empty:
                st.info("No ledger data found. Enter daily metrics in the Casino tab.")
            else:
                df_perf['record_date'] = pd.to_datetime(df_perf['record_date'])
                min_d, max_d = df_perf['record_date'].min().date(), df_perf['record_date'].max().date()
                
                col_d, col_b = st.columns([2, 1])
                audit_range = col_d.date_input("Audit Window:", value=(min_d, max_d))
                
                if isinstance(audit_range, tuple) and len(audit_range) == 2:
                    s_date, e_date = audit_range
                    mask = (df_perf['record_date'].dt.date >= s_date) & (df_perf['record_date'].dt.date <= e_date)
                    df_audit = df_perf.loc[mask].copy()
                    
                    if not df_audit.empty:
                        a_traf = df_audit['actual_traffic'].sum() if 'actual_traffic' in df_audit.columns else 0
                        a_rev = df_audit['coin_in'].sum() if 'coin_in' in df_audit.columns else 0
                        a_mem = df_audit['new_members'].sum() if 'new_members' in df_audit.columns else 0
                        
                        st.divider()
                        st.markdown(f"#### Audit Results: {s_date} to {e_date}")
                        k1, k2, k3 = st.columns(3)
                        k1.metric("Total Guest Traffic", f"{a_traf:,.0f}")
                        k2.metric("Gross Coin-In Revenue", f"${a_rev:,.0f}")
                        k3.metric("New Members Acquired", f"{a_mem:,.0f}")
                        
                        st.download_button("📥 Download Master Report (CSV)", data=df_audit.to_csv(index=False).encode('utf-8'), file_name=f"FloorCast_Audit_{s_date}.csv", use_container_width=True)
                    else:
                        st.warning("No data found in this date range.")
                        
        current_tab_index += 1

    # --- OTHER MODULES ---
    if "Brand & Sentiment Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 📢 Brand Integrity & Sentiment Vault")
            st.info("Brand tracking active.")
        current_tab_index += 1

    if "Hotel Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🏨 Hotel Revenue Engine")
            with st.form("hotel_entry_form"):
                entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_hot")
                hc1, hc2 = st.columns(2)
                m_rooms = hc1.number_input("Rooms Sold", min_value=0, step=1)
                m_adr = hc2.number_input("Average Daily Rate (ADR $)", min_value=0.0, step=10.0)
                if st.form_submit_button("Save Hotel Data", type="primary"): save_daily_log(entry_date, {"rooms_sold": m_rooms, "adr": m_adr})
        current_tab_index += 1

    if "F&B Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🍔 F&B Operational Engine")
            with st.form("fb_entry_form"):
                entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_fb")
                fc1, fc2 = st.columns(2)
                m_covers = fc1.number_input("Total Covers", min_value=0, step=1)
                m_fbrev = fc2.number_input("Gross F&B Revenue ($)", min_value=0.0, step=500.0)
                if st.form_submit_button("Save F&B Data", type="primary"): save_daily_log(entry_date, {"fb_covers": m_covers, "fb_revenue": m_fbrev})
        current_tab_index += 1

    if "Entertainment Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🎫 Entertainment Engine")
            with st.form("ent_entry_form"):
                entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_ent")
                ec1, ec2 = st.columns(2)
                m_tix = ec1.number_input("Tickets Scanned", min_value=0, step=1)
                m_entrev = ec2.number_input("Box Office Revenue ($)", min_value=0.0, step=500.0)
                if st.form_submit_button("Save Entertainment Data", type="primary"): save_daily_log(entry_date, {"tickets_sold": m_tix, "ent_revenue": m_entrev})
        current_tab_index += 1

    # --- TAB: SETTINGS ---
    with tabs[-1]:
        st.markdown("### ⚙️ Account Management & Settings")
        with st.expander("💳 Billing & Active Subscriptions", expanded=True):
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.markdown("##### Your Active Modules")
                if active_subs_details: st.dataframe(pd.DataFrame(active_subs_details), use_container_width=True, hide_index=True)
            with b_col2:
                st.markdown("##### Account Balance")
                st.markdown(f"<h3 style='margin:0; color:{'#EF4444' if comp_owed > 0 else '#10B981'};'>${comp_owed:,.2f}</h3>", unsafe_allow_html=True)
                if pending_invoices:
                    st.markdown("**Pending Invoices:**")
                    for inv in pending_invoices: st.markdown(f"- Due: **{inv['due_date']}** | Amount: **${inv['invoice_amount']:,.2f}**")
                else: st.success("All invoices are settled.")

        with st.expander("📂 Master Ledger Database & Bulk Upload"):
            t_data, t_csv = st.tabs(["📋 View Raw Database", "📥 Bulk CSV Upload"])
            with t_data:
                if has_data: st.dataframe(df_perf, use_container_width=True, hide_index=True)
                else: st.info("No ledger data found.")
            with t_csv:
                st.caption("Accepted columns: `date`, `coin_in`, `table_drop`, `marketing_spend`, `actual_traffic`, `new_members`, `attendance`, `ad_clicks`, `ad_impressions`, `active_promo`, `experiment_tag`, `rain_mm`, `snow_cm`, `rooms_sold`, `adr`, `fb_covers`, `fb_revenue`, `tickets_sold`, `ent_revenue`")
                with st.form("bulk_upload_form"):
                    dash_file = st.file_uploader("Drop Multi-Department CSV Here", type=["csv"], label_visibility="collapsed")
                    if st.form_submit_button("Process Bulk Data", use_container_width=True, type="primary") and dash_file:
                        try:
                            df_new = pd.read_csv(dash_file)
                            df_new.columns = df_new.columns.str.strip().str.lower().str.replace(' ', '_')
                            for col in df_new.columns:
                                if col not in ['date', 'active_promo', 'experiment_tag']: df_new[col] = df_new[col].replace('[\$,]', '', regex=True).astype(float)
                            records = [{"parent_company_id": comp_id, "record_date": str(row['date']), **{c: row[c] for c in ['coin_in', 'table_drop', 'marketing_spend', 'actual_traffic', 'new_members', 'attendance', 'ad_clicks', 'ad_impressions', 'active_promo', 'experiment_tag', 'rain_mm', 'snow_cm', 'rooms_sold', 'adr', 'fb_covers', 'fb_revenue', 'tickets_sold', 'ent_revenue'] if c in df_new.columns}} for _, row in df_new.iterrows() if 'date' in df_new.columns and pd.notna(row['date'])]
                            if records:
                                supabase.table("property_performance").upsert(records).execute()
                                st.success("Master Ledger Updated!"); time.sleep(1.5); st.rerun()
                        except Exception as e: st.error(f"Upload failed: {e}")

        missing_modules = [m for m in all_modules.keys() if m not in active_modules]
        if missing_modules:
            st.divider()
            st.markdown("#### 🚀 Upgrade Center")
            upsell_cols = st.columns(len(missing_modules) if len(missing_modules) < 4 else 3)
            for i, mod_name in enumerate(missing_modules):
                with upsell_cols[i % 3]:
                    st.markdown(f"<div style='background-color: #F8FAFC; padding: 1.5rem; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px;'><h5 style='margin-top: 0; color: #0F172A;'>🔒 {mod_name}</h5><p style='color: #64748B; font-size: 0.9rem;'>{all_modules[mod_name]['description']}</p></div>", unsafe_allow_html=True)
                    if st.button(f"Request Activation", key=f"req_{mod_name}", type="secondary", use_container_width=True):
                        supabase.table("module_requests").insert({"parent_company_id": comp_id, "module_name": mod_name, "requested_by": profile['email']}).execute()
                        st.success(f"Request sent! We will contact you regarding {mod_name}.")
