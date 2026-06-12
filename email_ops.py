# email_ops.py
import streamlit as st
import pandas as pd
import datetime

def render_email_module(supabase, tenant_id, property_name):
    st.title("📨 Email Analytics")
    st.write(f"Campaign distribution and engagement tracking for **{property_name}**.")

    tabs = st.tabs(["📊 Performance Audit", "📥 Automated Ingestion"])

    # --- TAB 1: EXECUTIVE DASHBOARD ---
    with tabs[0]:
        st.subheader("Monthly Performance Matrix")
        
        # Get all available months for this tenant
        dates_res = supabase.table("mt_email_snapshots").select("snapshot_month").eq("tenant_id", tenant_id).order("snapshot_month", desc=True).execute()
        
        if not dates_res.data:
            st.info("No email data found. Upload a campaign statement CSV in the 'Automated Ingestion' tab.")
        else:
            avail_dates = [d['snapshot_month'] for d in dates_res.data]
            selected_date = st.selectbox("Select Audit Month", avail_dates)
            
            if selected_date:
                # Fetch Macro Stats
                mac_res = supabase.table("mt_email_snapshots").select("*").eq("tenant_id", tenant_id).eq("snapshot_month", selected_date).execute()
                # Fetch Micro Campaign Stats
                camp_res = supabase.table("mt_campaign_records").select("*").eq("tenant_id", tenant_id).eq("snapshot_month", selected_date).execute()
                
                if mac_res.data:
                    macro = mac_res.data[0]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Delivered", f"{macro['total_emails_delivered']:,}")
                    c2.metric("Avg Open Rate", f"{macro['avg_unique_open_rate']*100:.2f}%")
                    c3.metric("Avg Reads/Open", f"{macro['avg_reads_per_unique_open']:.2f}")
                    c4.metric("Avg Bounce Rate", f"{macro['avg_bounce_rate']*100:.2f}%")
                    
                    st.divider()
                    st.markdown("### 🎯 Campaign Group Breakdown")
                    if camp_res.data:
                        df_camp = pd.DataFrame(camp_res.data)
                        display_camp = df_camp[['campaign_group_name', 'emails_delivered', 'avg_unique_open_rate', 'avg_unique_click_rate', 'pct_of_total_emails_sent']].copy()
                        
                        # Formatting
                        display_camp['avg_unique_open_rate'] = display_camp['avg_unique_open_rate'].apply(lambda x: f"{x*100:.2f}%")
                        display_camp['avg_unique_click_rate'] = display_camp['avg_unique_click_rate'].apply(lambda x: f"{x*100:.2f}%")
                        display_camp['pct_of_total_emails_sent'] = display_camp['pct_of_total_emails_sent'].apply(lambda x: f"{x*100:.2f}%")
                        
                        st.dataframe(display_camp.rename(columns={
                            'campaign_group_name': 'Campaign',
                            'emails_delivered': 'Delivered',
                            'avg_unique_open_rate': 'Open Rate',
                            'avg_unique_click_rate': 'Click Rate',
                            'pct_of_total_emails_sent': '% of Total Sent'
                        }), use_container_width=True, hide_index=True)

    # --- TAB 2: AUTOMATED CSV INGESTION ---
    with tabs[1]:
        st.subheader("Process Campaign Statement")
        with st.container(border=True):
            col_m, col_y = st.columns(2)
            with col_m:
                month_list = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
                email_month = st.selectbox("Reporting Month", month_list, index=datetime.date.today().month - 1)
            with col_y:
                email_year = st.selectbox("Reporting Year", [2024, 2025, 2026, 2027], index=2)
                
            target_date_iso = f"{email_year}-{email_month}-01"
            
            uploaded_csv = st.file_uploader("📥 Upload Statement (CSV):", type=["csv"])
            
            if uploaded_csv and st.button("🚀 Process & Vault Statement", use_container_width=True):
                try:
                    df_raw = pd.read_csv(uploaded_csv)
                    
                    if "Campaign Name" not in df_raw.columns or "Emails Delivered" not in df_raw.columns:
                        st.error("Invalid CSV structure. Missing 'Campaign Name' or 'Emails Delivered' columns.")
                    else:
                        # 1. Clean Data (Remove Commas)
                        cols_to_clean = ["Emails Delivered", "Unique Email Opens", "Total Email Opens", "Total Email Bounces", "Unsubscribes", "Unique Email Clicks"]
                        for col in cols_to_clean:
                            if col in df_raw.columns:
                                df_raw[col] = pd.to_numeric(df_raw[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

                        # 2. Filter Totals
                        mask = df_raw["Campaign Name"].astype(str).str.contains('Total|Average', case=False, na=False)
                        df_seg = df_raw[~mask].copy()

                        # 3. Macro Math
                        mac_del = int(df_seg["Emails Delivered"].sum())
                        mac_u_op = int(df_seg["Unique Email Opens"].sum())
                        mac_t_op = int(df_seg["Total Email Opens"].sum())
                        mac_bnc = int(df_seg["Total Email Bounces"].sum())
                        mac_uns = int(df_seg["Unsubscribes"].sum())
                        
                        mac_payload = {
                            "tenant_id": tenant_id, "snapshot_month": target_date_iso,
                            "total_emails_delivered": mac_del,
                            "avg_unique_open_rate": min(float(mac_u_op / mac_del) if mac_del > 0 else 0.0, 9.99),
                            "avg_reads_per_unique_open": min(float(mac_t_op / mac_u_op) if mac_u_op > 0 else 0.0, 9.99),
                            "avg_bounce_rate": min(float(mac_bnc / mac_del) if mac_del > 0 else 0.0, 9.99),
                            "avg_unsubscribe_rate": min(float(mac_uns / mac_del) if mac_del > 0 else 0.0, 9.99)
                        }
                        supabase.table("mt_email_snapshots").upsert(mac_payload, on_conflict="tenant_id, snapshot_month").execute()

                        # 4. Micro Math
                        def categorize(name):
                            n = str(name).upper()
                            if "HOTEL" in n: return "Hotel"
                            if "FOOD" in n or "CHOP" in n: return "Food & Bev"
                            if "PROMO" in n or "CORE" in n: return "Core Promo"
                            return "Other"

                        df_seg["Category"] = df_seg["Campaign Name"].apply(categorize)
                        group_agg = df_seg.groupby("Category").agg(
                            deliv=("Emails Delivered", "sum"),
                            u_op=("Unique Email Opens", "sum"),
                            u_cl=("Unique Email Clicks", "sum"),
                            bnc=("Total Email Bounces", "sum")
                        ).reset_index()

                        for _, row in group_agg.iterrows():
                            g_del = int(row["deliv"])
                            if g_del > 0:
                                c_payload = {
                                    "tenant_id": tenant_id, "snapshot_month": target_date_iso,
                                    "campaign_group_name": str(row["Category"]),
                                    "emails_delivered": g_del,
                                    "avg_unique_open_rate": min(float(row["u_op"] / g_del), 9.99),
                                    "avg_unique_click_rate": min(float(row["u_cl"] / g_del), 9.99),
                                    "avg_bounce_rate": min(float(row["bnc"] / g_del), 9.99),
                                    "pct_of_total_emails_sent": min(float(g_del / mac_del), 9.99)
                                }
                                supabase.table("mt_campaign_records").upsert(c_payload, on_conflict="tenant_id, snapshot_month, campaign_group_name").execute()

                        st.success("✅ Statement perfectly parsed and securely vaulted!")
                        st.rerun()

                except Exception as e:
                    st.error(f"Processing Error: {e}")
