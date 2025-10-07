import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import re
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from process.data_loader import load_all_data, get_companies_data, get_company_mapping, cached_table_query
from process.session_manager import ensure_data_loaded, get_dataframes
from auth.authentication import check_authentication
import plotly.express as px

# Set page config
#st.set_page_config(page_title="Ticket Items Analysis", layout="wide")

# Helper to ensure merge keys share the same integer dtype
def coerce_integer_columns(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

def main():
    check_authentication()
    st.title("Ticket Items Analysis")

    # Ensure data is loaded
    ensure_data_loaded()
    
    # Get dataframes safely
    dataframes = get_dataframes()

    # Extract necessary dataframes
    ticket_items_df = dataframes.get('ticket_items', pd.DataFrame())
    tickets_df = dataframes.get('tickets', pd.DataFrame())
    product_info_df = dataframes.get('product_info', pd.DataFrame())
    request_reasons_df = dataframes.get('request_reasons', pd.DataFrame())
    ticket_categories_df = dataframes.get('ticket_categories', pd.DataFrame())
    users_df = dataframes.get('users', pd.DataFrame())
    customers_df = dataframes.get('customers', pd.DataFrame())
    companies_df = dataframes.get('companies', pd.DataFrame())
    ticketcall_df = dataframes.get('ticketcall', pd.DataFrame())

    # Coerce merge keys to consistent nullable integer dtype
    coerce_integer_columns(ticket_items_df, ['ticket_id','product_id','request_reason_id','ticket_cat_id','created_by','customer_id','company_id'])
    coerce_integer_columns(tickets_df, ['id','company_id','customer_id','created_by'])
    coerce_integer_columns(product_info_df, ['id'])
    coerce_integer_columns(request_reasons_df, ['id'])
    coerce_integer_columns(ticket_categories_df, ['id'])
    coerce_integer_columns(users_df, ['id'])
    coerce_integer_columns(customers_df, ['id','company_id'])
    coerce_integer_columns(companies_df, ['id'])
    coerce_integer_columns(ticketcall_df, ['ticket_id','created_by','call_type'])


    # Process ticketcall data for call details
    if not ticketcall_df.empty:
        call_users_df = dataframes.get('users', pd.DataFrame()).copy().rename(columns={'name': 'user_name'})
        call_types_df = dataframes.get('call_types', pd.DataFrame()).copy().rename(columns={'name': 'call_type_name'})
        # Ensure ids used for merges are consistent
        coerce_integer_columns(call_users_df, ['id'])
        coerce_integer_columns(call_types_df, ['id'])
        
        processed_calls_df = ticketcall_df.merge(call_users_df[['id', 'user_name']], left_on='created_by', right_on='id', how='left')
        processed_calls_df = processed_calls_df.merge(call_types_df[['id', 'call_type_name']], left_on='call_type', right_on='id', how='left')
        processed_calls_df['user_name'] = processed_calls_df['user_name'].fillna('Unknown User')
        processed_calls_df['call_type_name'] = processed_calls_df['call_type_name'].fillna('Unknown Type')
        processed_calls_df['created_at'] = pd.to_datetime(processed_calls_df['created_at'], errors='coerce')
    else:
        processed_calls_df = pd.DataFrame(columns=['ticket_id', 'created_at', 'call_duration', 'call_type_name', 'user_name', 'description'])


    if ticket_items_df.empty:
        st.warning("No ticket items data available.")
        return

    # Ensure company_name is available on ticket_items before building filters
    if not companies_df.empty and 'company_id' in ticket_items_df.columns:
        companies_lookup = companies_df[['id','name']].copy()
        companies_lookup.rename(columns={'id':'company_id','name':'company_name'}, inplace=True)
        ticket_items_df = pd.merge(ticket_items_df, companies_lookup, on='company_id', how='left')
        ticket_items_df['company_name'] = ticket_items_df['company_name'].fillna('Unknown Company').astype(str).str.strip()

    # Convert date columns
    ticket_items_df['created_at'] = pd.to_datetime(ticket_items_df['created_at'])

    # Function to normalize product sizes
    def normalize_size(size):
        if isinstance(size, str):
            numbers = [int(s) for s in re.findall(r'\d+', size)]
            if len(numbers) == 2:
                return 'x'.join(map(str, sorted(numbers)))
            elif len(numbers) == 3:
                return 'x'.join(map(str, sorted(numbers[:2])))
        return 'Unknown Size'

    # Apply the function to the product_size column
    if 'product_size' in ticket_items_df.columns:
        ticket_items_df['normalized_size'] = ticket_items_df['product_size'].apply(normalize_size)

    # Sidebar Filters
    with st.sidebar:
        st.header("Filters")

        # Date range filter
        min_date = ticket_items_df['created_at'].min().date()
        max_date = ticket_items_df['created_at'].max().date()
        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
        
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Filter by Product
        product_list = ["All"] + product_info_df['product_name'].unique().tolist()
        selected_product = st.selectbox("Select Product", product_list)

        # Filter by Request Reason
        reason_list = ["All"] + request_reasons_df['name'].unique().tolist()
        selected_reason = st.selectbox("Select Request Reason", reason_list)

        # Filter by Ticket Category
        category_list = ["All"] + ticket_categories_df['name'].unique().tolist()
        selected_category = st.selectbox("Select Ticket Category", category_list)

        # Filter by Inspected
        inspected_list = ["All", "Yes", "No"]
        selected_inspected = st.selectbox("Select Inspected", inspected_list)

        # Filter by Company - use company_name values present in ticket_items
        company_name_options = ["All"] + sorted(ticket_items_df['company_name'].dropna().astype(str).str.strip().unique().tolist())
        selected_company_name = st.selectbox("Select Company", company_name_options)
        


    # Merge dataframes for detailed analysis with unique column names to avoid conflicts
    # Start with ticket_items as base dataframe
    merged_df = ticket_items_df.copy()
    
    # Then merge with tickets to get customer_id
    tickets_df_merge = tickets_df.copy()
    tickets_df_merge = tickets_df_merge.rename(columns={'id': 'ticket_table_id'})
    
    # Drop conflicting columns from tickets_df_merge to avoid duplicate column issues
    # IMPORTANT: We keep company_id from ticket_items, so we drop it from tickets
    columns_to_drop_tickets = ['created_by', 'updated_at', 'created_at', 'company_id']
    tickets_df_merge = tickets_df_merge.drop(columns=[col for col in columns_to_drop_tickets if col in tickets_df_merge.columns])
    
    # Ensure data types match before merging
    if 'ticket_id' in merged_df.columns:
        merged_df['ticket_id'] = pd.to_numeric(merged_df['ticket_id'], errors='coerce')
        tickets_df_merge['ticket_table_id'] = pd.to_numeric(tickets_df_merge['ticket_table_id'], errors='coerce')
    
    merged_df = merged_df.merge(tickets_df_merge, left_on='ticket_id', right_on='ticket_table_id', how='left')
    
    # Merge with product info
    product_info_df_merge = product_info_df.copy()
    product_info_df_merge = product_info_df_merge.rename(columns={'id': 'product_table_id'})
    
    # Drop conflicting columns from product_info_df_merge
    columns_to_drop_product = ['created_by', 'updated_at', 'company_id', 'created_at']
    product_info_df_merge = product_info_df_merge.drop(columns=[col for col in columns_to_drop_product if col in product_info_df_merge.columns])
    
    # Ensure data types match before merging
    if 'product_id' in merged_df.columns:
        merged_df['product_id'] = pd.to_numeric(merged_df['product_id'], errors='coerce')
        product_info_df_merge['product_table_id'] = pd.to_numeric(product_info_df_merge['product_table_id'], errors='coerce')
    
    merged_df = merged_df.merge(product_info_df_merge, left_on='product_id', right_on='product_table_id', how='left')
    
    # Merge with request reasons
    request_reasons_df_merge = request_reasons_df.copy()
    request_reasons_df_merge = request_reasons_df_merge.rename(columns={'id': 'reason_table_id', 'name': 'name_reason'})
    
    # Drop conflicting columns from request_reasons_df_merge
    columns_to_drop_reasons = ['created_by', 'updated_at', 'company_id', 'created_at']
    request_reasons_df_merge = request_reasons_df_merge.drop(columns=[col for col in columns_to_drop_reasons if col in request_reasons_df_merge.columns])
    
    # Ensure data types match before merging
    if 'request_reason_id' in merged_df.columns:
        merged_df['request_reason_id'] = pd.to_numeric(merged_df['request_reason_id'], errors='coerce')
        request_reasons_df_merge['reason_table_id'] = pd.to_numeric(request_reasons_df_merge['reason_table_id'], errors='coerce')
    
    merged_df = merged_df.merge(request_reasons_df_merge, left_on='request_reason_id', right_on='reason_table_id', how='left')
    
    # Merge with ticket categories
    ticket_categories_df_merge = ticket_categories_df.copy()
    ticket_categories_df_merge = ticket_categories_df_merge.rename(columns={'id': 'category_table_id', 'name': 'name_category'})
    
    # Drop conflicting columns from ticket_categories_df_merge
    columns_to_drop_categories = ['created_by', 'updated_at', 'company_id', 'created_at']
    ticket_categories_df_merge = ticket_categories_df_merge.drop(columns=[col for col in columns_to_drop_categories if col in ticket_categories_df_merge.columns])
    
    # Ensure data types match before merging
    if 'ticket_cat_id' in merged_df.columns:
        merged_df['ticket_cat_id'] = pd.to_numeric(merged_df['ticket_cat_id'], errors='coerce')
        ticket_categories_df_merge['category_table_id'] = pd.to_numeric(ticket_categories_df_merge['category_table_id'], errors='coerce')
    
    merged_df = merged_df.merge(ticket_categories_df_merge, left_on='ticket_cat_id', right_on='category_table_id', how='left')
    
    # Merge with users
    users_df_merge = users_df.copy()
    users_df_merge = users_df_merge.rename(columns={'id': 'user_table_id', 'name': 'name_user'})
    
    # Drop conflicting columns from users_df_merge
    columns_to_drop_users = ['updated_at', 'company_id', 'created_at']
    users_df_merge = users_df_merge.drop(columns=[col for col in columns_to_drop_users if col in users_df_merge.columns])
    
    # Ensure data types match before merging
    if 'created_by' in merged_df.columns:
        merged_df['created_by'] = pd.to_numeric(merged_df['created_by'], errors='coerce')
        users_df_merge['user_table_id'] = pd.to_numeric(users_df_merge['user_table_id'], errors='coerce')
    
    merged_df = merged_df.merge(users_df_merge, left_on='created_by', right_on='user_table_id', how='left')
    
    # Merge with customers
    customers_df_merge = customers_df.copy()
    customers_df_merge = customers_df_merge.rename(columns={'id': 'customer_table_id', 'name': 'customer_name'})
    
    # Drop conflicting columns from customers_df_merge but keep company_id
    columns_to_drop_customers = ['created_by', 'updated_at', 'created_at']
    customers_df_merge = customers_df_merge.drop(columns=[col for col in columns_to_drop_customers if col in customers_df_merge.columns])
    
    # Ensure data types match before merging
    if 'customer_id' in merged_df.columns:
        merged_df['customer_id'] = pd.to_numeric(merged_df['customer_id'], errors='coerce')
        customers_df_merge['customer_table_id'] = pd.to_numeric(customers_df_merge['customer_table_id'], errors='coerce')
    
    merged_df = merged_df.merge(customers_df_merge, left_on='customer_id', right_on='customer_table_id', how='left')

    # Merge ticket call data
    if ticketcall_df is not None and not ticketcall_df.empty:
        # Aggregate call descriptions per ticket
        call_descriptions = ticketcall_df.groupby('ticket_id')['description'].apply(lambda x: ' | '.join(x.astype(str))).reset_index()
        call_descriptions.rename(columns={'description': 'call_details'}, inplace=True)
        merged_df = merged_df.merge(call_descriptions, on='ticket_id', how='left')
        merged_df['call_details'] = merged_df['call_details'].fillna('No calls')

# Unify request reasons
    if 'name_reason' in merged_df.columns:
        merged_df['name_reason'] = merged_df['name_reason'].replace('هبوط بالمرتبه', 'هبوط')

    # Apply filters
    filtered_df = merged_df[
        (merged_df['created_at'] >= start_datetime) & (merged_df['created_at'] <= end_datetime)
    ]

    if selected_product != "All":
        filtered_df = filtered_df[filtered_df['product_name'] == selected_product]
    
    if selected_reason != "All":
        filtered_df = filtered_df[filtered_df['name_reason'] == selected_reason]

    if selected_category != "All":
        filtered_df = filtered_df[filtered_df['name_category'] == selected_category]

    if selected_inspected != "All":
        inspected_value = 1 if selected_inspected == "Yes" else 0
        filtered_df = filtered_df[filtered_df['inspected'] == inspected_value]

    if selected_company_name != "All" and 'company_name_x' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['company_name_x'].astype(str).str.strip() == str(selected_company_name).strip()]

    # Display KPIs
    st.header("Ticket Items Overview")
    total_items = len(filtered_df)
    total_tickets = filtered_df['ticket_id'].nunique()
    avg_items_per_ticket = total_items / total_tickets if total_tickets > 0 else 0

    kpi_cols = st.columns(2)
    kpi_cols[0].metric("Total Ticket Items", f"{total_items}")
    kpi_cols[1].metric("Average Items per Ticket", f"{avg_items_per_ticket:.2f}")


    # Display Analysis
    st.header("Analysis")

    if filtered_df.empty:
        st.info("No data matches the selected filters.")
    else:
        # Ticket Items by Product
        st.subheader("Ticket Items by Product")
        product_counts = filtered_df['product_name'].value_counts().reset_index()
        product_counts.columns = ['Product', 'Count']
        fig_product = px.pie(product_counts, names='Product', values='Count', title="Product Distribution")
        st.plotly_chart(fig_product, use_container_width=True)

        # Ticket Items by Ticket Category
        st.subheader("Ticket Items by Ticket Category")
        category_counts = filtered_df['name_category'].value_counts().reset_index()
        category_counts.columns = ['Category', 'Count']
        fig_category = px.bar(category_counts, x='Category', y='Count', title="Ticket Category Distribution")
        st.plotly_chart(fig_category, use_container_width=True)

        # Ticket Items by Request Reason
        st.subheader("Ticket Items by Request Reason")
        reason_counts = filtered_df['name_reason'].value_counts().reset_index()
        reason_counts.columns = ['Reason', 'Count']
        fig_reason = px.pie(reason_counts, names='Reason', values='Count', title="Request Reason Distribution")
        st.plotly_chart(fig_reason, use_container_width=True)


        # Ticket Items by Size
        st.subheader("Ticket Items by Size")
        if 'normalized_size' in filtered_df.columns:
            size_counts = filtered_df['normalized_size'].value_counts().reset_index()
            size_counts.columns = ['Size', 'Count']
            fig_size = px.bar(size_counts, x='Size', y='Count', title="Ticket Items per Size")
            st.plotly_chart(fig_size, use_container_width=True)
        else:
            st.info("No size data available.")

        # Visit Analysis (Moved Up)
        st.header("Visit Analysis")
        if 'inspected' in filtered_df.columns:
            # Ensure inspected_date is in datetime format if it exists
            if 'inspected_date' in filtered_df.columns:
                filtered_df['inspected_date'] = pd.to_datetime(filtered_df['inspected_date'], errors='coerce')
            
            visited_df = filtered_df[filtered_df['inspected'] == 1].copy()
            if 'inspected_date' in visited_df.columns:
                visited_df = visited_df[visited_df['inspected_date'].notna()]

            if not visited_df.empty:
                # Calculate time difference if inspected_date exists
                if 'inspected_date' in visited_df.columns and 'created_at' in visited_df.columns:
                    visited_df['time_to_inspection'] = (visited_df['inspected_date'] - visited_df['created_at']).dt.days

                st.write("### Inspected Ticket Items")
                
                visit_display_cols = [
                    'ticket_id', 'customer_name', 'product_name', 'product_size', 'quantity', 'name_reason', 
                    'inspected_date', 'time_to_inspection', 'prductuionManagerdecision', 'inspected_result', 'client_approval'
                ]
                
                # Filter for columns that exist in the dataframe
                existing_visit_cols = [col for col in visit_display_cols if col in visited_df.columns]

                st.dataframe(visited_df[existing_visit_cols].rename(columns={
                    'ticket_id': 'Ticket ID',
                    'customer_name': 'Customer',
                    'product_name': 'Product',
                    'product_size': 'Size',
                    'quantity': 'Quantity',
                    'name_reason': 'Reason',
                    'inspected_date': 'Visit Date',
                    'time_to_inspection': 'Days to Visit',
                    'prductuionManagerdecision': 'Manager Decision',
                    'inspected_result': 'Visit Result',
                    'client_approval': 'Client Approval'
                }))
            else:
                st.info("No visits recorded for the selected filters.")
        else:
            st.info("Visit information ('inspected' column) not available in the data.")

        # New Analysis Section
        st.header("Detailed Analysis")

        # Convert additional date columns
        if 'purchase_date' in filtered_df.columns:
            filtered_df['purchase_date'] = pd.to_datetime(filtered_df['purchase_date'], errors='coerce')
        if 'inspected_date' in filtered_df.columns:
            filtered_df['inspected_date'] = pd.to_datetime(filtered_df['inspected_date'], errors='coerce')

        # Purchase Analysis by Year and Request Reason Treemap
        if 'purchase_date' in filtered_df.columns and 'name_reason' in filtered_df.columns:
            st.subheader("Purchase Analysis by Year and Request Reason")
            purchase_analysis_df = filtered_df.copy()
            
            # Handle missing purchase dates
            purchase_analysis_df['Year'] = pd.to_datetime(purchase_analysis_df['purchase_date'], errors='coerce').dt.year
            purchase_analysis_df['Year'] = purchase_analysis_df['Year'].fillna('Unknown').astype(str)
            
            # Ensure request reason is not null
            purchase_analysis_df['name_reason'] = purchase_analysis_df['name_reason'].fillna('Unknown')

            if not purchase_analysis_df.empty:
                treemap_data = purchase_analysis_df.groupby(['Year', 'name_reason']).size().reset_index(name='Count')

                fig_treemap = px.treemap(treemap_data,
                                         path=[px.Constant("All"), 'Year', 'name_reason'],
                                         values='Count',
                                         title='Purchase Distribution by Year and Request Reason')
                fig_treemap.update_traces(root_color="lightgrey")
                fig_treemap.update_layout(margin = dict(t=50, l=25, r=25, b=25))
                st.plotly_chart(fig_treemap, use_container_width=True)
            else:
                st.info("No data available to display the treemap.")

        # Production Manager Decision Analysis
        if 'prductuionManagerdecision' in filtered_df.columns and not filtered_df['prductuionManagerdecision'].isnull().all():
            st.subheader("Production Manager Decisions")
            decision_counts = filtered_df['prductuionManagerdecision'].value_counts().reset_index()
            decision_counts.columns = ['Decision', 'Count']
            fig_decision = px.pie(decision_counts, names='Decision', values='Count', title="Production Manager Decision Distribution")
            st.plotly_chart(fig_decision, use_container_width=True)

        # Client Approval Analysis
        if 'client_approval' in filtered_df.columns and not filtered_df['client_approval'].isnull().all():
            st.subheader("Client Approval Status")
            approval_counts = filtered_df['client_approval'].value_counts().reset_index()
            approval_counts.columns = ['Approval Status', 'Count']
            fig_approval = px.pie(approval_counts, names='Approval Status', values='Count', title="Client Approval Distribution")
            st.plotly_chart(fig_approval, use_container_width=True)


        # Display limited data preview with download option
        st.subheader("Filtered Ticket Items (Top 10 Preview)")
        display_cols = [
            'ticket_id', 'product_name', 'product_size', 'request_reason_detail', 'name_reason', 
            'name_category', 'name_user', 'created_at'
        ]
        
        # Create renamed dataframe for display and download
        display_df = filtered_df[display_cols].rename(columns={
            'ticket_id': 'Ticket ID',
            'product_name': 'Product',
            'product_size': 'Size',
            'request_reason_detail': 'Details',
            'name_reason': 'Reason',
            'name_category': 'Category',
            'name_user': 'Created By',
            'created_at': 'Date'
        })
        
        # Show only top 10 rows
        st.dataframe(display_df.head(10))
        
        # Add download button for full data
        if not filtered_df.empty:
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Download Full Data as CSV",
                data=csv,
                file_name="ticket_items_data.csv",
                mime="text/csv",
            )
            st.info(f"Note: Only showing top 10 rows as preview. Full dataset contains {len(display_df)} rows. Use the download button to get the complete dataset.")

        # Top 10 Customers by Ticket Items
        st.header("Top 10 Customers by Item Count")
        
        # Determine aggregation for item count
        if 'quantity' in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df['quantity']):
            item_agg = ('quantity', 'sum')
        else:
            item_agg = ('id', 'size')
            
        customer_item_counts = filtered_df.groupby('customer_name').agg(
            item_count=item_agg,
            ticket_count=('ticket_id', 'nunique'),
            product_sizes=('product_size', lambda x: ', '.join(x.unique())),
            issue_reasons=('name_reason', lambda x: ', '.join(x.unique())),
            visit_status=('inspected', lambda x: 'Visited' if 1 in x.values else 'Not Visited'),
            call_details=('call_details', 'first')
        ).sort_values(by='item_count', ascending=False).head(10)

        st.write("Top 10 Customers by Item Count:")
        
        # Rename columns for display
        customer_item_counts.rename(columns={
            'item_count': 'Item Count',
            'ticket_count': 'Ticket Count',
            'product_sizes': 'Product Sizes',
            'issue_reasons': 'Issue Reasons',
            'visit_status': 'Visit Status',
            'call_details': 'Call Details'
        }, inplace=True)

        st.dataframe(customer_item_counts)

        # Expandable section for ticket and call details
        for customer_name, row in customer_item_counts.iterrows():
            with st.expander(f"See details for {customer_name}"):
                st.write(f"**Total Items:** {row['Item Count']}")
                st.write(f"**Total Tickets:** {row['Ticket Count']}")
                
                # Display tickets for the customer (limited to 5)
                st.write("**Tickets (Top 5):**")
                customer_tickets = filtered_df[filtered_df['customer_name'] == customer_name][[
                    'ticket_id', 'created_at', 'name_category', 'name_reason', 'product_name', 'product_size'
                ]].drop_duplicates()
                
                # Show only top 5 tickets
                display_tickets = customer_tickets.rename(columns={
                    'ticket_id': 'Ticket ID',
                    'created_at': 'Date',
                    'name_category': 'Category',
                    'name_reason': 'Reason',
                    'product_name': 'Product',
                    'product_size': 'Size'
                })
                
                st.dataframe(display_tickets.head(5))
                
                # Show count of additional tickets if any
                if len(customer_tickets) > 5:
                    st.info(f"{len(customer_tickets) - 5} more tickets not shown. Download the full data for complete information.")

                # Display calls for the customer's tickets (limited to 5)
                st.write("**Calls (Top 5):**")
                customer_ticket_ids = filtered_df[filtered_df['customer_name'] == customer_name]['ticket_id'].unique()
                if not processed_calls_df.empty and len(customer_ticket_ids) > 0:
                    customer_calls = processed_calls_df[processed_calls_df['ticket_id'].isin(customer_ticket_ids)]
                    if not customer_calls.empty:
                        # Create display dataframe with renamed columns
                        display_calls = customer_calls[[
                            'ticket_id', 'created_at', 'call_duration', 'call_type_name', 'user_name', 'description'
                        ]].rename(columns={
                            'ticket_id': 'Ticket ID',
                            'created_at': 'Call Date',
                            'call_duration': 'Duration (s)',
                            'call_type_name': 'Call Type',
                            'user_name': 'Agent',
                            'description': 'Description'
                        })
                        
                        # Show only top 5 calls
                        st.dataframe(display_calls.head(5))
                        
                        # Show count of additional calls if any
                        if len(customer_calls) > 5:
                            st.info(f"{len(customer_calls) - 5} more calls not shown.")
                            
                        # Add download button for customer's calls
                        csv = display_calls.to_csv(index=False)
                        st.download_button(
                            label=f"Download All Calls for {customer_name}",
                            data=csv,
                            file_name=f"calls_{customer_name.replace(' ', '_')}.csv",
                            mime="text/csv",
                        )
                    else:
                        st.info("No calls found for this customer's tickets.")
                else:
                    st.info("No call data available or no tickets for this customer.")


if __name__ == "__main__":
    main()
""