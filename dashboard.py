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
    # 2. GLOBAL DATA FETCH & HELPER FUNCTIONS
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

    # LEGACY GEMINI SENTIMENT SCORER
    def archive_sentiment_entry(text, asset_tag, review_date):
        try:
            genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", ""))
            model = genai.GenerativeModel('gemini-2.5-flash') 
            score_prompt = f"Analyze sentiment. Return ONLY a single float between -1.0 and 1.0: {text}"
            ai_res = model.generate_content(score_prompt)
            try: sentiment_score = float(ai_res.text.strip())
            except: sentiment_score = 0.0

            sentiment_category = "Positive" if sentiment_score > 0.3 else "Negative" if sentiment_score < -0.3 else "Neutral"
            abs_score = abs(sentiment_score)
            intensity_level = "Extreme" if abs_score >= 0.8 else "Moderate" if abs_score >= 0.4 else "Low"

            payload = {
                "message_id": str(uuid.uuid4()),
                "parent_company_id": comp_id,
                "asset": asset_tag,
                "sentiment_score": sentiment_score,
                "sentiment_category": sentiment_category,
                "intensity_level": intensity_level,
                "raw_text": text,
                "timestamp": review_date.strftime("%Y-%m-%dT12:00:00")
            }
            supabase.table("sentiment_history").insert(payload).execute()
            return True
        except Exception as e:
            st.error(f"Archival Sync Error: {e}. Check Gemini API Key.")
            return False

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
    if "Core AI & Marketing" in active_modules: tab_titles.append("🧠 Core AI Model")
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

    # --- TAB 2: CORE AI & MARKETING ---
    current_tab_index = 1
    if "Core AI & Marketing" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🧠 FloorCast Core AI & Marketing")
            ai_tabs = st.tabs(["📊 Attribution & Adstock", "🔮 Scenario Simulator", "🔬 Experiment Vault"])
            
            with ai_tabs[0]:
                with st.expander("✍️ Log Daily Casino & Marketing Ledger", expanded=not has_data):
                    with st.form("casino_entry_form"):
                        entry_date = st.date_input("Audit Date", value=date.today() - timedelta(days=1), key="d_cas")
                        st.markdown("##### Financials & Floor Traffic")
                        f1, f2, f3, f4 = st.columns(4)
                        m_coin, m_table, m_traffic, m_members = f1.number_input("Coin-In ($)", min_value=0.0, step=1000.0), f2.number_input("Table Drop ($)", min_value=0.0, step=1000.0), f3.number_input("Actual Traffic", min_value=0, step=1), f4.number_input("New Members", min_value=0, step=1)
                        st.markdown("##### Digital Signal & Marketing")
                        d1, d2, d3, d4 = st.columns(4)
                        m_spend, m_clicks, m_imps, m_event = d1.number_input("Marketing Spend ($)", min_value=0.0, step=100.0), d2.number_input("Ad Clicks", min_value=0, step=1), d3.number_input("Social Impressions", min_value=0, step=1), d4.number_input("Event Attendance", min_value=0, step=1)
                        st.markdown("##### Environmental Context & Experiments")
                        c1, c2, c3, c4 = st.columns(4)
                        m_promo, m_tag, m_rain, m_snow = c1.text_input("Active Promotion"), c2.text_input("Experiment Tag"), c3.number_input("Rain (mm)", step=1.0), c4.number_input("Snow (cm)", step=1.0)
                        if st.form_submit_button("🚀 Commit to Forensic Vault", type="primary", use_container_width=True):
                            save_daily_log(entry_date, {"coin_in": m_coin, "table_drop": m_table, "marketing_spend": m_spend, "actual_traffic": m_traffic, "new_members": m_members, "attendance": m_event, "ad_clicks": m_clicks, "ad_impressions": m_imps, "active_promo": m_promo.strip() if m_promo else None, "experiment_tag": m_tag.strip() if m_tag else None, "rain_mm": m_rain, "snow_cm": m_snow})

                if has_data and not df_perf.empty:
                    st.divider()
                    w_col, s_col = st.columns([1.5, 1])
                    with w_col:
                        st.markdown("#### 🌊 Offline-to-Online Attribution")
                        total_guests = df_perf['actual_traffic'].sum() if 'actual_traffic' in df_perf.columns else 0
                        digital_lift = (df_perf['ad_clicks'].sum() * 0.05) if 'ad_clicks' in df_perf.columns else 0 
                        gravity_lift = (df_perf['attendance'].sum() * 0.25) if 'attendance' in df_perf.columns else 0
                        organic_base = total_guests - digital_lift - gravity_lift
                        if organic_base < 0: organic_base = total_guests * 0.6
                        
                        fig_water = go.Figure(go.Waterfall(orientation="v", measure=["relative", "relative", "relative", "total"], x=["Organic", "Online Signal", "Gravity", "Total Traffic"], y=[organic_base, digital_lift, gravity_lift, total_guests], decreasing={"marker":{"color":"#EF4444"}}, increasing={"marker":{"color":"#2563EB"}}, totals={"marker":{"color":"#F59E0B"}}))
                        fig_water.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white")
                        st.plotly_chart(fig_water, use_container_width=True)
                    with s_col:
                        st.markdown("#### 📈 Signal Correlation")
                        if 'ad_clicks' in df_perf.columns and df_perf['ad_clicks'].sum() > 0:
                            fig_corr = px.scatter(df_perf, x='ad_clicks', y='actual_traffic', labels={'ad_clicks': 'Clicks', 'actual_traffic': 'Traffic'}, color_discrete_sequence=['#2563EB'])
                            fig_corr.update_layout(height=350, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
                            st.plotly_chart(fig_corr, use_container_width=True)
                        else: st.info("Awaiting Digital Signal Data.")

            with ai_tabs[1]:
                st.markdown("#### 🛠️ Configure Scenario Parameters")
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1: sim_season = st.selectbox("Season", ["Winter", "Spring", "Summer", "Autumn", "Peak"])
                with sc2: sim_event = st.number_input("Event Attendance", value=0, step=500)
                with sc3: sim_clicks = st.number_input("Planned Ad Clicks", value=1000, step=100)
                with sc4: test_lift_pct = st.number_input("Apply Proven Exp Lift %", value=0.0, step=0.5)

                if st.button("🚀 Run Seasonal Projection", use_container_width=True):
                    seasonal_base = 1500 * {"Winter": 0.85, "Spring": 1.05, "Summer": 1.15, "Autumn": 1.20, "Peak": 1.35}.get(sim_season, 1.0)
                    digital_lift = (sim_clicks * 0.05)
                    gravity_lift = sim_event * 0.25
                    test_impact = seasonal_base * (test_lift_pct / 100)
                    proj_guests = max(0, seasonal_base + digital_lift + gravity_lift + test_impact)
                    
                    st.divider()
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Seasonal Base", f"{seasonal_base:,.0f}")
                    r2.metric("Marketing & Event Lift", f"{(digital_lift + gravity_lift):,.0f}")
                    r3.metric("AI Traffic Projection", f"{proj_guests:,.0f}", delta=f"{test_impact:+.0f} from Test")

            with ai_tabs[2]:
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
                        else: st.warning(f"Data Missing: Tag ledger entries as '{tag_a}' or '{tag_b}'.")
        current_tab_index += 1

    # --- TAB 3: BRAND & SENTIMENT PREMIUM (NEW PORT) ---
    if "Brand & Sentiment Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 📢 Brand Integrity & Sentiment Vault")
            bs_tabs = st.tabs(["📝 PR Scorecard", "🧠 Guest Sentiment Vault"])
            
            # --- 3A: PR SCORECARD ---
            with bs_tabs[0]:
                pr_res = supabase.table("pr_scorecard").select("*").eq("parent_company_id", comp_id).order("report_month", desc=True).execute()
                df_pr = pd.DataFrame(pr_res.data) if pr_res.data else pd.DataFrame()
                
                with st.expander("📝 Log Monthly PR Metrics", expanded=df_pr.empty):
                    with st.form("pr_entry_form", clear_on_submit=True):
                        f1, f2, f3 = st.columns(3)
                        m_date = f1.date_input("Report Month", value=date.today().replace(day=1))
                        m_imp = f2.number_input("Earned Impressions", min_value=0, step=1000)
                        m_ment = f3.number_input("Earned Mentions", min_value=0, step=1)
                        m_mediums = st.text_input("Primary Mediums (e.g., CTV News, Ottawa Citizen)")
                        m_comment = st.text_area("Executive Summary")
                        if st.form_submit_button("Vault PR Entry", use_container_width=True):
                            supabase.table("pr_scorecard").upsert({"parent_company_id": comp_id, "report_month": m_date.strftime("%Y-%m-%d"), "earned_impressions": m_imp, "earned_mentions": m_ment, "mediums": m_mediums, "executive_summary": m_comment}).execute()
                            st.rerun()

                if not df_pr.empty:
                    df_pr['report_month'] = pd.to_datetime(df_pr['report_month'])
                    st.divider()
                    fig_pr = go.Figure()
                    df_chart = df_pr.sort_values('report_month')
                    fig_pr.add_trace(go.Scatter(x=df_chart['report_month'], y=df_chart['earned_impressions'], name="Impressions", line=dict(color='#2563EB', width=4), yaxis="y"))
                    fig_pr.add_trace(go.Bar(x=df_chart['report_month'], y=df_chart['earned_mentions'], name="Mentions", marker_color='rgba(200, 200, 200, 0.3)', yaxis="y2"))
                    fig_pr.update_layout(height=350, template="plotly_white", margin=dict(l=0, r=0, t=10, b=0), yaxis2=dict(overlaying="y", side="right"), legend=dict(orientation="h", yanchor="bottom", y=1.02))
                    st.plotly_chart(fig_pr, use_container_width=True)

            # --- 3B: SENTIMENT VAULT ---
            with bs_tabs[1]:
                tags = ["Overall Property", "Casino Floor", "Hotel Room", "Restaurant", "Entertainment"]
                col_i1, col_i2 = st.columns(2)
                
                with col_i1:
                    with st.expander("📝 Manual Sentiment Archival", expanded=True):
                        with st.form("manual_sentiment_form", clear_on_submit=True):
                            manual_tag = st.selectbox("Assign to Asset:", tags)
                            manual_date = st.date_input("Review Date:", value=date.today())
                            f_text = st.text_area("Review Content", placeholder="Paste review text...", height=100)
                            if st.form_submit_button("🛡️ Archive & AI Score", use_container_width=True):
                                if f_text and archive_sentiment_entry(f_text, manual_tag, manual_date):
                                    st.rerun()

                with col_i2:
                    with st.expander("📄 DOCX Intelligence Loader (Legacy)", expanded=True):
                        st.caption("Upload raw feedback exports to auto-score via Gemini AI.")
                        uploaded_doc = st.file_uploader("Upload .docx Source", type="docx")
                        bulk_tag = st.selectbox("Bulk Assign:", tags, key="b_tag")
                        bulk_date = st.date_input("Bulk Review Date:", value=date.today(), key="b_date")
                        if uploaded_doc and st.button("🚀 Execute Bulk Parse", use_container_width=True):
                            try:
                                from docx import Document
                                doc = Document(uploaded_doc)
                                valid_paras = [p.text.strip() for p in doc.paragraphs if len(p.text.strip()) > 20]
                                if valid_paras:
                                    bar = st.progress(0)
                                    success = 0
                                    for idx, text in enumerate(valid_paras):
                                        if archive_sentiment_entry(text, bulk_tag, bulk_date): success += 1
                                        bar.progress((idx + 1) / len(valid_paras))
                                        time.sleep(1.5) # Throttle Gemini API limits
                                    st.success(f"{success} entries scored & vaulted.")
                            except Exception as e:
                                st.error("Requires python-docx installed. Or verify API limits.")

                st.divider()
                s_res = supabase.table("sentiment_history").select("*").eq("parent_company_id", comp_id).order("timestamp", desc=True).execute()
                if s_res.data:
                    df_vault = pd.DataFrame(s_res.data)
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Total Vault Volume", f"{len(df_vault):,} Records")
                    sc2.metric("Positive Sentiments", f"{len(df_vault[df_vault['sentiment_category'] == 'Positive']):,}")
                    sc3.metric("Critical Sentiments", f"{len(df_vault[df_vault['sentiment_category'] == 'Negative']):,}", delta_color="inverse")
                    
                    st.markdown("#### 🔍 Recent AI-Scored Reviews")
                    for _, row in df_vault.head(10).iterrows():
                        with st.container(border=True):
                            c1, c2 = st.columns([4, 1])
                            c1.markdown(f"**Asset:** `{row.get('asset')}` | **Category:** {row.get('sentiment_category')}")
                            c1.write(row.get('raw_text'))
                            
                            score = float(row.get('sentiment_score', 0))
                            color = "#EF4444" if score < -0.3 else "#10B981" if score > 0.3 else "#F59E0B"
                            c2.metric("AI Score", f"{score:.2f}")
                            c2.markdown(f"<div style='height:8px; width:100%; background:{color}; border-radius:4px;'></div>", unsafe_allow_html=True)
                else:
                    st.info("No sentiment data vaulted yet.")
        current_tab_index += 1

    # --- TAB 4: HOTEL ENGINE ---
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

    # --- TAB 5: F&B ENGINE ---
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

    # --- TAB 6: ENTERTAINMENT ENGINE ---
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

    # --- TAB 7: SETTINGS ---
    with tabs[-1]:
        st.markdown("### ⚙️ Account Management & Settings")
        
        with st.expander("💳 Billing & Active Subscriptions", expanded=True):
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.markdown("##### Your Active Modules")
                if active_subs_details: st.dataframe(pd.DataFrame(active_subs_details), use_container_width=True, hide_index=True)
                else: st.info("No premium modules active.")
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
