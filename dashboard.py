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
import calendar

# ==========================================
# STATE INITIALIZATION & SAFETY WRAPPER
# ==========================================
if "active_view" not in st.session_state:
    st.session_state.active_view = "dashboard"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def safe_get_data(res):
    """Bulletproofs Supabase API responses against Streamlit AttributeError crashes."""
    if hasattr(res, 'data'):
        return res.data
    elif isinstance(res, dict):
        return res.get('data', [])
    return []

# ==========================================
# CALIBRATION & AI ENGINES
# ==========================================
def get_forensic_metrics(df_input, cals):
    if not df_input: return {"df": pd.DataFrame()}
    df = pd.DataFrame(df_input).copy()
    df['record_date'] = pd.to_datetime(df['record_date'])
    
    # 1. Base Heartbeat (Calibrated)
    hb = {'Monday': cals['mon_base'], 'Tuesday': cals['tue_base'], 'Wednesday': cals['wed_base'], 
          'Thursday': cals['thu_base'], 'Friday': cals['fri_base'], 'Saturday': cals['sat_base'], 'Sunday': cals['sun_base']}
    df['baseline'] = df['record_date'].dt.day_name().map(hb).astype(float)
    
    # 2. Marketing Decay (Calibrated)
    dec, c1, c2 = 0.85, cals['ad_click_lift'], 0.0002
    pool, lift = 0.0, []
    for _, r in df.iterrows():
        pool = ((float(r.get('ad_clicks', 0) or 0)*c1) + (float(r.get('ad_impressions', 0) or 0)*c2)) + (pool * dec)
        lift.append(pool)
    df['residual_lift'] = lift
    
    # 3. Expected Traffic Synthesis
    if 'predicted_traffic' in df.columns:
        fallback_calc = df['baseline'] + df['residual_lift'] + float(cals['promo_lift'])
        df['expected'] = pd.to_numeric(df['predicted_traffic'], errors='coerce').fillna(fallback_calc)
        df['predicted_traffic'] = df['expected']
    else:
        df['predicted_traffic'] = df['baseline'] + df['residual_lift'] + float(cals['promo_lift'])
        
    return {"df": df}

def generate_forward_forecast(df_historical, cals, days=14):
    """Generates a pure future predictive dataframe based on custom property calibrations."""
    if df_historical.empty: return pd.DataFrame()
    last_date = df_historical['record_date'].max()
    future_dates = [last_date + timedelta(days=i) for i in range(1, days+1)]
    df_future = pd.DataFrame({'record_date': future_dates})
    
    hb = {'Monday': cals['mon_base'], 'Tuesday': cals['tue_base'], 'Wednesday': cals['wed_base'], 
          'Thursday': cals['thu_base'], 'Friday': cals['fri_base'], 'Saturday': cals['sat_base'], 'Sunday': cals['sun_base']}
    df_future['baseline'] = df_future['record_date'].dt.day_name().map(hb).astype(float)
    
    last_lift = df_historical['residual_lift'].iloc[-1] if 'residual_lift' in df_historical.columns else 0
    decay_rate = 0.85
    future_lift = []
    for _ in range(days):
        last_lift = last_lift * decay_rate
        future_lift.append(last_lift)
    
    df_future['residual_lift'] = future_lift
    df_future['predicted_traffic'] = df_future['baseline'] + df_future['residual_lift']
    
    # Generate Financial Forecasts based on GM calibration
    df_future['predicted_coin_in'] = df_future['predicted_traffic'] * cals['avg_coin_in']
    df_future['predicted_table_drop'] = df_future['predicted_traffic'] * cals['avg_table_drop']
    
    return df_future

def get_omniscient_advisor_context(comp_id):
    context = f"--- EXECUTIVE ANALYST CONTEXT FOR TENANT {comp_id} ---\n"
    perf = supabase.table("property_performance").select("*").eq("parent_company_id", comp_id).order("record_date", desc=True).limit(30).execute()
    perf_data = safe_get_data(perf)
    if perf_data: context += f"\nCASINO LEDGER (30d):\n{pd.DataFrame(perf_data).to_string(index=False)}\n"
    roi = supabase.table("monthly_roi").select("*").eq("parent_company_id", comp_id).order("report_month", desc=True).limit(6).execute()
    roi_data = safe_get_data(roi)
    if roi_data: context += f"\nMARKETING ROI MATRIX (6m):\n{pd.DataFrame(roi_data).to_string(index=False)}\n"
    sent = supabase.table("sentiment_history").select("*").eq("parent_company_id", comp_id).order("timestamp", desc=True).limit(50).execute()
    sent_data = safe_get_data(sent)
    if sent_data: context += f"\nRECENT GUEST SENTIMENT:\n{pd.DataFrame(sent_data).to_string(index=False)}\n"
    pr = supabase.table("pr_scorecard").select("*").eq("parent_company_id", comp_id).order("report_month", desc=True).limit(6).execute()
    pr_data = safe_get_data(pr)
    if pr_data: context += f"\nPR SCORECARD:\n{pd.DataFrame(pr_data).to_string(index=False)}\n"
    return context

def ask_ai_advisor(query, comp_id, chat_history):
    genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", ""))
    model = genai.GenerativeModel('gemini-2.5-flash')
    context = get_omniscient_advisor_context(comp_id)
    history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history[:-1]])
    
    prompt = f"""
    You are the FloorCast AI Advisor. You have full visibility into the property's operational and marketing data. 
    Analyze the context provided and provide a data-backed, strategic recommendation.
    
    CONTEXT:
    {context}
    
    PREVIOUS CONVERSATION:
    {history_text}
    
    USER QUERY:
    {query}
    
    ADVISOR RECOMMENDATION:
    """
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"AI Advisor is currently unavailable. Error: {e}"

