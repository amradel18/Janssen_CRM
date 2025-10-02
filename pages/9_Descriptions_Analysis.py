import streamlit as st
import pandas as pd
import os
import sys
import re

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the centralized modules
from process.data_loader import load_all_data, get_companies_data, get_company_mapping
from process.session_manager import ensure_data_loaded, get_dataframes
from auth.authentication import check_authentication

# Set page config
# Page config is set in the main app

PROBLEM_KEYWORDS = sorted(list(set([
    # --- حماية المستهلك ومشتقاتها ---
    "حماية المستهلك", "حمايه المستهلك", "شكوى حماية المستهلك", "شكوي حمايه المستهلك",
    "بلاغ حماية المستهلك", "بلاغ حمايه المستهلك", "مكتب حماية المستهلك", "هيئة حماية المستهلك",
    "حقوق المستهلك", "حقوق المستهلكين",

    # --- مشاكل عامة باللهجة المصرية ---
    "مشكلة", "مشاكل", "مشكله", "مشكل", "باز", "بايظ", "بايظه", "باظت",
    "عطل", "عطلان", "عطله", "واقف", "واقفه", "وقف", "وقفه",
    "وقع", "وقعلي", "وقعلى", "وقعت", "مهنج", "معلق", "مقفول",
    "تعبان", "تعبانه", "مضروب", "مغشوش", "مش شغال", "مش شغاله",
    "ما بيشتغلش", "ما بيشتغلش خالص", "مش راضي يشتغل", "مش شغال خالص",
    "not working", "error", "problem", "issue",

    # --- تصعيد وغضب وشتيمة مصرية ---
    "شكوى", "شكوي", "هاشتكي", "هاشتكيك", "اشتكي", "عايز اشتكي",
    "تصعيد", "مدير", "مسؤول", "مسئول", "عايز المسئول", "عايز المسؤول",
    "مافيش رد", "مفيش رد", "مفيش متابعه", "مفيش متابعة",
    "بيتجاهلوا", "اهمال", "استهتار", "سوء خدمة", "سوء معامله", "سوء معاملة",
    "زبالة", "زباله", "يا نصابين", "حرامية", "حراميه", "يا حرامية",
    "نصاب", "نصابين", "فاشل", "فاشله", "بهدلة", "بهدله", "مهزلة", "مهزله", "كارثة", "كارثه",
    "scam", "fraud", "fake", "rude", "bad service",

    # --- مشاكل الجودة (مراتب + خامات) ---
    "خامة بايظة", "خامة تعبانة", "خامات وحشة", "مش اصلي", "مش أصلي", "مش اصلى", "مضروب", "تالف",
    "broken", "bad quality"

    # --- مشاكل في الراحة والاستعمال ---
    "مقع", "مقعط", "غاطس", "هبطت", "هبوط", "متهالك", "مش مستوي", "مش مستويه", "معوج", "معوجه",
    "سقف", "سقفت", "تقطع", "تقطعت", "تشققت", "تشقق",
    "خشنة", "خشنه", "خشونه", "بتجرح", "بتوجع", "وجع ضهر", "وجع ظهر", "وجع ضهرى", "وجع ظهري",
    "صداع", "مش مريحة", "مش مريحه", "موجعة", "موجعه", "بتوجعني", "بتوجعنى",
    "dirty",

    # --- مشاكل التوصيل والشحن ---
    "توصيل", "التوصيل", "الشحن", "مش وصلت", "ماوصلتش", "موصلتش",
    "اتأخر", "اتأخرت", "اتأجل", "تأخير", "delay", "delayed",
    "ميعاد غلط", "ميعاد متأخر", "ميعاد متاخر",
    "العربية اتأخرت", "العربية اتأجلت", "النقل باز", "النقل متأخر",

    # --- نظافة وتعقيم ---
    "متسخة", "متسخه", "وسخة", "وسخه", "مش نظيفة", "مش نظيفه", "مش نضيفه",
    "ملوثة", "ملوثه", "بقع", "بقعة", "وساخة", "وساخه", "تراب", "مليانة تراب",
    "ريحة وحشة", "ريحة وحشه", "ريحة كريهة", "ريحة كريهه", "ريحة عفن", "ريحة معفنه", "ريحة تراب",
    "عفن", "معفن", "معفنه", "حشرات", "ناموس", "بق الفراش", "بق", "bed bugs",

    # --- انجليزي مستخدم بكثرة في مصر ---
    "broken", "delay", "late", "dirty", "problem", "issue",
    "complaint", "refund", "return", "exchange",
    "fake", "fraud", "scam", "bad quality", "low quality",
    "support", "customer support", "no response"
])))


def find_problematic_keywords(text):
    """
    Finds problematic keywords in the given text.
    """
    found_keywords = []
    # Use word boundaries to match whole words
    for keyword in PROBLEM_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            found_keywords.append(keyword)
    return list(set(found_keywords)) # Return unique keywords

