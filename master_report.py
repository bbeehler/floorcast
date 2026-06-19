# master_report.py
import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import json

def fetch_module_data(supabase, tenant_id, start_date, end_date):
    """Fetches all operational data across modules for the selected window."""
    data = {}
    
    # 1. Casino / Ledger
    res_casino = supabase.table("mt_ledger").select("*").eq("tenant_id", tenant_id).gte("entry_date", str(start_date)).lte("entry_date", str(end_date)).execute()
    data['casino'] = pd.DataFrame(res_casino.data) if res_casino.data else pd.DataFrame()
    if not data['casino'].empty: data['casino']['date'] = pd.to_datetime(data['casino']['entry_date'])

    # 2. F&B
    res_fnb = supabase.table("mt_fnb_ledger").select("*").eq("tenant_id", tenant_id).gte("audit_date", str(start_date)).lte("audit_date", str(end_date)).execute()
    data['fnb'] = pd.DataFrame(res_fnb.data) if res_fnb.data else pd.DataFrame()
    if not data['fnb'].empty: data['fnb']['date'] = pd.to_datetime(data['fnb']['audit_date'])

    # 3. Hotel
    res_hotel = supabase.table("mt_hotel_ledger").select("*").eq("tenant_id", tenant_id).gte("audit_date", str(start_date)).lte("audit_date", str(end_date)).execute()
    data['hotel'] = pd.DataFrame(res_hotel.data) if res_hotel.data else pd.DataFrame()
    if not data['hotel'].empty: data['hotel']['date'] = pd.to_datetime(data['hotel']['audit_date'])

    # 4. Sentiment
    res_sent = supabase.table("mt_sentiment_history").select("*").eq("tenant_id", tenant_id).gte("timestamp", f"{start_date}T00:00:00").lte("timestamp", f"{end_date}T23:59:59").execute()
    data['sentiment'] = pd.DataFrame(res_sent.data) if res_sent.data else pd.DataFrame()
    if not data['sentiment'].empty: data['sentiment']['date'] = pd.to_datetime(data['sentiment']['timestamp']).dt.normalize()

    return data