def get_aggregated_email_analytics(comp_id, s_date, e_date):
    target_uuid = str(comp_id)
    start_str = s_date.replace(day=1).strftime("%Y-%m-%d")
    last_day = calendar.monthrange(e_date.year, e_date.month)[1]
    end_str = e_date.replace(day=last_day).strftime("%Y-%m-%d")
    m_agg, c_agg, prev_m_agg, prev_c_agg = {}, [], {}, []
    try:
        mac_res = supabase.table("monthly_email_snapshots").select("*").eq("parent_company_id", target_uuid).gte("snapshot_month", start_str).lte("snapshot_month", end_str).order("snapshot_month", desc=True).execute()
        mac_data = safe_get_data(mac_res)
        if not mac_data: return m_agg, c_agg, prev_m_agg, prev_c_agg
        df = pd.DataFrame(mac_data)
        total_vol = df['total_emails_delivered'].sum() if 'total_emails_delivered' in df.columns else 0
        if total_vol > 0:
            m_agg = {'total_emails_delivered': total_vol, 'avg_unique_open_rate': df.get('avg_unique_open_rate', df.get('open_rate', pd.Series([0]))).mean(), 'avg_bounce_rate': df.get('avg_bounce_rate', pd.Series([0])).mean(), 'avg_unsubscribe_rate': df.get('avg_unsubscribe_rate', pd.Series([0])).mean()}
    except Exception: pass
    return m_agg, c_agg, prev_m_agg, prev_c_agg

def archive_sentiment_entry(text, asset_tag, review_date, comp_id):
    try:
        genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel('gemini-2.5-flash') 
        ai_res = model.generate_content(f"Analyze sentiment. Return ONLY a single float between -1.0 and 1.0: {text}")
        try: sentiment_score = float(ai_res.text.strip())
        except: sentiment_score = 0.0

        sentiment_category = "Positive" if sentiment_score > 0.3 else "Negative" if sentiment_score < -0.3 else "Neutral"
        abs_score = abs(sentiment_score)
        intensity_level = "Extreme" if abs_score >= 0.8 else "Moderate" if abs_score >= 0.4 else "Low"

        payload = {
            "message_id": str(uuid.uuid4()), "parent_company_id": comp_id, "asset": asset_tag,
            "sentiment_score": sentiment_score, "sentiment_category": sentiment_category,
            "intensity_level": intensity_level, "raw_text": text,
            "timestamp": review_date.strftime("%Y-%m-%dT12:00:00")
        }
        supabase.table("sentiment_history").insert(payload).execute()
        return True
    except: return False

# ==========================================
# STATE INITIALIZATION (BULLTPROOF)
# ==========================================
def initialize_session_state():
    if "active_view" not in st.session_state:
        st.session_state.active_view = "dashboard"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    # Added this to prevent the attribute error when fetching user profile
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {}

# Run this once at the very start
initialize_session_state()

