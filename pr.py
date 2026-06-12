# pr.py
import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go

def render_pr_module(supabase, tenant_id, property_name):
    st.title("📢 PR Scorecard")
    st.write(f"Earned Media & Brand Authority tracking for **{property_name}**.")

    # --- 1. DATA ENTRY MODAL ---
    with st.expander("📝 Log Monthly PR Metrics", expanded=False):
        with st.form("pr_entry_form", clear_on_submit=True):
            today_pr = datetime.date.today()
            f1, f2, f3 = st.columns(3)
            with f1: m_date = st.date_input("Report Month", value=today_pr.replace(day=1))
            with f2: m_imp = st.number_input("Earned Impressions", min_value=0, step=1000)
            with f3: m_ment = st.number_input("Earned Mentions", min_value=0, step=1)
            
            m_mediums = st.text_input("Primary Mediums (e.g., CTV News, Local Radio)")
            m_comment = st.text_area("Executive Summary & Narrative")
            
            if st.form_submit_button("Vault PR Entry", use_container_width=True):
                entry = {
                    "tenant_id": tenant_id,
                    "report_month": m_date.strftime("%Y-%m-%d"),
                    "earned_impressions": m_imp,
                    "earned_mentions": m_ment,
                    "mediums": m_mediums,
                    "executive_summary": m_comment
                }
                try:
                    supabase.table("mt_pr_scorecard").upsert(entry, on_conflict="tenant_id, report_month").execute()
                    st.success(f"PR Metrics for {m_date.strftime('%B %Y')} Vaulted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving PR data: {e}")

    # --- 2. DATA RETRIEVAL ---
    pr_res = supabase.table("mt_pr_scorecard").select("*").eq("tenant_id", tenant_id).order("report_month", desc=True).execute()
    
    if not pr_res.data:
        st.info("The PR Scorecard vault is empty. Log your first month above to unlock analytics.")
        return

    df_pr = pd.DataFrame(pr_res.data)
    df_pr['report_month'] = pd.to_datetime(df_pr['report_month'])
    
    curr = df_pr.iloc[0]
    prev = df_pr.iloc[1] if len(df_pr) > 1 else curr

    # --- 3. METRIC CARDS ---
    st.markdown("### 📊 Performance against MoM Baseline")
    k1, k2 = st.columns(2)
    imp_mom_pct = ((curr['earned_impressions'] - prev['earned_impressions']) / prev['earned_impressions'] * 100) if prev['earned_impressions'] > 0 else 0
    k1.metric("Earned Media Impressions", f"{curr['earned_impressions']:,}", delta=f"{imp_mom_pct:+.1f}% MoM")

    ment_mom_pct = ((curr['earned_mentions'] - prev['earned_mentions']) / prev['earned_mentions'] * 100) if prev['earned_mentions'] > 0 else 0
    k2.metric("Earned Media Mentions", f"{curr['earned_mentions']}", delta=f"{ment_mom_pct:+.1f}% MoM")

    # --- 4. VISUAL TREND ---
    st.write("### 📈 Earned Media Traction Trend")
    fig_pr = go.Figure()
    df_chart = df_pr.sort_values('report_month')
    fig_pr.add_trace(go.Scatter(x=df_chart['report_month'], y=df_chart['earned_impressions'], name="Impressions", line=dict(color='#FFCC00', width=4), yaxis="y"))
    fig_pr.add_trace(go.Bar(x=df_chart['report_month'], y=df_chart['earned_mentions'], name="Mentions", marker_color='rgba(255, 255, 255, 0.2)', yaxis="y2"))
    
    fig_pr.update_layout(
        template="plotly_dark", 
        yaxis=dict(title="Impressions", showgrid=False), 
        yaxis2=dict(title="Mentions", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), 
        margin=dict(l=10, r=10, t=30, b=10), height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_pr, use_container_width=True)

    # --- 5. NARRATIVE ARCHIVE ---
    st.write("### 📜 Monthly PR Narrative Archive")
    for index, row in df_pr.iterrows():
        date_label = row['report_month'].strftime('%B %Y')
        with st.expander(f"Audit: {date_label} — {row['mediums']}", expanded=(index==0)):
            st.markdown(f"**Earned Reach:** {row['earned_impressions']:,} impressions across {row['earned_mentions']} placements.")
            st.info(row['executive_summary'] if row['executive_summary'] else "No summary vaulted for this period.")
            
            if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                supabase.table("mt_pr_scorecard").delete().eq("id", row['id']).execute()
                st.rerun()