@st.cache_data
def get_descriptions_with_details(dataframes):
    """
    Extracts descriptions from ticketcall and customercall tables with customer and date info.
    """
    ticketcall_df = dataframes.get('ticketcall', pd.DataFrame()).copy()
    customercall_df = dataframes.get('customercall', pd.DataFrame()).copy()
    customers_df = dataframes.get('customers', pd.DataFrame()).copy()
    customer_phones_df = dataframes.get('customer_phones', pd.DataFrame()).copy()

    descriptions_data = []

    # Process ticket calls
    if 'description' in ticketcall_df.columns and 'customer_id' in ticketcall_df.columns and 'created_at' in ticketcall_df.columns:
        ticket_calls = ticketcall_df[['customer_id', 'description', 'created_at']].dropna()
        descriptions_data.append(ticket_calls)

    # Process customer calls
    if 'description' in customercall_df.columns and 'customer_id' in customercall_df.columns and 'created_at' in customercall_df.columns:
        customer_calls = customercall_df[['customer_id', 'description', 'created_at']].dropna()
        descriptions_data.append(customer_calls)

    if not descriptions_data:
        return pd.DataFrame({'customer_id': [], 'description': [], 'created_at': [], 'customer_name': [], 'customer_phones': []})

    # Combine data and ensure datetime format
    full_df = pd.concat(descriptions_data, ignore_index=True)
    full_df['created_at'] = pd.to_datetime(full_df['created_at'])

    # Aggregate phone numbers
    if not customer_phones_df.empty and 'customer_id' in customer_phones_df.columns and 'phone' in customer_phones_df.columns:
        customer_phones_df['phone'] = customer_phones_df['phone'].astype(str)
        phone_agg = customer_phones_df.groupby('customer_id')['phone'].apply(lambda x: '; '.join(x)).reset_index()
        phone_agg = phone_agg.rename(columns={'phone': 'customer_phones'})
        full_df = pd.merge(full_df, phone_agg, on='customer_id', how='left')
        full_df['customer_phones'] = full_df['customer_phones'].fillna('No Phone')
    else:
        full_df['customer_phones'] = 'No Phone'

    # Merge with customer data to get names
    if 'id' in customers_df.columns and 'name' in customers_df.columns:
        customers_df = customers_df.rename(columns={'id': 'customer_id', 'name': 'customer_name'})
        company_mapping = get_company_mapping()
        customers_df['company_name'] = customers_df['company_id'].map(company_mapping).fillna("NULL")
        full_df = pd.merge(full_df, customers_df[['customer_id', 'customer_name', 'company_name']], on='customer_id', how='left')
        full_df['customer_name'] = full_df['customer_name'].fillna('Unknown')
        full_df['company_name'] = full_df['company_name'].fillna('NULL')
    else:
        full_df['customer_name'] = 'Unknown'
        full_df['company_name'] = 'NULL'


    return full_df.drop_duplicates(subset=['description'])


def main():
    check_authentication()
    st.title("Problematic Descriptions from Ticket and Customer Calls")

    # Ensure data is loaded
    ensure_data_loaded()
    
    # Get dataframes safely
    dataframes = get_dataframes()

    with st.spinner("Processing descriptions..."):
        descriptions_df = get_descriptions_with_details(dataframes)

    if descriptions_df.empty:
        st.warning("No descriptions found in 'ticketcall' or 'customercall' tables.")
        return

    # Date Filter
    st.sidebar.header("Filter Options")
    min_date = descriptions_df['created_at'].min().date()
    max_date = descriptions_df['created_at'].max().date()
    start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)

    # Company filter
    if 'company_name' in descriptions_df.columns:
        companies = list(descriptions_df['company_name'].unique())
        selected_companies = st.sidebar.multiselect("Select Companies", companies, default=companies)
    else:
        selected_companies = []

    # Filter dataframe based on date
    filtered_df = descriptions_df[(descriptions_df['created_at'].dt.date >= start_date) & (descriptions_df['created_at'].dt.date <= end_date)]

    if selected_companies:
        filtered_df = filtered_df[filtered_df['company_name'].isin(selected_companies)]

    if filtered_df.empty:
        st.warning("No descriptions found in the selected date range.")
    else:
        st.header("Descriptions with Problematic Keywords")

        with st.spinner("Finding descriptions with problematic keywords..."):
            # Find problematic keywords
            filtered_df['problem_keywords'] = filtered_df['description'].apply(find_problematic_keywords)

            # Filter for rows that have at least one problematic keyword
            problematic_df = filtered_df[filtered_df['problem_keywords'].apply(lambda x: len(x) > 0)].copy()

        if problematic_df.empty:
            st.info("No descriptions with problematic keywords found in the selected date range.")
        else:
            st.write(f"**Found {len(problematic_df)} descriptions with problematic keywords.**")
            st.dataframe(problematic_df[['customer_name', 'customer_phones', 'description', 'created_at', 'problem_keywords']])

if __name__ == "__main__":
    main()