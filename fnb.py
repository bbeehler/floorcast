# fnb.py
import streamlit as st
import pandas as pd
import datetime

def render_fnb_module(supabase, tenant_id, property_name):
    st.title("🍽️ Food & Beverage")
    st.write(f"Dining metrics and cover tracking for **{property_name}**.")

    tabs = st.tabs(["📊 F&B Dashboard", "📝 Daily Shift Entry"])

    # --- TAB 1: DASHBOARD ---
    with tabs[0]:
        res = supabase.table("mt_fnb_ledger").select("*").eq("tenant_id", tenant_id).order("audit_date", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            total_rev = df['total_revenue'].sum()
            total_covers = df['total_covers'].sum()
            avg_check = (total_rev / total_covers) if total_covers > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Total F&B Revenue", f"${total_rev:,.2f}")
            c2.metric("Total Covers", f"{total_covers:,}")
            c3.metric("Average Check", f"${avg_check:.2f}")

            st.divider()
            display_df = df[['audit_date', 'total_covers', 'total_revenue']].copy()
            display_df['total_revenue'] = display_df['total_revenue'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No F&B data found. Log your first shift in the next tab.")

    # --- TAB 2: DATA ENTRY ---
    with tabs[1]:
        with st.form("fnb_form", clear_on_submit=True):
            a_date = st.date_input("Audit Date", value=datetime.date.today())
            c1, c2 = st.columns(2)
            with c1: covers = st.number_input("Total Covers", min_value=0, step=10)
            with c2: rev = st.number_input("Total Revenue ($)", min_value=0.0, step=500.0)

            if st.form_submit_button("💾 Vault F&B Data", use_container_width=True):
                payload = {"tenant_id": tenant_id, "audit_date": str(a_date), "total_covers": covers, "total_revenue": rev}
                try:
                    supabase.table("mt_fnb_ledger").upsert(payload, on_conflict="tenant_id, audit_date").execute()
                    st.success("F&B shift data vaulted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")
