# casino.py
import streamlit as st
import pandas as pd
import datetime

def render_casino_module(supabase, tenant_id, property_name):
    st.title("🎰 Casino Analytics")
    st.write(f"Operational data and forecasting for **{property_name}**.")

    tabs = st.tabs(["📊 Executive Dashboard", "📝 Daily Ledger Entry"])

    # --- TAB 1: EXECUTIVE DASHBOARD ---
    with tabs[0]:
        st.subheader("Performance Overview")
        
        # 1. Fetch ONLY this tenant's data
        res = supabase.table("mt_ledger").select("*").eq("tenant_id", tenant_id).order("entry_date", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            
            # 2. Calculate simple metrics
            total_rev = df['actual_coin_in'].sum()
            total_traffic = df['actual_traffic'].sum()
            total_members = df['new_members'].sum()
            
            # 3. Render Scoreboard
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Coin-In", f"${total_rev:,.0f}")
            c2.metric("Total Traffic", f"{total_traffic:,} Guests")
            c3.metric("New Members", f"{total_members:,}")
            
            st.divider()
            st.markdown("### 📜 Historical Ledger")
            # Clean up the dataframe for display
            display_df = df[['entry_date', 'actual_traffic', 'actual_coin_in', 'new_members']].copy()
            display_df['actual_coin_in'] = display_df['actual_coin_in'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
        else:
            st.info("No ledger data found. Add your first entry in the 'Daily Ledger Entry' tab.")

    # --- TAB 2: DATA ENTRY ---
    with tabs[1]:
        st.subheader("Log Daily Performance")
        with st.form("casino_ledger_form", clear_on_submit=True):
            e_date = st.date_input("Audit Date", value=datetime.date.today())
            
            col1, col2 = st.columns(2)
            with col1:
                e_traffic = st.number_input("Actual Traffic (Headcount)", min_value=0, step=1)
                e_members = st.number_input("New Card Signups", min_value=0, step=1)
            with col2:
                e_coin = st.number_input("Actual Coin-In ($)", min_value=0.0, step=1000.0)

            if st.form_submit_button("💾 Save to Secure Vault", use_container_width=True):
                payload = {
                    "tenant_id": tenant_id,
                    "entry_date": str(e_date),
                    "actual_traffic": e_traffic,
                    "actual_coin_in": e_coin,
                    "new_members": e_members
                }
                
                try:
                    # Upsert updates the row if the date already exists for this tenant
                    supabase.table("mt_ledger").upsert(payload, on_conflict="tenant_id, entry_date").execute()
                    st.success(f"Data for {e_date} successfully vaulted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save data: {e}")
