import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
from datetime import datetime
import numpy as np
# -----------------------------
# Load project modules
# -----------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from process.data_loader import load_all_data, get_companies_data, get_company_mapping
from process.session_manager import ensure_data_loaded, get_dataframes
from auth.authentication import check_authentication


def main():
    check_authentication()
    # Page config is set in the main app

    dataframes = load_all_data()

    def apply_filters(df, start_date, end_date, selected_company_id):
        if df.empty:
            return pd.DataFrame()
        
        # Ensure 'created_at' is datetime for filtering
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            filtered_df = df[(df['created_at'].dt.date >= start_date) & (df['created_at'].dt.date <= end_date)]
        else:
            filtered_df = df

        # Filter by company_id - prioritize direct company_id from action item tables
        if selected_company_id != 'All':
            # First check for direct company_id from action item tables
            if 'company_id' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['company_id'] == selected_company_id]
            # Fallback to company_id_customer if direct company_id is not available
            elif 'company_id_customer' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['company_id_customer'] == selected_company_id]
        
        return filtered_df

    st.title("Action Items Analysis")
    
    # Company filter at the top of the page
    st.subheader("🏢 Company Filter")
    companies_df = get_companies_data()
    selected_company_name = 'All'
    selected_company_id = 'All'

    if not companies_df.empty and 'id' in companies_df.columns and 'name' in companies_df.columns:
        # Create a mapping from company_name to company_id
        company_name_to_id = dict(zip(companies_df['name'], companies_df['id']))
        company_names_for_selectbox = ['All'] + sorted(companies_df['name'].unique().tolist())
        
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_company_name = st.selectbox("Select Company", company_names_for_selectbox, key="company_filter_main")
        
        if selected_company_name != 'All':
            selected_company_id = company_name_to_id.get(selected_company_name, 'All')
            with col2:
                st.info(f"Selected: {selected_company_name}")
    
    st.divider()
    
    # Ensure data is loaded
    ensure_data_loaded()
    
    # Get dataframes safely
    dataframes = get_dataframes()

    ticket_item_change_another_df = dataframes.get('ticket_item_change_another', pd.DataFrame())
    ticket_item_maintenance_df = dataframes.get('ticket_item_maintenance', pd.DataFrame())
    ticket_item_change_same_df = dataframes.get('ticket_item_change_same', pd.DataFrame())
    ticket_items_df = dataframes.get('ticket_items', pd.DataFrame())
    product_info_df = dataframes.get('product_info', pd.DataFrame())
    request_reasons_df = dataframes.get('request_reasons', pd.DataFrame())
    tickets_df = dataframes.get('tickets', pd.DataFrame())
    customers_df = dataframes.get('customers', pd.DataFrame())

    # Add company_name to customers_df
    if not customers_df.empty and 'company_id' in customers_df.columns:
        company_mapping = get_company_mapping()
        customers_df['company_name'] = customers_df['company_id'].map(company_mapping).fillna("NULL")

  

    # Unify problem names
    if not request_reasons_df.empty:
        request_reasons_df['name'] = request_reasons_df['name'].replace({'هبوط بالمرتبه': 'هبوط'})

    def merge_data(df, ticket_items_df, tickets_df, product_info_df, request_reasons_df, customers_df):
        if df.empty or ticket_items_df.empty:
            return pd.DataFrame()


        merged = pd.merge(df, ticket_items_df, left_on='ticket_item_id', right_on='id', how='inner', suffixes=('_df', ''))

        # Step 2: Prepare tickets_df for merge
        tickets_df_processed = tickets_df.copy()
        if 'created_at' in tickets_df_processed.columns:
            # Rename created_at in tickets_df to avoid conflict with the primary 'created_at' from ticket_items_df
            tickets_df_processed.rename(columns={'created_at': 'ticket_created_at_from_tickets'}, inplace=True)

        # Step 3: Merge with tickets_df_processed
        # Use suffixes to ensure no conflict with existing columns in 'merged'
        merged = pd.merge(merged, tickets_df_processed, left_on='ticket_id', right_on='id', how='left', suffixes=('', '_ticket_info'))

        # Step 4: Clean up any remaining conflicting 'created_at' columns
        # The 'created_at' from ticket_items_df should already be named 'created_at'
        # We need to drop any other 'created_at' variants that might have been introduced.
        columns_to_drop = []
        for col in merged.columns:
            if col.startswith('created_at_') and col != 'created_at':
                columns_to_drop.append(col)
            if col == 'ticket_created_at_from_tickets': # This was explicitly renamed, so we can drop it if not needed
                columns_to_drop.append(col)

        if columns_to_drop:
            merged.drop(columns=columns_to_drop, inplace=True)

        # Map company_id to company_name via direct merge with companies_df
        if 'company_id' in merged.columns:
            companies_df = get_companies_data()
            if not companies_df.empty and 'id' in companies_df.columns and 'name' in companies_df.columns:
                companies_small = companies_df[['id', 'name']].rename(columns={'id': 'company_id', 'name': 'company_name'})
                merged = pd.merge(merged, companies_small, on='company_id', how='left')
                merged['company_name'] = merged['company_name'].fillna("Unknown Company")
            else:
                merged['company_name'] = "Unknown Company"

        # Merge with customers to get customer name
        if not customers_df.empty and 'customer_id' in merged.columns:
            merged = pd.merge(merged, customers_df[['id', 'name' ,'company_id']], left_on='customer_id', right_on='id', how='left', suffixes=('', '_customer'))
            merged.rename(columns={'name': 'customer_name'}, inplace=True)

        # Merge with request reasons
        if not request_reasons_df.empty and 'request_reason_id' in merged.columns:
            reasons_renamed = request_reasons_df.rename(columns={'name': 'request_reason_name'})
            merged = pd.merge(merged, reasons_renamed[['id', 'request_reason_name']], left_on='request_reason_id', right_on='id', how='left')

        # Merge with product info
        if not product_info_df.empty and 'product_id' in merged.columns:
            merged = pd.merge(merged, product_info_df[['id', 'product_name']], left_on='product_id', right_on='id', how='left', suffixes=('', '_product'))

        return merged

    merged_change_another = merge_data(ticket_item_change_another_df, ticket_items_df, tickets_df, product_info_df, request_reasons_df, customers_df)
    merged_change_another = merged_change_another[[
    "ticket_item_id",
    "cost",
    "client_approval_df",
    "pulled",
    "pull_date",
    "delivered",
    "delivery_date",
    "updated_at_df",
    "ticket_id",
    "product_id",
    "product_size",
    "quantity",
    "purchase_date",
    "purchase_location",
    "request_reason_detail",
    "inspected",
    "inspection_date",
    "inspection_result",
    "created_at",
    "updated_at",
    "company_id",
    "company_name",
    "customer_id",
    "ticket_cat_id",
    "description",
    "status",
    "created_by_ticket_info",
    "closed_at",
    "id_customer",
    "customer_name",
    "company_id_customer",
    "request_reason_name",
    "product_name"
]]
    merged_maintenance = merge_data(ticket_item_maintenance_df, ticket_items_df, tickets_df, product_info_df, request_reasons_df, customers_df)
    merged_maintenance = merged_maintenance[[
    "ticket_item_id",
    "maintenance_steps",
    "maintenance_cost",
    "client_approval_df",
    "pulled",
    "pull_date",
    "delivered",
    "delivery_date",
    "ticket_id",
    "product_id",
    "product_size",
    "quantity",
    "purchase_date",
    "purchase_location",
    "request_reason_id",
    "request_reason_detail",
    "inspected",
    "inspection_date",
    "inspection_result",
    "created_at",
    "updated_at",
    "company_id",
    "company_name",
    "ticket_cat_id",
    "description",
    "status",
    "created_by_ticket_info",
    "closed_at",
    "updated_at_ticket_info",
    "closing_notes",
    "closed_by",
    "customer_id",
    "customer_name",
    "company_id_customer",
    "request_reason_name",
    "product_name"
]]
    merged_change_same = merge_data(ticket_item_change_same_df, ticket_items_df, tickets_df, product_info_df, request_reasons_df, customers_df)
    merged_change_same = merged_change_same[[
    "ticket_item_id",
    "cost",
    "client_approval_df",
    "pulled",
    "pull_date",
    "delivered",
    "delivery_date",
    "ticket_id",
    "product_size",
    "quantity",
    "purchase_date",
    "purchase_location",
    "request_reason_id",
    "request_reason_detail",
    "inspected",
    "inspection_date",
    "inspection_result",
    "created_at",
    "updated_at",
    "company_id",
    "company_name",
    "customer_id",
    "ticket_cat_id",
    "description",
    "status",
    "created_by_ticket_info",
    "closed_at",
    "customer_name",
    "company_id_customer",
    "request_reason_name",
    "product_name"
]]
    # Add a source column to each dataframe before concatenation
    merged_change_another['_source_df'] = 'change_another'
    merged_maintenance['_source_df'] = 'maintenance'
    merged_change_same['_source_df'] = 'change_same'

    # Combine all for filter options
    combined_df = pd.concat([merged_change_another, merged_maintenance, merged_change_same], ignore_index=True)

    # Sidebar filters
    st.sidebar.header("Filter Options")

    # Date filter
    if not combined_df.empty and 'created_at' in combined_df.columns:
        min_date = combined_df['created_at'].min().date()
        max_date = combined_df['created_at'].max().date()
    else:
        min_date = datetime.today().date()
        max_date = datetime.today().date()

    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)
    
    # Apply filters to each dataframe independently
    def apply_filters_to_dataframe(df, start_date, end_date, selected_company_id):
        if df.empty:
            return pd.DataFrame()
        
        # Apply date filter
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            filtered_df = df[(df['created_at'].dt.date >= start_date) & (df['created_at'].dt.date <= end_date)]
        else:
            filtered_df = df

        # Apply company filter - prioritize direct company_id from action item tables
        if selected_company_id != 'All':
            # First check for direct company_id from action item tables
            if 'company_id' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['company_id'] == selected_company_id]
            # Fallback to company_id_customer if direct company_id is not available
            elif 'company_id_customer' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['company_id_customer'] == selected_company_id]
        
        return filtered_df

    # Apply filters to each individual dataframe
    filtered_change_another = apply_filters_to_dataframe(merged_change_another, start_date, end_date, selected_company_id)
    filtered_maintenance = apply_filters_to_dataframe(merged_maintenance, start_date, end_date, selected_company_id)
    filtered_change_same = apply_filters_to_dataframe(merged_change_same, start_date, end_date, selected_company_id)


    # Tabs
    tab1, tab2, tab3 = st.tabs(["Change Another", "Maintenance", "Change Same"])

    def calculate_kpis(df, df_name):
        kpis = {}
        kpis["Number of Rows"] = len(df)

        if 'product_name' in df.columns:
            kpis["Total Unique Products"] = df['product_name'].nunique()
        else:
            kpis["Total Unique Products"] = 0

        if 'customer_name' in df.columns:
            kpis["Total Unique Customers"] = df['customer_name'].nunique()
        else:
            kpis["Total Unique Customers"] = 0
        
        cost_column = 'cost' if df_name != 'Maintenance' else 'maintenance_cost'
        if cost_column in df.columns:
            total_cost = df[cost_column].fillna(0).sum()
            kpis["Total Costs"] = f"{total_cost:,.2f}"
            
            if kpis["Total Unique Customers"] > 0:
                kpis["Average Cost per Customer"] = f"{total_cost / kpis['Total Unique Customers']:,.2f}"
            else:
                kpis["Average Cost per Customer"] = "0.00"
            
            customers_with_zero_cost = df[df[cost_column].fillna(0) == 0]['customer_name'].nunique()
            kpis["Customers with 0 Cost"] = customers_with_zero_cost
        else:
            kpis["Total Costs"] = "0.00"
            kpis["Average Cost per Customer"] = "0.00"
            kpis["Customers with 0 Cost"] = 0

        if 'created_at' in df.columns and 'inspection_date' in df.columns:
            df_temp = df.copy()
            df_temp['created_at'] = pd.to_datetime(df_temp['created_at'], errors='coerce')
            df_temp['inspection_date'] = pd.to_datetime(df_temp['inspection_date'], errors='coerce')
            # Filter out rows where either date is null
            valid_mask = df_temp['created_at'].notna() & df_temp['inspection_date'].notna()
            if valid_mask.any():
                diffs = (df_temp.loc[valid_mask, 'inspection_date'] - df_temp.loc[valid_mask, 'created_at']).dt.days
                if not diffs.empty:
                    kpis["Avg Days (Creation to Delivery)"] = f"{diffs.mean():,.2f}"
                else:
                    kpis["Avg Days (Creation to Delivery)"] = "N/A"
            else:
                kpis["Avg Days (Creation to Delivery)"] = "N/A"
        else:
            kpis["Avg Days (Creation to Delivery)"] = "N/A"

        return kpis

    with tab1:
        st.subheader("Change Another KPIs")
        kpis_change_another = calculate_kpis(filtered_change_another, "Change Another")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Number of Rows", kpis_change_another["Number of Rows"])
            st.metric("Total Unique Products", kpis_change_another["Total Unique Products"])
        with col2:
            st.metric("Total Unique Customers", kpis_change_another["Total Unique Customers"])
            st.metric("Average Cost per Customer", kpis_change_another["Average Cost per Customer"])
        with col3:
            st.metric("Total Costs", kpis_change_another["Total Costs"])
            st.metric("Customers with 0 Cost", kpis_change_another["Customers with 0 Cost"])
        with col4:
            st.metric("Avg Days (Creation to Delivery)", kpis_change_another["Avg Days (Creation to Delivery)"])

        # Two pie charts under KPIs
        pie_col1, pie_col2 = st.columns(2)
        with pie_col1:
            if not filtered_change_another.empty and 'client_approval_df' in filtered_change_another.columns:
                approval_series = (
                    filtered_change_another['client_approval_df']
                    .astype('Int64')
                    .fillna(0)
                    .astype(int)
                    .map({1: 'Approved', 0: 'Not Approved'})
                )
                approval_counts = approval_series.value_counts().reset_index()
                approval_counts.columns = ['Status', 'Count']
                fig_appr = px.pie(approval_counts, names='Status', values='Count', hole=0.35,
                                   color='Status', color_discrete_map={'Approved': '#2ecc71', 'Not Approved': '#e74c3c'})
                fig_appr.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_appr, use_container_width=True)
            else:
                st.info("No data to show client approval.")
        with pie_col2:
            if not filtered_change_another.empty:
                eff_cost = pd.to_numeric(filtered_change_another.get('cost', pd.Series([np.nan]*len(filtered_change_another))), errors='coerce').fillna(0)
                paid_flag = np.where(eff_cost > 0, 'Paid (>0)', 'Cost = 0')
                paid_counts = pd.Series(paid_flag).value_counts().reset_index()
                paid_counts.columns = ['Status', 'Count']
                fig_paid = px.pie(paid_counts, names='Status', values='Count', hole=0.35,
                                   color='Status', color_discrete_map={'Paid (>0)': '#3498db', 'Cost = 0': '#95a5a6'})
                fig_paid.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_paid, use_container_width=True)
            else:
                st.info("No data to show cost distribution.")
        
        # Quantity Treemap (Change Another)
        if not filtered_change_another.empty:
            treemap_df = filtered_change_another.copy()
            if all(col in treemap_df.columns for col in ['request_reason_name', 'product_name', 'quantity']):
                treemap_df['quantity'] = pd.to_numeric(treemap_df['quantity'], errors='coerce').fillna(0)
                treemap_df = treemap_df.dropna(subset=['request_reason_name', 'product_name'])
                agg = treemap_df.groupby(['request_reason_name', 'product_name'], as_index=False)['quantity'].sum()
                agg = agg[agg['quantity'] > 0]
                if not agg.empty:
                    fig = px.treemap(
                        agg,
                        path=['request_reason_name', 'product_name'],
                        values='quantity',
                        title='Quantity Treemap by Request Reason and Product'
                    )
                    fig.update_traces(textinfo='label+value')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info('No quantity data to show treemap.')
            else:
                st.info('Required columns missing to draw treemap (request_reason_name, product_name, quantity).')
        else:
            st.info('No data for treemap.')

        # Top 10 Customers by Paid Cost (Change Another)
        if not filtered_change_another.empty:
            df_tab = filtered_change_another.copy()
            cost_col = 'cost'
            if cost_col in df_tab.columns:
                df_tab[cost_col] = pd.to_numeric(df_tab[cost_col], errors='coerce').fillna(0)
                df_paid = df_tab[df_tab[cost_col] > 0].copy()
                group_col = 'customer_id' if 'customer_id' in df_paid.columns else ('company_id_customer' if 'company_id_customer' in df_paid.columns else ('customer_name' if 'customer_name' in df_paid.columns else None))
                if group_col is not None:
                    totals = (
                        df_paid.dropna(subset=[group_col])
                              .groupby(group_col, as_index=False)[cost_col]
                              .sum()
                              .rename(columns={cost_col: 'total_paid'})
                    )
                    top_ids = totals.sort_values('total_paid', ascending=False).head(10)[group_col].tolist()
                    df_top_candidates = df_paid[df_paid[group_col].isin(top_ids)].copy()
                    df_top = (
                        df_top_candidates
                        .sort_values([group_col, cost_col], ascending=[True, False])
                        .drop_duplicates(subset=[group_col], keep='first')
                    )
                    if 'customer_name' in df_top.columns and 'customer_id' in df_top.columns:
                        df_top['customer'] = df_top.apply(lambda r: f"{r['customer_name']} ({r['customer_id']})" if pd.notna(r.get('customer_id')) else str(r.get('customer_name')), axis=1)
                    else:
                        df_top['customer'] = df_top.get('customer_name', df_top.get('customer_id', ''))
                    if 'client_approval_df' in df_top.columns:
                        df_top['client_approval'] = (
                            pd.to_numeric(df_top['client_approval_df'], errors='coerce')
                              .fillna(0)
                              .astype(int)
                              .map({1: 'Approved', 0: 'Not Approved'})
                        )
                    total_map = dict(zip(totals[group_col], totals['total_paid']))
                    df_top['total_paid_by_customer'] = df_top[group_col].map(total_map)
                    df_top = df_top.sort_values('total_paid_by_customer', ascending=False).head(10)
                    display_cols = [
                        'customer', 'product_name', 'quantity', 'product_size', 'description', 'inspection_result', 'client_approval_df', 'client_approval', cost_col, 'total_paid_by_customer'
                    ]
                    display_cols = [c for c in display_cols if c in df_top.columns]
                    df_view = df_top[display_cols]
                    st.markdown("Top 10 Customers by Paid Cost")
                    st.dataframe(df_view, use_container_width=True)
                else:
                    st.info("No customer identifier column found to compute top customers.")
            else:
                st.info("No cost column available to compute top customers.")
        else:
            st.info("No data for Top 10 customers.")

        # Instead of showing full raw data, provide a download button and show only top 5 rows as preview
        st.subheader("Data Preview (Top 5 Rows)")
        st.dataframe(filtered_change_another.head(5))
        
        # Add download button for full data
        if not filtered_change_another.empty:
            csv = filtered_change_another.to_csv(index=False)
            st.download_button(
                label="Download Full Data as CSV",
                data=csv,
                file_name="change_another_data.csv",
                mime="text/csv",
            )
            st.info("Note: Only showing top 5 rows as preview. Use the download button to get the complete dataset.")
        
    with tab2:
        st.subheader("Maintenance KPIs")
        kpis_maintenance = calculate_kpis(filtered_maintenance, "Maintenance")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Number of Rows", kpis_maintenance["Number of Rows"])
            st.metric("Total Unique Products", kpis_maintenance["Total Unique Products"])
        with col2:
            st.metric("Total Unique Customers", kpis_maintenance["Total Unique Customers"])
            st.metric("Average Cost per Customer", kpis_maintenance["Average Cost per Customer"])
        with col3:
            st.metric("Total Costs", kpis_maintenance["Total Costs"])
            st.metric("Customers with 0 Cost", kpis_maintenance["Customers with 0 Cost"])
        with col4:
            st.metric("Avg Days (Creation to Delivery)", kpis_maintenance["Avg Days (Creation to Delivery)"])

        # Two pie charts under KPIs
        pie_col1, pie_col2 = st.columns(2)
        with pie_col1:
            if not filtered_maintenance.empty and 'client_approval_df' in filtered_maintenance.columns:
                approval_series = (
                    filtered_maintenance['client_approval_df']
                    .astype('Int64')
                    .fillna(0)
                    .astype(int)
                    .map({1: 'Approved', 0: 'Not Approved'})
                )
                approval_counts = approval_series.value_counts().reset_index()
                approval_counts.columns = ['Status', 'Count']
                fig_appr = px.pie(approval_counts, names='Status', values='Count', hole=0.35,
                                   color='Status', color_discrete_map={'Approved': '#2ecc71', 'Not Approved': '#e74c3c'})
                fig_appr.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_appr, use_container_width=True)
            else:
                st.info("No data to show client approval.")
        with pie_col2:
            if not filtered_maintenance.empty:
                eff_cost = pd.to_numeric(filtered_maintenance.get('maintenance_cost', pd.Series([np.nan]*len(filtered_maintenance))), errors='coerce').fillna(0)
                paid_flag = np.where(eff_cost > 0, 'Paid (>0)', 'Cost = 0')
                paid_counts = pd.Series(paid_flag).value_counts().reset_index()
                paid_counts.columns = ['Status', 'Count']
                fig_paid = px.pie(paid_counts, names='Status', values='Count', hole=0.35,
                                   color='Status', color_discrete_map={'Paid (>0)': '#3498db', 'Cost = 0': '#95a5a6'})
                fig_paid.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_paid, use_container_width=True)
            else:
                st.info("No data to show cost distribution.")

        # Quantity Treemap (Maintenance)
        if not filtered_maintenance.empty:
            treemap_df = filtered_maintenance.copy()
            if all(col in treemap_df.columns for col in ['request_reason_name', 'product_name', 'quantity']):
                treemap_df['quantity'] = pd.to_numeric(treemap_df['quantity'], errors='coerce').fillna(0)
                treemap_df = treemap_df.dropna(subset=['request_reason_name', 'product_name'])
                agg = treemap_df.groupby(['request_reason_name', 'product_name'], as_index=False)['quantity'].sum()
                agg = agg[agg['quantity'] > 0]
                if not agg.empty:
                    fig = px.treemap(
                        agg,
                        path=['request_reason_name', 'product_name'],
                        values='quantity',
                        title='Quantity Treemap by Request Reason and Product'
                    )
                    fig.update_traces(textinfo='label+value')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info('No quantity data to show treemap.')
            else:
                st.info('Required columns missing to draw treemap (request_reason_name, product_name, quantity).')
        else:
            st.info('No data for treemap.')

        # Top 10 Customers by Paid Cost (Maintenance)
        if not filtered_maintenance.empty:
            df_tab = filtered_maintenance.copy()
            cost_col = 'maintenance_cost'
            if cost_col in df_tab.columns:
                df_tab[cost_col] = pd.to_numeric(df_tab[cost_col], errors='coerce').fillna(0)
                df_paid = df_tab[df_tab[cost_col] > 0].copy()
                group_col = 'customer_id' if 'customer_id' in df_paid.columns else ('company_id_customer' if 'company_id_customer' in df_paid.columns else ('customer_name' if 'customer_name' in df_paid.columns else None))
                if group_col is not None:
                    totals = (
                        df_paid.dropna(subset=[group_col])
                              .groupby(group_col, as_index=False)[cost_col]
                              .sum()
                              .rename(columns={cost_col: 'total_paid'})
                    )
                    top_ids = totals.sort_values('total_paid', ascending=False).head(10)[group_col].tolist()
                    df_top = df_paid[df_paid[group_col].isin(top_ids)].copy()
                    if 'customer_name' in df_top.columns and 'customer_id' in df_top.columns:
                        df_top['customer'] = df_top.apply(lambda r: f"{r['customer_name']} ({r['customer_id']})" if pd.notna(r.get('customer_id')) else str(r.get('customer_name')), axis=1)
                    else:
                        df_top['customer'] = df_top.get('customer_name', df_top.get('customer_id', ''))
                    if 'client_approval_df' in df_top.columns:
                        df_top['client_approval'] = (
                            pd.to_numeric(df_top['client_approval_df'], errors='coerce')
                              .fillna(0)
                              .astype(int)
                              .map({1: 'Approved', 0: 'Not Approved'})
                        )
                    total_map = dict(zip(totals[group_col], totals['total_paid']))
                    df_top['total_paid_by_customer'] = df_top[group_col].map(total_map)
                    display_cols = [
                        'customer', 'product_name', 'quantity', 'product_size', 'description', 'maintenance_steps', 'client_approval', cost_col, 'total_paid_by_customer'
                    ]
                    display_cols = [c for c in display_cols if c in df_top.columns]
                    df_view = df_top[display_cols].sort_values(['total_paid_by_customer', cost_col], ascending=[False, False])
                    st.markdown("Top 10 Customers by Paid Cost")
                    st.dataframe(df_view, use_container_width=True)
                else:
                    st.info("No customer identifier column found to compute top customers.")
            else:
                st.info("No cost column available to compute top customers.")
        else:
            st.info("No data for Top 10 customers.")

        # Instead of showing full raw data, provide a download button and show only top 5 rows as preview
        st.subheader("Data Preview (Top 5 Rows)")
        st.dataframe(filtered_maintenance.head(5))
        
        # Add download button for full data
        if not filtered_maintenance.empty:
            csv = filtered_maintenance.to_csv(index=False)
            st.download_button(
                label="Download Full Data as CSV",
                data=csv,
                file_name="maintenance_data.csv",
                mime="text/csv",
            )
            st.info("Note: Only showing top 5 rows as preview. Use the download button to get the complete dataset.")
    with tab3:
        st.subheader("Change Same KPIs")
        kpis_change_same = calculate_kpis(filtered_change_same, "Change Same")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Number of Rows", kpis_change_same["Number of Rows"])
            st.metric("Total Unique Products", kpis_change_same["Total Unique Products"])
        with col2:
            st.metric("Total Unique Customers", kpis_change_same["Total Unique Customers"])
            st.metric("Average Cost per Customer", kpis_change_same["Average Cost per Customer"])
        with col3:
            st.metric("Total Costs", kpis_change_same["Total Costs"])
            st.metric("Customers with 0 Cost", kpis_change_same["Customers with 0 Cost"])
        with col4:
            st.metric("Avg Days (Creation to Delivery)", kpis_change_same["Avg Days (Creation to Delivery)"])

        # Two pie charts under KPIs
        pie_col1, pie_col2 = st.columns(2)
        with pie_col1:
            if not filtered_change_same.empty and 'client_approval_df' in filtered_change_same.columns:
                approval_series = (
                    filtered_change_same['client_approval_df']
                    .astype('Int64')
                    .fillna(0)
                    .astype(int)
                    .map({1: 'Approved', 0: 'Not Approved'})
                )
                approval_counts = approval_series.value_counts().reset_index()
                approval_counts.columns = ['Status', 'Count']
                fig_appr = px.pie(approval_counts, names='Status', values='Count', hole=0.35,
                                   color='Status', color_discrete_map={'Approved': '#2ecc71', 'Not Approved': '#e74c3c'})
                fig_appr.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_appr, use_container_width=True)
            else:
                st.info("No data to show client approval.")
        with pie_col2:
            if not filtered_change_same.empty:
                eff_cost = pd.to_numeric(filtered_change_same.get('cost', pd.Series([np.nan]*len(filtered_change_same))), errors='coerce').fillna(0)
                paid_flag = np.where(eff_cost > 0, 'Paid (>0)', 'Cost = 0')
                paid_counts = pd.Series(paid_flag).value_counts().reset_index()
                paid_counts.columns = ['Status', 'Count']
                fig_paid = px.pie(paid_counts, names='Status', values='Count', hole=0.35,
                                   color='Status', color_discrete_map={'Paid (>0)': '#3498db', 'Cost = 0': '#95a5a6'})
                fig_paid.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_paid, use_container_width=True)
            else:
                st.info("No data to show cost distribution.")

        # Quantity Treemap (Change Same)
        if not filtered_change_same.empty:
            treemap_df = filtered_change_same.copy()
            if all(col in treemap_df.columns for col in ['request_reason_name', 'product_name', 'quantity']):
                treemap_df['quantity'] = pd.to_numeric(treemap_df['quantity'], errors='coerce').fillna(0)
                treemap_df = treemap_df.dropna(subset=['request_reason_name', 'product_name'])
                if treemap_df['quantity'].sum() > 0:
                    fig = px.treemap(
                        treemap_df,
                        path=['request_reason_name', 'product_name'],
                        values='quantity',
                        color='quantity',
                        color_continuous_scale='Blues',
                        title='Quantity Treemap by Request Reason and Product'
                    )
                    fig.update_traces(textinfo='label+value')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info('No quantity data to show treemap.')
            else:
                st.info('Required columns missing to draw treemap (request_reason_name, product_name, quantity).')
        else:
            st.info('No data for treemap.')

        # Top 10 Customers by Paid Cost (Change Same)
        if not filtered_change_same.empty:
            df_tab = filtered_change_same.copy()
            cost_col = 'cost'
            if cost_col in df_tab.columns:
                df_tab[cost_col] = pd.to_numeric(df_tab[cost_col], errors='coerce').fillna(0)
                df_paid = df_tab[df_tab[cost_col] > 0].copy()
                group_col = 'customer_id' if 'customer_id' in df_paid.columns else ('company_id_customer' if 'company_id_customer' in df_paid.columns else ('customer_name' if 'customer_name' in df_paid.columns else None))
                if group_col is not None:
                    totals = (
                        df_paid.dropna(subset=[group_col])
                              .groupby(group_col, as_index=False)[cost_col]
                              .sum()
                              .rename(columns={cost_col: 'total_paid'})
                    )
                    top_ids = totals.sort_values('total_paid', ascending=False).head(10)[group_col].tolist()
                    df_top = df_paid[df_paid[group_col].isin(top_ids)].copy()
                    df_top = (
                        df_top_candidates
                        .sort_values([group_col, cost_col], ascending=[True, False])
                        .drop_duplicates(subset=[group_col], keep='first')
                    )
                    if 'customer_name' in df_top.columns and 'customer_id' in df_top.columns:
                        df_top['customer'] = df_top.apply(lambda r: f"{r['customer_name']} ({r['customer_id']})" if pd.notna(r.get('customer_id')) else str(r.get('customer_name')), axis=1)
                    else:
                        df_top['customer'] = df_top.get('customer_name', df_top.get('customer_id', ''))
                    if 'client_approval_df' in df_top.columns:
                        df_top['client_approval'] = (
                            pd.to_numeric(df_top['client_approval_df'], errors='coerce')
                              .fillna(0)
                              .astype(int)
                              .map({1: 'Approved', 0: 'Not Approved'})
                        )
                    total_map = dict(zip(totals[group_col], totals['total_paid']))
                    df_top['total_paid_by_customer'] = df_top[group_col].map(total_map)
                    display_cols = [
                        'customer', 'product_name', 'quantity', 'product_size', 'description', 'inspection_result', 'client_approval_df', 'client_approval', cost_col, 'total_paid_by_customer'
                    ]
                    display_cols = [c for c in display_cols if c in df_top.columns]
                    df_view = df_top[display_cols].sort_values(['total_paid_by_customer', cost_col], ascending=[False, False])
                    st.markdown("Top 10 Customers by Paid Cost")
                    st.dataframe(df_view, use_container_width=True)
                else:
                    st.info("No customer identifier column found to compute top customers.")
            else:
                st.info("No cost column available to compute top customers.")
        else:
            st.info("No data for Top 10 customers.")

        # Instead of showing full raw data, provide a download button and show only top 5 rows as preview
        st.subheader("Data Preview (Top 5 Rows)")
        st.dataframe(filtered_change_same.head(5))
        
        # Add download button for full data
        if not filtered_change_same.empty:
            csv = filtered_change_same.to_csv(index=False)
            st.download_button(
                label="Download Full Data as CSV",
                data=csv,
                file_name="change_same_data.csv",
                mime="text/csv",
            )
            st.info("Note: Only showing top 5 rows as preview. Use the download button to get the complete dataset.")

if __name__ == "__main__":
    main()