# ==========================================
# MAIN RENDER FUNCTION
# ==========================================
def render():
    profile = st.session_state.get('user_profile', {})
    user_role = profile.get('global_role', 'User')

    # --- 1. FETCH CLIENT CONTEXT & CALIBRATIONS ---
    try:
        access_res = supabase.table("user_property_access").select("parent_company_id, parent_companies(company_name, total_owed)").eq("user_email", profile.get('email', '')).execute()
        access_data = safe_get_data(access_res)
        if not access_data:
            st.error("No company link found. Contact Support.")
            return
        
        comp_id = access_data[0]['parent_company_id']
        comp_name = access_data[0]['parent_companies']['company_name']
        comp_owed = float(access_data[0]['parent_companies']['total_owed'] or 0.0)

        all_mods_res = supabase.table("system_modules").select("*").execute()
        all_mods_data = safe_get_data(all_mods_res)
        all_modules = {m['module_name']: m for m in all_mods_data} if all_mods_data else {}

        subs_res = supabase.table("company_subscriptions").select("agreed_price, billing_frequency, system_modules(module_name)").eq("parent_company_id", comp_id).eq("status", "Active").execute()
        subs_data = safe_get_data(subs_res)
        active_modules = [s['system_modules']['module_name'] for s in subs_data] if subs_data else []
        active_subs_details = [{"Module": s['system_modules']['module_name'], "Price": float(s['agreed_price']), "Frequency": s['billing_frequency']} for s in subs_data] if subs_data else []
        
        inv_res = supabase.table("invoices").select("*").eq("parent_company_id", comp_id).eq("status", "Pending").execute()
        pending_invoices = safe_get_data(inv_res)
        
        # Load GM AI Calibrations
        cals = {
            'mon_base': 4000.0, 'tue_base': 3800.0, 'wed_base': 4200.0, 'thu_base': 4800.0,
            'fri_base': 6500.0, 'sat_base': 7200.0, 'sun_base': 5500.0,
            'avg_coin_in': 115.0, 'avg_table_drop': 45.0,
            'ad_click_lift': 0.05, 'promo_lift': 500.0,
            'rain_penalty': -12.0, 'snow_penalty': -45.0,
            'fb_capture_pct': 15.0, 'fb_avg_check': 45.0,
            'hotel_capture_pct': 5.0, 'hotel_base_adr': 189.0
        }
        try:
            cal_res = supabase.table("property_calibrations").select("calibrations").eq("parent_company_id", comp_id).execute()
            cal_data = safe_get_data(cal_res)
            if cal_data and cal_data[0].get('calibrations'):
                cals.update(cal_data[0]['calibrations'])
        except Exception:
            pass

    except Exception as e:
        st.error(f"Failed to load workspace data: {e}")
        return

    # --- 2. GLOBAL PREDICTIVE DATA FETCH ---
    try:
        perf_res = supabase.table("property_performance").select("*").eq("parent_company_id", comp_id).order("record_date", asc=True).execute()
        perf_data = safe_get_data(perf_res)
        if perf_data:
            df_perf = pd.DataFrame(perf_data)
            for col in ['coin_in', 'table_drop', 'marketing_spend', 'actual_traffic', 'ad_clicks', 'attendance', 'rooms_sold', 'adr', 'fb_covers', 'fb_revenue', 'tickets_sold', 'ent_revenue']:
                if col in df_perf.columns: df_perf[col] = pd.to_numeric(df_perf[col], errors='coerce').fillna(0)
            
            # Application of the Calibrated Forecasting Engine
            m = get_forensic_metrics(df_perf.to_dict(orient='records'), cals)
            df_perf = m['df']
            df_forward = generate_forward_forecast(df_perf, cals, days=14)
            
            total_coin_in = df_perf['coin_in'].sum()
            total_table_drop = df_perf['table_drop'].sum()
            total_marketing = df_perf['marketing_spend'].sum()
            has_data = True
        else:
            total_coin_in, total_table_drop, total_marketing = 0.0, 0.0, 0.0
            has_data = False
            df_perf = pd.DataFrame()
            df_forward = pd.DataFrame()
    except Exception:
        total_coin_in, total_table_drop, total_marketing = 0.0, 0.0, 0.0
        has_data = False
        df_perf = pd.DataFrame()
        df_forward = pd.DataFrame()

    def save_daily_log(entry_date, payload):
        try:
            # 1. Check if record exists
            existing = supabase.table("property_performance").select("id").eq("parent_company_id", comp_id).eq("record_date", str(entry_date)).execute()
            ex_data = safe_get_data(existing)
            
            # 2. Perform action
            if ex_data: 
                res = supabase.table("property_performance").update(payload).eq("id", ex_data[0]['id']).execute()
            else:
                payload["parent_company_id"] = comp_id
                payload["record_date"] = str(entry_date)
                res = supabase.table("property_performance").insert(payload).execute()
            
            # 3. VERIFICATION STEP
            # If the response 'data' is empty after an insert/update, it means RLS blocked the write.
            if not res.data:
                st.error("🚨 DATABASE BLOCKED WRITE: Your Row Level Security (RLS) policy is preventing this insert. Please check your SQL policies.")
                return
                
            st.success(f"Ledger for {entry_date} securely updated.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e: 
            st.error(f"Save failed: {e}")
            
    # --- 3. TOP NAVIGATION BAR ---
    nav_c1, nav_c2, nav_c3, nav_c4 = st.columns([5, 2, 1.5, 1])
    with nav_c1: 
        st.markdown(f"<h3 style='margin-top: 10px; color:#111827;'>🎰 FloorCast OS <span style='color: #6B7280; font-weight: 400; font-size: 1.2rem;'>| {comp_name}</span></h3>", unsafe_allow_html=True)
    with nav_c2: 
        st.markdown(f"<p style='margin-top: 15px; color:#6B7280; font-size: 0.9rem; text-align: right;'>👤 {profile.get('first_name', '')} ({user_role})</p>", unsafe_allow_html=True)
    with nav_c3:
        if st.session_state.active_view == "ai_chat":
            if st.button("⬅️ Dashboard", use_container_width=True, type="secondary"):
                st.session_state.active_view = "dashboard"
                st.rerun()
        else:
            if st.button("🤖 AI Advisor", use_container_width=True, type="primary"):
                st.session_state.active_view = "ai_chat"
                st.rerun()
    with nav_c4:
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    st.divider()

    # ==========================================
    # VIEW ROUTING: CHAT vs DASHBOARD
    # ==========================================
    if st.session_state.active_view == "ai_chat":
        # --- THE FULL-PAGE AI CHAT INTERFACE ---
        st.markdown(f"### 🤖 FloorCast AI Advisor — {comp_name}")
        st.caption("I am fully hydrated with your recent Casino Ledgers, Marketing ROI, PR reach, and Guest Sentiment logs. Ask me anything.")
        st.divider()
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
            with st.chat_message("assistant"):
                with st.spinner("Analyzing operational and marketing data databases..."):
                    query = st.session_state.chat_history[-1]["content"]
                    response = ask_ai_advisor(query, comp_id, st.session_state.chat_history)
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    st.rerun()
                    
        if new_query := st.chat_input("Ask a follow-up question..."):
            st.session_state.chat_history.append({"role": "user", "content": new_query})
            st.rerun()

    else:
        # --- THE MAIN DASHBOARD VIEW ---
        
        # --- DYNAMIC TAB GENERATOR ---
        tab_titles = ["📊 Master Overview"]
        if "Core AI & Marketing" in active_modules: 
            tab_titles.extend(["🎰 Casino", "📈 Marketing", "📋 Reports"])
        if "Brand & Sentiment Premium" in active_modules: tab_titles.append("📢 Brand & Sentiment")
        if "Hotel Premium" in active_modules: tab_titles.append("🏨 Hotel Engine")
        if "F&B Premium" in active_modules: tab_titles.append("🍔 F&B Engine")
        if "Entertainment Premium" in active_modules: tab_titles.append("🎫 Entertainment")
        tab_titles.append("⚙️ Settings")

        tabs = st.tabs(tab_titles)

        # --- TAB 1: MASTER OVERVIEW (WITH PREDICTIVE) ---
        with tabs[0]:
            st.markdown("### Floor Performance Snapshot")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Gross Coin-In", f"${total_coin_in:,.0f}")
            c2.metric("Forecasted ADR", "$0.00", "Awaiting Pace Data") if "Hotel Premium" in active_modules else c2.metric("Forecasted ADR", "🔒 Locked", "Requires Hotel Module")
            c3.metric("F&B Covers", "0", "Awaiting POS Data") if "F&B Premium" in active_modules else c3.metric("F&B Covers", "🔒 Locked", "Requires F&B Module")
            c4.metric("Attributed Media Spend", f"${total_marketing:,.0f}")

            if has_data and not df_forward.empty:
                st.divider()
                st.markdown("#### 🔮 14-Day Financial & Traffic Forecast")
                st.caption("AI projection based on your custom property calibrations, momentum, and decay.")
                
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    fig_forecast = go.Figure()
                    recent_actuals = df_perf.tail(7)
                    fig_forecast.add_trace(go.Scatter(x=recent_actuals['record_date'], y=recent_actuals['actual_traffic'], name="Historical Actuals", line=dict(color='#94A3B8', width=3)))
                    fig_forecast.add_trace(go.Scatter(x=df_forward['record_date'], y=df_forward['predicted_traffic'], name="AI Forward Prediction", line=dict(color='#2563EB', width=4, dash='dash')))
                    fig_forecast.update_layout(title="Foot Traffic Projection", height=300, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig_forecast, use_container_width=True)
                with f_col2:
                    fig_fin = go.Figure()
                    fig_fin.add_trace(go.Scatter(x=df_forward['record_date'], y=df_forward['predicted_coin_in'], name="Projected Coin-In", line=dict(color='#10B981', width=3)))
                    fig_fin.add_trace(go.Scatter(x=df_forward['record_date'], y=df_forward['predicted_table_drop'], name="Projected Table Drop", line=dict(color='#F59E0B', width=3)))
                    fig_fin.update_layout(title="Revenue Projection", height=300, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig_fin, use_container_width=True)

        # --- THE CORE SUITE ---
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
                        m_clicks = c3.number_input("Ad Clicks", min_value=0, step=100)
                        m_imps = c4.number_input("Ad Impressions", min_value=0, step=1000)
                        w1, w2 = st.columns(2)
                        m_rain = w1.number_input("Rain (mm)", min_value=0.0, step=1.0)
                        m_snow = w2.number_input("Snow (cm)", min_value=0.0, step=1.0)
                        if st.form_submit_button("🚀 Commit to Ledger", type="primary", use_container_width=True):
                            save_daily_log(entry_date, {"coin_in": m_coin, "table_drop": m_table, "actual_traffic": m_traffic, "new_members": m_members, "attendance": m_event, "ad_clicks": m_clicks, "ad_impressions": m_imps, "active_promo": m_promo.strip() if m_promo else None, "rain_mm": m_rain, "snow_cm": m_snow})

                with st.expander("📂 Historical Ledger Corrections", expanded=False):
                    if has_data and not df_perf.empty:
                        df_edit = df_perf.copy().sort_values('record_date', ascending=False)
                        df_edit['record_date'] = pd.to_datetime(df_edit['record_date']).dt.date
                        edit_cols = ['id', 'record_date', 'coin_in', 'table_drop', 'actual_traffic', 'new_members', 'attendance', 'ad_clicks', 'ad_impressions', 'rain_mm', 'snow_cm']
                        for c in edit_cols:
                            if c not in df_edit.columns: df_edit[c] = None
                        df_edit = df_edit[edit_cols].head(30)
                        with st.form("ledger_corrections_form", border=False):
                            edited_df = st.data_editor(
                                df_edit,
                                column_config={
                                    "id": None, 
                                    "record_date": st.column_config.DateColumn("Date", required=True),
                                    "coin_in": st.column_config.NumberColumn("Coin-In ($)", step=100.0),
                                    "table_drop": st.column_config.NumberColumn("Table Drop ($)", step=100.0),
                                    "actual_traffic": st.column_config.NumberColumn("Traffic", step=1),
                                    "new_members": st.column_config.NumberColumn("Members", step=1),
                                    "attendance": st.column_config.NumberColumn("Events", step=1),
                                    "ad_clicks": st.column_config.NumberColumn("Clicks", step=100),
                                    "ad_impressions": st.column_config.NumberColumn("Imps", step=1000)
                                },
                                num_rows="dynamic", use_container_width=True, hide_index=True, key="interactive_ledger_editor"
                            )
                            if st.form_submit_button("💾 Sync Corrections to Vault", type="primary", use_container_width=True):
                                try:
                                    orig_ids, new_ids = set(df_edit['id'].dropna()), set(edited_df['id'].dropna())
                                    deleted_ids = orig_ids - new_ids
                                    if deleted_ids:
                                        for d_id in deleted_ids: supabase.table("property_performance").delete().eq("id", d_id).execute()
                                    upsert_payload = []
                                    for _, row in edited_df.iterrows():
                                        rec = { "parent_company_id": comp_id, "record_date": str(row['record_date']), "coin_in": row['coin_in'] if pd.notna(row['coin_in']) else 0, "table_drop": row['table_drop'] if pd.notna(row['table_drop']) else 0, "actual_traffic": row['actual_traffic'] if pd.notna(row['actual_traffic']) else 0, "new_members": row['new_members'] if pd.notna(row['new_members']) else 0, "attendance": row['attendance'] if pd.notna(row['attendance']) else 0, "ad_clicks": row['ad_clicks'] if pd.notna(row['ad_clicks']) else 0, "ad_impressions": row['ad_impressions'] if pd.notna(row['ad_impressions']) else 0, "rain_mm": row['rain_mm'] if pd.notna(row['rain_mm']) else 0, "snow_cm": row['snow_cm'] if pd.notna(row['snow_cm']) else 0 }
                                        if pd.notna(row.get('id')): rec['id'] = row['id']
                                        upsert_payload.append(rec)
                                    if upsert_payload: supabase.table("property_performance").upsert(upsert_payload).execute()
                                    st.success("✅ Ledger Corrections Synchronized."); time.sleep(1.5); st.rerun()
                                except Exception as e: st.error(f"Sync failed: {e}")

                st.divider()
                st.markdown("#### 🔮 Specific Scenario Simulator")
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

                    if st.button("🚀 Run Scenario Projection", use_container_width=True):
                        seasonal_base = 1500 * {"Winter": 0.85, "Spring": 1.05, "Summer": 1.15, "Autumn": 1.20, "Peak": 1.35}.get(sim_season, 1.0)
                        gravity_lift = sim_event * 0.25
                        friction = (sim_rain * -12) + (sim_snow * -45)
                        test_impact = seasonal_base * (test_lift_pct / 100)
                        proj_guests = max(0, seasonal_base + gravity_lift + friction + test_impact)
                        st.divider()
                        r1, r2, r3 = st.columns(3)
                        r1.metric("Seasonal Base", f"{seasonal_base:,.0f}")
                        r2.metric("Gravity Lift & Friction", f"{(gravity_lift + friction):,.0f}")
                        r3.metric("AI Scenario Projection", f"{proj_guests:,.0f}", delta=f"{test_impact:+.0f} from Lift")

            current_tab_index += 1

            # --- TAB 3: MARKETING ---
            with tabs[current_tab_index]:
                st.markdown("### 📈 Marketing & Attribution Analytics")
                mkt_tabs = st.tabs(["💰 Monthly Spend & BL-ROAS", "📊 O2O Attribution Visuals", "🔬 Experiment Vault"])
                
                with mkt_tabs[0]:
                    st.markdown("#### Monthly Ad Spend & ROI Calculator")
                    LTV_BENCHMARK = 1900.00
                    with st.form("roas_monthly_form", border=True):
                        selected_month = st.date_input("Audit Fiscal Month", value=date.today().replace(day=1))
                        ledger_traffic, ledger_signups, ledger_coin_in = 0, 0, 0.0
                        if not df_perf.empty:
                            m_mask = (df_perf['record_date'].dt.month == selected_month.month) & (df_perf['record_date'].dt.year == selected_month.year)
                            selected_month_df = df_perf.loc[m_mask].copy()
                            if not selected_month_df.empty:
                                ledger_traffic = int(selected_month_df['actual_traffic'].sum())
                                ledger_signups = int(selected_month_df['new_members'].sum())
                                ledger_coin_in = float(selected_month_df['coin_in'].sum())

                        c1, c2, c3 = st.columns(3)
                        utm_s = c1.number_input("UTM Sessions", min_value=0, step=100)
                        org_s = c2.number_input("Organic Sessions", min_value=0, step=100)
                        ad_spend = c3.number_input("Total Ad Spend ($)", min_value=0.0, step=500.0)
                        
                        s1, s2, s3 = st.columns(3)
                        likes = s1.number_input("Social Engagement", min_value=0, step=10)
                        shares = s2.number_input("Social Shares", min_value=0, step=5)
                        views = s3.number_input("Reach / Impressions", min_value=0, step=1000)

                        g1, g2, g3 = st.columns(3)
                        time_site = g1.number_input("Time-on-Site Sessions", min_value=0, step=10)
                        cta_clicks = g2.number_input("Booking CTA Clicks", min_value=0, step=10)
                        geo_lift = g3.number_input("Incremental Geo Traffic", min_value=0, step=10)

                        if st.form_submit_button("🚀 Generate BL-ROAS Audit", use_container_width=True):
                            brand_value = (utm_s * 1.5) + (org_s * 0.5) + (likes * 0.1) + (shares * 0.5) + (geo_lift * 2.0)
                            bl_roas = brand_value / ad_spend if ad_spend > 0 else 0.0
                            enhanced_rev = brand_value + ledger_coin_in + (ledger_signups * LTV_BENCHMARK)
                            try:
                                supabase.table("monthly_roi").upsert({
                                    "parent_company_id": comp_id, "report_month": str(selected_month.replace(day=1)),
                                    "utm_sessions": utm_s, "organic_sessions": org_s, "ad_spend": ad_spend,
                                    "social_likes": likes, "social_shares": shares, "post_views": views,
                                    "site_time_sessions": time_site, "booking_clicks": cta_clicks,
                                    "geo_lift_traffic": geo_lift, "brand_value": brand_value, 
                                    "calculated_bl_roas": bl_roas, "enhanced_revenue": enhanced_rev
                                }).execute()
                                st.success(f"Successfully vaulted BL-ROAS for {selected_month.strftime('%B %Y')}"); st.rerun()
                            except Exception as e: st.error(f"Error saving ROI data: {e}")

                    try:
                        roi_res = supabase.table("monthly_roi").select("*").eq("parent_company_id", comp_id).order("report_month", desc=True).execute()
                        roi_data = safe_get_data(roi_res)
                        if roi_data:
                            df_roi = pd.DataFrame(roi_data)
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
                    except Exception: pass

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
                            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Adstock_Decay_Curve.png/600px-Adstock_Decay_Curve.png", use_container_width=True)

                with mkt_tabs[2]:
                    ev_res = supabase.table("experiment_registry").select("*").eq("parent_company_id", comp_id).execute()
                    ev_data = safe_get_data(ev_res)
                    v_res, v_man = st.tabs(["📊 Results", "⚙️ Registry"])
                    with v_man:
                        with st.form("new_experiment_form", clear_on_submit=True):
                            e1, e2 = st.columns(2)
                            n_name = e1.text_input("Experiment Name")
                            n_a, n_b = e2.text_input("Control Tag (Version A)", value="Control"), e2.text_input("Test Tag (Version B)", value="Test_V1")
                            if st.form_submit_button("🚀 Deploy to Registry") and n_name and n_a and n_b:
                                supabase.table("experiment_registry").insert({"parent_company_id": comp_id, "test_name": n_name, "version_a_tag": n_a.strip(), "version_b_tag": n_b.strip()}).execute()
                                st.rerun()
                    with v_res:
                        if ev_data and has_data:
                            exp_dict = {e['test_name']: e for e in ev_data}
                            sel_exp = st.selectbox("Select Active Experiment:", list(exp_dict.keys()))
                            tag_a, tag_b = exp_dict[sel_exp]['version_a_tag'], exp_dict[sel_exp]['version_b_tag']
                            df_perf['experiment_tag'] = df_perf['experiment_tag'].astype(str).str.strip()
                            df_a, df_b = df_perf[df_perf['experiment_tag'] == tag_a], df_perf[df_perf['experiment_tag'] == tag_b]
                            if not df_a.empty and not df_b.empty:
                                vol_a, vol_b = df_a['actual_traffic'].mean(), df_b['actual_traffic'].mean()
                                st.metric("Total Volume Lift", f"{((vol_b - vol_a) / vol_a) * 100 if vol_a > 0 else 0:+.1f}% vs Control")

            current_tab_index += 1

            # --- TAB 4: REPORTS ---
            with tabs[current_tab_index]:
                st.markdown(f"### 📋 Master Property Audit: {comp_name}")
                st.caption("Forensic Ledger: Financials, Multi-Channel Attribution, & Earned Media")
                if not has_data or df_perf.empty:
                    st.info("No ledger data found.")
                else:
                    min_d, max_d = df_perf['record_date'].min().date(), df_perf['record_date'].max().date()
                    col_d, col_b = st.columns([2, 1])
                    audit_range = col_d.date_input("Audit Window:", value=(min_d, max_d))
                    
                    if isinstance(audit_range, tuple) and len(audit_range) == 2:
                        s_date, e_date = audit_range
                        mask = (df_perf['record_date'].dt.date >= s_date) & (df_perf['record_date'].dt.date <= e_date)
                        df_audit = df_perf.loc[mask].copy()
                        
                        if not df_audit.empty:
                            t_rev = df_audit['coin_in'].sum()
                            t_traf = df_audit['actual_traffic'].sum()
                            t_mems = df_audit['new_members'].sum()
                            t_clicks = df_audit['ad_clicks'].sum()
                            t_imps = df_audit['ad_impressions'].sum()
                            t_pred = df_audit['predicted_traffic'].sum()
                            accuracy = (1 - (abs(t_traf - t_pred) / t_traf)) * 100 if t_traf > 0 else 0

                            st.markdown("### 📊 Executive Summary")
                            k1, k2, k3, k4, k5, k6 = st.columns(6)
                            k1.metric("Total Traffic", f"{t_traf:,.0f}")
                            k2.metric("Actual Revenue", f"${t_rev:,.0f}")
                            k3.metric("Ad Clicks", f"{t_clicks:,.0f}")
                            k4.metric("New Members", f"{t_mems:,.0f}")
                            k5.metric("Social Reach", f"{t_imps:,.0f}")
                            k6.metric("AI Accuracy", f"{accuracy:.1f}%")

                            st.divider()
                            st.markdown("### 🌊 Multi-Channel Attribution Flow")
                            fig_stack = go.Figure()
                            for name, col, color in [('Organic Heartbeat', 'baseline', '#8E9AAF'), ('Digital ROI Lift', 'residual_lift', '#0047AB'), ('Event Attendance', 'attendance', '#FFCC00')]:
                                if col in df_audit.columns: fig_stack.add_trace(go.Scatter(x=df_audit['record_date'], y=df_audit[col], name=name, stackgroup='one', line=dict(width=0.5, color=color), fill='tonexty'))
                            fig_stack.update_layout(height=400, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
                            st.plotly_chart(fig_stack, use_container_width=True)
                            
                            st.divider()
                            st.download_button("📥 Download Master Report (CSV)", data=df_audit.to_csv(index=False).encode('utf-8'), file_name=f"FloorCast_Audit_{s_date}.csv", use_container_width=True)
            current_tab_index += 1

        # --- TAB 5: BRAND & SENTIMENT ---
        if "Brand & Sentiment Premium" in active_modules:
            with tabs[current_tab_index]:
                st.markdown("### 📢 Brand Integrity & Sentiment Vault")
                bs_tabs = st.tabs(["📝 PR Scorecard", "🧠 Guest Sentiment Vault"])
                with bs_tabs[0]:
                    pr_res = supabase.table("pr_scorecard").select("*").eq("parent_company_id", comp_id).order("report_month", desc=True).execute()
                    pr_data = safe_get_data(pr_res)
                    df_pr = pd.DataFrame(pr_data) if pr_data else pd.DataFrame()
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
                        fig_pr = go.Figure()
                        df_chart = df_pr.sort_values('report_month')
                        fig_pr.add_trace(go.Scatter(x=df_chart['report_month'], y=df_chart['earned_impressions'], name="Impressions", line=dict(color='#2563EB', width=4), yaxis="y"))
                        fig_pr.add_trace(go.Bar(x=df_chart['report_month'], y=df_chart['earned_mentions'], name="Mentions", marker_color='rgba(200, 200, 200, 0.3)', yaxis="y2"))
                        fig_pr.update_layout(height=350, template="plotly_white", margin=dict(l=0, r=0, t=10, b=0), yaxis2=dict(overlaying="y", side="right"), legend=dict(orientation="h", yanchor="bottom", y=1.02))
                        st.plotly_chart(fig_pr, use_container_width=True)

                with bs_tabs[1]:
                    tags = ["Overall Property", "Casino Floor", "Hotel Room", "Restaurant", "Entertainment"]
                    col_i1, col_i2 = st.columns(2)
                    with col_i1:
                        with st.expander("📝 Manual Sentiment Archival", expanded=True):
                            with st.form("manual_sentiment_form", clear_on_submit=True):
                                manual_tag = st.selectbox("Assign to Asset:", tags)
                                manual_date = st.date_input("Review Date:", value=date.today())
                                f_text = st.text_area("Review Content", height=100)
                                if st.form_submit_button("🛡️ Archive & AI Score", use_container_width=True):
                                    if f_text and archive_sentiment_entry(f_text, manual_tag, manual_date, comp_id): st.rerun()
                    with col_i2:
                        with st.expander("📄 DOCX Intelligence Loader (Legacy)", expanded=True):
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
                                        for idx, text in enumerate(valid_paras):
                                            archive_sentiment_entry(text, bulk_tag, bulk_date, comp_id)
                                            bar.progress((idx + 1) / len(valid_paras))
                                            time.sleep(1.5)
                                        st.success("Entries scored & vaulted.")
                                except Exception as e: st.error("Verification failed.")

                    s_res = supabase.table("sentiment_history").select("*").eq("parent_company_id", comp_id).order("timestamp", desc=True).execute()
                    s_data = safe_get_data(s_res)
                    if s_data:
                        df_vault = pd.DataFrame(s_data)
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.metric("Total Vault Volume", f"{len(df_vault):,} Records")
                        sc2.metric("Positive Sentiments", f"{len(df_vault[df_vault['sentiment_category'] == 'Positive']):,}")
                        sc3.metric("Critical Sentiments", f"{len(df_vault[df_vault['sentiment_category'] == 'Negative']):,}", delta_color="inverse")
                        for _, row in df_vault.head(10).iterrows():
                            with st.container(border=True):
                                c1, c2 = st.columns([4, 1])
                                c1.markdown(f"**Asset:** `{row.get('asset')}` | **Category:** {row.get('sentiment_category')}")
                                c1.write(row.get('raw_text'))
                                score = float(row.get('sentiment_score', 0))
                                color = "#EF4444" if score < -0.3 else "#10B981" if score > 0.3 else "#F59E0B"
                                c2.metric("AI Score", f"{score:.2f}")
                                c2.markdown(f"<div style='height:8px; width:100%; background:{color}; border-radius:4px;'></div>", unsafe_allow_html=True)
            current_tab_index += 1

        # --- TAB 6: HOTEL ENGINE (PREDICTIVE UPGRADE) ---
        if "Hotel Premium" in active_modules:
            with tabs[current_tab_index]:
                st.markdown("### 🏨 Hotel Revenue Engine")
                with st.expander("✍️ Log Daily Hotel Ledger", expanded=not has_data):
                    with st.form("hotel_entry_form"):
                        entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_hot")
                        hc1, hc2 = st.columns(2)
                        m_rooms = hc1.number_input("Rooms Sold", min_value=0, step=1)
                        m_adr = hc2.number_input("Average Daily Rate (ADR $)", min_value=0.0, step=10.0)
                        if st.form_submit_button("Save Hotel Data", type="primary", use_container_width=True): save_daily_log(entry_date, {"rooms_sold": m_rooms, "adr": m_adr})

                st.divider()
                TOTAL_ROOMS = st.number_input("⚙️ Total Available Rooms Base", value=300, step=50)
                
                if has_data and 'rooms_sold' in df_perf.columns:
                    df_hotel = df_perf[df_perf['rooms_sold'] > 0].copy()
                    if not df_hotel.empty:
                        df_hotel['occupancy'] = (df_hotel['rooms_sold'] / TOTAL_ROOMS) * 100
                        avg_occ = df_hotel['occupancy'].mean()
                        avg_adr = df_hotel['adr'].mean()
                        st.markdown("#### 📈 Historical Yield Physics")
                        h1, h2, h3 = st.columns(3)
                        h1.metric("Average Occupancy", f"{avg_occ:.1f}%")
                        h2.metric("Average ADR", f"${avg_adr:.2f}")
                        h3.metric("Calculated RevPAR", f"${(avg_adr * (avg_occ/100)):.2f}")
                        
                        if not df_forward.empty:
                            st.markdown("#### 🔮 14-Day Predictive Hotel Occupancy")
                            st.caption("Forecasted room demand based on projected casino floor gravity and custom calibrations.")
                            df_hotel_fwd = df_forward.copy()
                            df_hotel_fwd['predicted_rooms'] = df_hotel_fwd['predicted_traffic'] * (cals['hotel_capture_pct'] / 100)
                            df_hotel_fwd['predicted_occ'] = (df_hotel_fwd['predicted_rooms'] / TOTAL_ROOMS) * 100
                            
                            fig_hotel_fwd = px.bar(df_hotel_fwd, x='record_date', y='predicted_occ', text_auto='.1f', title="Forecasted Occupancy %")
                            fig_hotel_fwd.update_traces(marker_color='#2563EB', textposition='outside')
                            fig_hotel_fwd.update_layout(height=350, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
                            st.plotly_chart(fig_hotel_fwd, use_container_width=True)
            current_tab_index += 1

        # --- TAB 7: F&B ENGINE (PREDICTIVE UPGRADE) ---
        if "F&B Premium" in active_modules:
            with tabs[current_tab_index]:
                st.markdown("### 🍔 F&B Operational Engine")
                with st.expander("✍️ Log Daily F&B Ledger", expanded=not has_data):
                    with st.form("fb_entry_form"):
                        entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_fb")
                        fc1, fc2 = st.columns(2)
                        m_covers = fc1.number_input("Total Covers", min_value=0, step=1)
                        m_fbrev = fc2.number_input("Gross F&B Revenue ($)", min_value=0.0, step=500.0)
                        if st.form_submit_button("Save F&B Data", type="primary", use_container_width=True): save_daily_log(entry_date, {"fb_covers": m_covers, "fb_revenue": m_fbrev})

                st.divider()
                if has_data and 'fb_covers' in df_perf.columns and 'actual_traffic' in df_perf.columns:
                    df_fb = df_perf[df_perf['fb_covers'] > 0].copy()
                    if not df_fb.empty:
                        capture_rate = (df_fb['fb_covers'].sum() / df_fb['actual_traffic'].sum() * 100)
                        avg_check = df_fb['fb_revenue'].sum() / df_fb['fb_covers'].sum()
                        
                        st.markdown("#### 🔄 The 'Halo Effect' (Traffic to Covers Matrix)")
                        f1, f2, f3 = st.columns(3)
                        f1.metric("Average Check", f"${avg_check:.2f}")
                        f2.metric("Casino Capture Rate", f"{capture_rate:.1f}%")
                        f3.metric("Total Covers Logged", f"{df_fb['fb_covers'].sum():,.0f}")
                        
                        if not df_forward.empty:
                            st.markdown("#### 🔮 14-Day Predictive Kitchen Demand")
                            st.caption("Forecasted restaurant covers based on upcoming projected casino footfall and custom calibrations.")
                            df_fb_fwd = df_forward.copy()
                            df_fb_fwd['predicted_covers'] = df_fb_fwd['predicted_traffic'] * (cals['fb_capture_pct'] / 100)
                            
                            fig_fb_fwd = px.line(df_fb_fwd, x='record_date', y='predicted_covers', markers=True, title="Forecasted F&B Covers")
                            fig_fb_fwd.update_traces(line=dict(color='#F59E0B', width=3))
                            fig_fb_fwd.update_layout(height=350, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
                            st.plotly_chart(fig_fb_fwd, use_container_width=True)
            current_tab_index += 1

        # --- TAB 8: ENTERTAINMENT ENGINE ---
        if "Entertainment Premium" in active_modules:
            with tabs[current_tab_index]:
                st.markdown("### 🎫 Entertainment Engine")
                with st.expander("✍️ Log Daily Entertainment Ledger", expanded=not has_data):
                    with st.form("ent_entry_form"):
                        entry_date = st.date_input("Reporting Date", value=date.today() - timedelta(days=1), key="d_ent")
                        ec1, ec2 = st.columns(2)
                        m_tix = ec1.number_input("Tickets Scanned", min_value=0, step=1)
                        m_entrev = ec2.number_input("Box Office Revenue ($)", min_value=0.0, step=500.0)
                        if st.form_submit_button("Save Entertainment Data", type="primary", use_container_width=True): save_daily_log(entry_date, {"tickets_sold": m_tix, "ent_revenue": m_entrev})

                st.divider()
                if has_data and 'tickets_sold' in df_perf.columns:
                    df_ent = df_perf[df_perf['tickets_sold'] > 0].copy()
                    if not df_ent.empty:
                        df_no_ent = df_perf[df_perf['tickets_sold'] <= 0]
                        avg_coin_event = df_ent['coin_in'].mean()
                        avg_coin_no_event = df_no_ent['coin_in'].mean() if not df_no_ent.empty else 0
                        indirect_lift = avg_coin_event - avg_coin_no_event
                        
                        st.markdown("#### 🎸 Historical Event Lift Matrix")
                        e1, e2, e3 = st.columns(3)
                        e1.metric("Average Box Office", f"${df_ent['ent_revenue'].mean():,.0f}")
                        e2.metric("Average Tickets Scanned", f"{df_ent['tickets_sold'].mean():,.0f}")
                        e3.metric("Indirect Floor Lift (Avg)", f"${indirect_lift:,.0f}")
                        
                        fig_ent = go.Figure()
                        fig_ent.add_trace(go.Bar(x=['Non-Event Day Avg', 'Event Day Avg'], y=[avg_coin_no_event, avg_coin_event], marker_color=['#94A3B8', '#10B981']))
                        fig_ent.update_layout(title="Casino Coin-In Impact Comparison", height=350, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
                        st.plotly_chart(fig_ent, use_container_width=True)
            current_tab_index += 1

        # --- TAB 9: SETTINGS (WITH CALIBRATION UI) ---
        with tabs[-1]:
            st.markdown("### ⚙️ Account Management & Settings")
            
            with st.expander("🎛️ AI Predictive Calibration Engine", expanded=True):
                st.caption("Adjust the specific coefficients the AI uses to forecast your property's performance.")
                with st.form("calibration_form"):
                    cal_tabs = st.tabs(["🎰 Casino & Traffic", "🏨 Hotel Engine", "🍔 F&B Engine"])
                    with cal_tabs[0]:
                        st.markdown("##### Base Traffic by Day")
                        b1, b2, b3, b4 = st.columns(4)
                        new_mon = b1.number_input("Monday", value=float(cals['mon_base']), step=100.0)
                        new_tue = b2.number_input("Tuesday", value=float(cals['tue_base']), step=100.0)
                        new_wed = b3.number_input("Wednesday", value=float(cals['wed_base']), step=100.0)
                        new_thu = b4.number_input("Thursday", value=float(cals['thu_base']), step=100.0)
                        b5, b6, b7, _ = st.columns(4)
                        new_fri = b5.number_input("Friday", value=float(cals['fri_base']), step=100.0)
                        new_sat = b6.number_input("Saturday", value=float(cals['sat_base']), step=100.0)
                        new_sun = b7.number_input("Sunday", value=float(cals['sun_base']), step=100.0)
                        st.markdown("##### Spend & Environment")
                        e1, e2, e3 = st.columns(3)
                        new_coin = e1.number_input("Avg Coin-In / Guest ($)", value=float(cals['avg_coin_in']), step=5.0)
                        new_drop = e2.number_input("Avg Table Drop / Guest ($)", value=float(cals['avg_table_drop']), step=5.0)
                        new_rain = e3.number_input("Rain Penalty (Per mm)", value=float(cals['rain_penalty']), step=1.0)
                    with cal_tabs[1]:
                        st.markdown("##### Hotel Integration")
                        h1, h2 = st.columns(2)
                        new_h_cap = h1.number_input("Casino Traffic Capture Rate (%)", value=float(cals['hotel_capture_pct']), step=0.5)
                        new_h_adr = h2.number_input("Base ADR ($)", value=float(cals['hotel_base_adr']), step=5.0)
                    with cal_tabs[2]:
                        st.markdown("##### F&B Integration")
                        f1, f2 = st.columns(2)
                        new_fb_cap = f1.number_input("Dining Capture Rate (%)", value=float(cals['fb_capture_pct']), step=1.0)
                        new_fb_check = f2.number_input("Average Check ($)", value=float(cals['fb_avg_check']), step=1.0)

                    if st.form_submit_button("💾 Save Calibrations to Vault", type="primary", use_container_width=True):
                        updated_cals = cals.copy()
                        updated_cals.update({
                            'mon_base': new_mon, 'tue_base': new_tue, 'wed_base': new_wed, 'thu_base': new_thu,
                            'fri_base': new_fri, 'sat_base': new_sat, 'sun_base': new_sun,
                            'avg_coin_in': new_coin, 'avg_table_drop': new_drop, 'rain_penalty': new_rain,
                            'hotel_capture_pct': new_h_cap, 'hotel_base_adr': new_h_adr,
                            'fb_capture_pct': new_fb_cap, 'fb_avg_check': new_fb_check
                        })
                        if save_property_calibrations(comp_id, updated_cals):
                            st.rerun()

            with st.expander("💳 Billing & Active Subscriptions", expanded=False):
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    st.markdown("##### Your Active Modules")
                    if active_subs_details: st.dataframe(pd.DataFrame(active_subs_details), use_container_width=True, hide_index=True)
                with b_col2:
                    st.markdown("##### Account Balance")
                    st.markdown(f"<h3 style='margin:0; color:{'#EF4444' if comp_owed > 0 else '#10B981'};'>${comp_owed:,.2f}</h3>", unsafe_allow_html=True)
            with st.expander("📂 Master Ledger Database & Bulk Upload"):
                t_data, t_csv = st.tabs(["📋 View Raw Database", "📥 Bulk CSV Upload"])
                with t_data:
                    if has_data: st.dataframe(df_perf, use_container_width=True, hide_index=True)
                with t_csv:
                    st.caption("Accepted columns: `date`, `coin_in`, `table_drop`, `marketing_spend`, `actual_traffic`, `new_members`, `attendance`, `ad_clicks`, `ad_impressions`, `active_promo`, `experiment_tag`, `rain_mm`, `snow_cm`, `rooms_sold`, `adr`, `fb_covers`, `fb_revenue`, `tickets_sold`, `ent_revenue`")
                    with st.form("bulk_upload_form"):
                        dash_file = st.file_uploader("Drop CSV", type=["csv"], label_visibility="collapsed")
                        if st.form_submit_button("Process Data", type="primary") and dash_file:
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