def render_master_report_module(supabase, tenant_id, property_name):
    st.markdown(f"<h2 style='color: #111827; margin-bottom: 1rem;'>📊 Master Report Builder</h2>", unsafe_allow_html=True)

    # --- 1. LOAD SAVED TEMPLATES ---
    res_templates = supabase.table("mt_saved_reports").select("*").eq("tenant_id", tenant_id).order("created_at", desc=True).execute()
    saved_reports = {row['report_name']: row for row in res_templates.data} if res_templates.data else {}

    col_load, _ = st.columns([1, 2])
    with col_load:
        if saved_reports:
            template_options = ["-- Build New Custom Report --"] + list(saved_reports.keys())
            selected_template = st.selectbox("Load Saved Template:", template_options)
        else:
            selected_template = "-- Build New Custom Report --"
            st.selectbox("Load Saved Template:", [selected_template], disabled=True)

    # Apply template config if selected
    active_config = {"metrics": [], "charts": []}
    if selected_template != "-- Build New Custom Report --":
        active_config = saved_reports[selected_template]['config']

    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    # --- 2. REPORT CONFIGURATOR ---
    st.markdown("<h4 style='color: #111827;'>1. Define Parameters</h4>", unsafe_allow_html=True)
    
    c_date, c_metrics, c_charts = st.columns([1, 1.5, 1.5])
    
    with c_date:
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=30)
        audit_window = st.date_input("Audit Window", value=(default_start, today))
    
    available_metrics = [
        "Gaming Revenue", "Casino Traffic", "New Signups", 
        "F&B Revenue", "F&B Covers", 
        "Hotel Revenue", "Rooms Sold", 
        "Average Sentiment Score"
    ]
    
    with c_metrics:
        selected_metrics = st.multiselect(
            "Select KPI Cards to Display", 
            available_metrics, 
            default=active_config.get("metrics", ["Gaming Revenue", "F&B Revenue", "Hotel Revenue"])
        )
        
    with c_charts:
        selected_charts = st.multiselect(
            "Select Data Streams to Chart", 
            available_metrics, 
            default=active_config.get("charts", ["Gaming Revenue"])
        )

    # Save Template Form
    with st.expander("💾 Save this Configuration as a Template"):
        with st.form("save_template_form", border=False):
            t_name = st.text_input("Template Name", placeholder="e.g., Weekly Executive Brief")
            if st.form_submit_button("Save Template", use_container_width=True):
                if t_name:
                    payload = {
                        "tenant_id": tenant_id,
                        "report_name": t_name,
                        "config": {"metrics": selected_metrics, "charts": selected_charts}
                    }
                    supabase.table("mt_saved_reports").insert(payload).execute()
                    st.success(f"Template '{t_name}' saved.")
                    st.rerun()

    st.markdown("<hr style='margin: 1rem 0 2rem 0;'>", unsafe_allow_html=True)

    # --- 3. RENDER REPORT ---
    if isinstance(audit_window, tuple) and len(audit_window) == 2:
        start_date, end_date = audit_window
        data = fetch_module_data(supabase, tenant_id, start_date, end_date)

        # Dictionary to map selections to actual math
        kpi_math = {}
        if not data['casino'].empty:
            kpi_math["Gaming Revenue"] = (data['casino']['actual_coin_in'].sum(), "$", "")
            kpi_math["Casino Traffic"] = (data['casino']['actual_traffic'].sum(), "", "")
            kpi_math["New Signups"] = (data['casino']['new_members'].sum(), "", "")
        
        if not data['fnb'].empty:
            kpi_math["F&B Revenue"] = (data['fnb']['total_revenue'].sum(), "$", "")
            kpi_math["F&B Covers"] = (data['fnb']['total_covers'].sum(), "", "")
            
        if not data['hotel'].empty:
            kpi_math["Hotel Revenue"] = (data['hotel']['room_revenue'].sum(), "$", "")
            kpi_math["Rooms Sold"] = (data['hotel']['rooms_sold'].sum(), "", "")
            
        if not data['sentiment'].empty:
            avg_score = data['sentiment']['sentiment_score'].astype(float).mean()
            kpi_math["Average Sentiment Score"] = (avg_score, "", " / 1.0")

        # RENDER KPI CARDS
        if selected_metrics:
            st.markdown("<h4 style='color: #111827; margin-bottom: 1rem;'>Executive KPIs</h4>", unsafe_allow_html=True)
            
            # Dynamically create rows of 4 cards
            cols = st.columns(4)
            for i, metric in enumerate(selected_metrics):
                col = cols[i % 4]
                val, prefix, suffix = kpi_math.get(metric, (0, "", ""))
                
                # Format smartly based on if it's currency, float, or integer
                if prefix == "$":
                    formatted_val = f"{prefix}{val:,.0f}{suffix}"
                elif metric == "Average Sentiment Score":
                    formatted_val = f"{prefix}{val:+.2f}{suffix}"
                else:
                    formatted_val = f"{prefix}{val:,.0f}{suffix}"

                with col:
                    st.markdown(f"""
                    <div class="bento-card" style="margin-bottom: 1rem;">
                        <p style="color: #6B7280; margin: 0; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">{metric}</p>
                        <h2 style="color: #111827; margin: 0.5rem 0; font-size: 2rem;">{formatted_val}</h2>
                    </div>
                    """, unsafe_allow_html=True)

        # RENDER UNIFIED TIMELINE CHART
        if selected_charts:
            st.markdown("<h4 style='color: #111827; margin-top: 2rem; margin-bottom: 1rem;'>Unified Timeline</h4>", unsafe_allow_html=True)
            
            fig = go.Figure()
            colors = ['#2563EB', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#6366F1', '#EC4899']
            
            # Map chart selections to the respective dataframes
            chart_mapping = {
                "Gaming Revenue": (data['casino'], 'actual_coin_in'),
                "Casino Traffic": (data['casino'], 'actual_traffic'),
                "New Signups": (data['casino'], 'new_members'),
                "F&B Revenue": (data['fnb'], 'total_revenue'),
                "F&B Covers": (data['fnb'], 'total_covers'),
                "Hotel Revenue": (data['hotel'], 'room_revenue'),
                "Rooms Sold": (data['hotel'], 'rooms_sold'),
            }

            for i, chart_metric in enumerate(selected_charts):
                if chart_metric in chart_mapping:
                    df_target, col_target = chart_mapping[chart_metric]
                    if not df_target.empty:
                        # Group by date in case of multiple entries per day
                        df_grouped = df_target.groupby('date')[col_target].sum().reset_index()
                        
                        # Plot on secondary Y axis if it's revenue vs volume to prevent squashing
                        is_currency = "Revenue" in chart_metric
                        
                        fig.add_trace(go.Scatter(
                            x=df_grouped['date'], 
                            y=df_grouped[col_target], 
                            name=chart_metric,
                            yaxis="y1" if is_currency else "y2",
                            line=dict(width=3, color=colors[i % len(colors)])
                        ))

            fig.update_layout(
                height=450, 
                margin=dict(l=0, r=0, t=10, b=0), 
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#F3F4F6', title="Revenue ($)"),
                yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Volume (Count)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.markdown('<div class="bento-card" style="padding-top: 1rem;">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
            
    else:
        st.info("Select a valid date range to build the report.")
