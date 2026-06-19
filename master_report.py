# master_report.py
import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import json

def fetch_module_data(supabase, tenant_id, start_date, end_date):
    """Fetches all operational and marketing data across modules for the selected window."""
    data = {}
    
    # 1. Casino / Ledger (Includes Marketing Ad data & AI Predictions)
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

    # 5. Email Ops
    res_email = supabase.table("mt_email_ledger").select("*").eq("tenant_id", tenant_id).gte("audit_date", str(start_date)).lte("audit_date", str(end_date)).execute()
    data['email'] = pd.DataFrame(res_email.data) if res_email.data else pd.DataFrame()
    if not data['email'].empty: data['email']['date'] = pd.to_datetime(data['email']['audit_date'])

    # 6. PR & Earned Media
    res_pr = supabase.table("mt_pr_ledger").select("*").eq("tenant_id", tenant_id).gte("audit_date", str(start_date)).lte("audit_date", str(end_date)).execute()
    data['pr'] = pd.DataFrame(res_pr.data) if res_pr.data else pd.DataFrame()
    if not data['pr'].empty: data['pr']['date'] = pd.to_datetime(data['pr']['audit_date'])

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
    active_config = {"metrics": [], "charts": [], "chart_type": "Line"}
    if selected_template != "-- Build New Custom Report --":
        active_config = saved_reports[selected_template]['config']

    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    # --- 2. REPORT CONFIGURATOR ---
    st.markdown("<h4 style='color: #111827;'>1. Define Parameters</h4>", unsafe_allow_html=True)
    
    c_date, c_metrics, c_charts, c_type = st.columns([1, 1.5, 1.5, 1])
    
    with c_date:
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=30)
        audit_window = st.date_input("Audit Window", value=(default_start, today))
    
    available_metrics = [
        "Gaming Revenue", "Casino Traffic", "New Signups", 
        "F&B Revenue", "F&B Covers", 
        "Hotel Revenue", "Rooms Sold", 
        "Average Sentiment Score",
        "Digital Ad Clicks", "Social Reach", "AI Prediction Accuracy",
        "Email Volume Sent", "Email Open Rate", "Email CTR",
        "PR Earned Impressions", "PR Media Value"
    ]
    
    chartable_streams = [
        "Gaming Revenue", "Casino Traffic", "New Signups", "F&B Revenue", "F&B Covers", 
        "Hotel Revenue", "Rooms Sold", "Digital Ad Clicks", "Social Reach",
        "Channel Attribution Flow" # <--- The Special Sankey Option
    ]

    with c_metrics:
        selected_metrics = st.multiselect(
            "Select KPI Cards to Display", 
            available_metrics, 
            default=active_config.get("metrics", ["Gaming Revenue", "Casino Traffic", "Digital Ad Clicks", "AI Prediction Accuracy"])
        )
        
    with c_charts:
        selected_charts = st.multiselect(
            "Select Data Streams to Chart", 
            chartable_streams, 
            default=active_config.get("charts", ["Gaming Revenue", "Channel Attribution Flow"])
        )
        
    with c_type:
        chart_style = st.selectbox(
            "Visualization Style", 
            ["Line", "Bar", "Area Fill"], 
            index=["Line", "Bar", "Area Fill"].index(active_config.get("chart_type", "Line"))
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
                        "config": {"metrics": selected_metrics, "charts": selected_charts, "chart_type": chart_style}
                    }
                    supabase.table("mt_saved_reports").insert(payload).execute()
                    st.success(f"Template '{t_name}' saved.")
                    st.rerun()

    st.markdown("<hr style='margin: 1rem 0 2rem 0;'>", unsafe_allow_html=True)

    # --- 3. RENDER REPORT ---
    if isinstance(audit_window, tuple) and len(audit_window) == 2:
        start_date, end_date = audit_window
        data = fetch_module_data(supabase, tenant_id, start_date, end_date)

        # Dictionary to map selections to actual math safely
        kpi_math = {}
        
        # Casino / AI / Marketing
        if not data['casino'].empty:
            kpi_math["Gaming Revenue"] = (data['casino']['actual_coin_in'].sum(), "$", "")
            kpi_math["Casino Traffic"] = (data['casino']['actual_traffic'].sum(), "", "")
            kpi_math["New Signups"] = (data['casino']['new_members'].sum(), "", "")
            
            ad_clicks = data['casino'].get('ad_clicks', pd.Series([0])).sum()
            kpi_math["Digital Ad Clicks"] = (ad_clicks, "", "")
            kpi_math["Social Reach"] = (data['casino'].get('ad_impressions', pd.Series([0])).sum(), "", "")

            # AI Accuracy Math (1 - (abs(actual - expected) / actual))
            if 'predicted_traffic' in data['casino'].columns:
                valid_preds = data['casino'].dropna(subset=['predicted_traffic', 'actual_traffic'])
                if not valid_preds.empty and valid_preds['actual_traffic'].sum() > 0:
                    variance = abs(valid_preds['actual_traffic'] - valid_preds['predicted_traffic']) / valid_preds['actual_traffic']
                    avg_acc = (1 - variance.mean()) * 100
                    kpi_math["AI Prediction Accuracy"] = (max(0, min(100, avg_acc)), "", "%")
                else: kpi_math["AI Prediction Accuracy"] = (0, "", "%")
        
        # F&B
        if not data['fnb'].empty:
            kpi_math["F&B Revenue"] = (data['fnb'].get('total_revenue', pd.Series([0])).sum(), "$", "")
            kpi_math["F&B Covers"] = (data['fnb'].get('total_covers', pd.Series([0])).sum(), "", "")
            
        # Hotel
        if not data['hotel'].empty:
            kpi_math["Hotel Revenue"] = (data['hotel'].get('room_revenue', pd.Series([0])).sum(), "$", "")
            kpi_math["Rooms Sold"] = (data['hotel'].get('rooms_sold', pd.Series([0])).sum(), "", "")
            
        # Sentiment
        if not data['sentiment'].empty:
            avg_score = data['sentiment']['sentiment_score'].astype(float).mean()
            kpi_math["Average Sentiment Score"] = (avg_score, "", " / 1.0")
            
        # Email Ops
        if not data['email'].empty:
            sent = data['email'].get('emails_sent', pd.Series([0])).sum()
            opens = data['email'].get('emails_opened', pd.Series([0])).sum()
            clicks = data['email'].get('emails_clicked', pd.Series([0])).sum()
            kpi_math["Email Volume Sent"] = (sent, "", "")
            kpi_math["Email Open Rate"] = ((opens / sent) * 100 if sent > 0 else 0, "", "%")
            kpi_math["Email CTR"] = ((clicks / opens) * 100 if opens > 0 else 0, "", "%")
            
        # PR
        if not data['pr'].empty:
            kpi_math["PR Earned Impressions"] = (data['pr'].get('earned_impressions', pd.Series([0])).sum(), "", "")
            kpi_math["PR Media Value"] = (data['pr'].get('media_value', pd.Series([0])).sum(), "$", "")

        # --- RENDER KPI CARDS ---
        if selected_metrics:
            st.markdown("<h4 style='color: #111827; margin-bottom: 1rem;'>Executive KPIs</h4>", unsafe_allow_html=True)
            
            cols = st.columns(4)
            for i, metric in enumerate(selected_metrics):
                col = cols[i % 4]
                val, prefix, suffix = kpi_math.get(metric, (0, "", ""))
                
                # Format smartly based on if it's currency, float, or percentage
                if suffix == "%":
                    formatted_val = f"{val:.1f}{suffix}"
                elif metric == "Average Sentiment Score":
                    formatted_val = f"{prefix}{val:+.2f}{suffix}"
                elif prefix == "$":
                    formatted_val = f"{prefix}{val:,.0f}{suffix}"
                else:
                    formatted_val = f"{val:,.0f}"

                # Add color to specific high-value metrics
                text_color = "#111827"
                if "Accuracy" in metric and val > 90: text_color = "#10B981"
                elif "Accuracy" in metric and val < 85: text_color = "#EF4444"

                with col:
                    st.markdown(f"""
                    <div class="bento-card" style="margin-bottom: 1rem;">
                        <p style="color: #6B7280; margin: 0; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">{metric}</p>
                        <h2 style="color: {text_color}; margin: 0.5rem 0; font-size: 2rem;">{formatted_val}</h2>
                    </div>
                    """, unsafe_allow_html=True)

        # --- RENDER UNIFIED TIMELINE CHART ---
        if selected_charts:
            st.markdown("<h4 style='color: #111827; margin-top: 2rem; margin-bottom: 1rem;'>Visual Intelligence</h4>", unsafe_allow_html=True)
            
            # 1. Standard Timeline Rendering
            standard_charts = [c for c in selected_charts if c != "Channel Attribution Flow"]
            
            if standard_charts:
                fig = go.Figure()
                colors = ['#2563EB', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#6366F1', '#EC4899']
                
                chart_mapping = {
                    "Gaming Revenue": (data['casino'], 'actual_coin_in'),
                    "Casino Traffic": (data['casino'], 'actual_traffic'),
                    "New Signups": (data['casino'], 'new_members'),
                    "Digital Ad Clicks": (data['casino'], 'ad_clicks'),
                    "Social Reach": (data['casino'], 'ad_impressions'),
                    "F&B Revenue": (data['fnb'], 'total_revenue'),
                    "F&B Covers": (data['fnb'], 'total_covers'),
                    "Hotel Revenue": (data['hotel'], 'room_revenue'),
                    "Rooms Sold": (data['hotel'], 'rooms_sold'),
                }

                for i, chart_metric in enumerate(standard_charts):
                    if chart_metric in chart_mapping:
                        df_target, col_target = chart_mapping[chart_metric]
                        if not df_target.empty and col_target in df_target.columns:
                            df_grouped = df_target.groupby('date')[col_target].sum().reset_index()
                            is_currency = "Revenue" in chart_metric
                            y_axis = "y1" if is_currency else "y2"
                            trace_color = colors[i % len(colors)]
                            
                            if chart_style == "Bar":
                                fig.add_trace(go.Bar(x=df_grouped['date'], y=df_grouped[col_target], name=chart_metric, yaxis=y_axis, marker_color=trace_color))
                            elif chart_style == "Area Fill":
                                fig.add_trace(go.Scatter(x=df_grouped['date'], y=df_grouped[col_target], name=chart_metric, yaxis=y_axis, fill='tozeroy', line=dict(color=trace_color, width=2)))
                            else:
                                fig.add_trace(go.Scatter(x=df_grouped['date'], y=df_grouped[col_target], name=chart_metric, yaxis=y_axis, line=dict(width=3, color=trace_color)))

                barmode = 'group' if chart_style == "Bar" else 'overlay'
                fig.update_layout(
                    barmode=barmode,
                    height=400, 
                    margin=dict(l=0, r=0, t=10, b=0), 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='#F3F4F6'),
                    yaxis2=dict(overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.markdown('<div class="bento-card" style="padding-top: 1rem;">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)

            # 2. Advanced Sankey "Attribution Flow" Rendering
            if "Channel Attribution Flow" in selected_charts:
                st.markdown("<h5 style='color: #4B5563; margin-top: 2rem;'>Customer Journey Flow (Attribution)</h5>", unsafe_allow_html=True)
                
                # Fetch baseline values
                ad_clicks_total = data['casino'].get('ad_clicks', pd.Series([0])).sum() if not data['casino'].empty else 0
                social_imps_total = data['casino'].get('ad_impressions', pd.Series([0])).sum() if not data['casino'].empty else 0
                pr_imps_total = data['pr'].get('earned_impressions', pd.Series([0])).sum() if not data['pr'].empty else 0
                actual_traffic = data['casino'].get('actual_traffic', pd.Series([0])).sum() if not data['casino'].empty else 0
                actual_rev = data['casino'].get('actual_coin_in', pd.Series([0])).sum() if not data['casino'].empty else 0
                
                # Apply simulated weight conversions for the visual flow
                # (Normally this pulls directly from your MTA engine)
                digital_traffic = int(ad_clicks_total * 0.05)
                social_traffic = int(social_imps_total * 0.0002)
                pr_traffic = int(pr_imps_total * 0.0001)
                organic_traffic = max(0, actual_traffic - (digital_traffic + social_traffic + pr_traffic))

                # Node indices: 0:Organic, 1:Digital Ads, 2:Social, 3:PR/Earned, 4:Total Foot Traffic, 5:Gaming Revenue
                fig_sankey = go.Figure(data=[go.Sankey(
                    node = dict(
                        pad = 15, thickness = 20,
                        line = dict(color = "black", width = 0.5),
                        label = ["Organic Brand Base", "Digital Search/Ads", "Social Media", "PR / Earned Media", "Total Property Traffic", "Gaming Revenue"],
                        color = ["#9CA3AF", "#2563EB", "#8B5CF6", "#10B981", "#111827", "#F59E0B"]
                    ),
                    link = dict(
                        source = [0, 1, 2, 3, 4], # Organic, Digital, Social, PR -> Traffic -> Revenue
                        target = [4, 4, 4, 4, 5],
                        value = [organic_traffic, digital_traffic, social_traffic, pr_traffic, actual_rev]
                    )
                )])

                fig_sankey.update_layout(height=450, font_size=12, margin=dict(l=0, r=0, t=10, b=10))
                
                st.markdown('<div class="bento-card" style="padding-top: 1rem;">', unsafe_allow_html=True)
                if actual_traffic == 0:
                    st.info("Insufficient data to build the Attribution Flow model.")
                else:
                    st.plotly_chart(fig_sankey, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
                
    else:
        st.info("Select a valid date range to build the report.")
