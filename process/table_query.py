import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import streamlit as st
from datetime import datetime, date


@st.cache_data(show_spinner=False, ttl=600)
def parse_dates(df: pd.DataFrame, date_columns: List[str]) -> pd.DataFrame:
    """
    تحويل أعمدة التاريخ في DataFrame إلى نوع datetime.
    
    Args:
        df: DataFrame المراد معالجته
        date_columns: قائمة بأسماء أعمدة التاريخ
        
    Returns:
        DataFrame مع أعمدة التاريخ المحولة
    """
    df_copy = df.copy()
    for col in date_columns:
        if col in df_copy.columns:
            df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
    return df_copy


@st.cache_data(show_spinner=False, ttl=600)
def filter_by_date_range(df: pd.DataFrame, date_column: str, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> pd.DataFrame:
    """
    تصفية DataFrame بناءً على نطاق تاريخ.
    
    Args:
        df: DataFrame المراد تصفيته
        date_column: اسم عمود التاريخ للتصفية عليه
        start_date: تاريخ البداية (شامل)
        end_date: تاريخ النهاية (شامل)
        
    Returns:
        DataFrame مصفى
    """
    if date_column not in df.columns:
        return df
        
    # تأكد من أن عمود التاريخ هو من نوع datetime
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy[date_column]):
        df_copy[date_column] = pd.to_datetime(df_copy[date_column], errors='coerce')
    
    # تحويل تواريخ البداية والنهاية إلى datetime إذا كانت من نوع date
    start_datetime = pd.Timestamp(start_date)
    end_datetime = pd.Timestamp(end_date)
    
    # تصفية البيانات
    mask = (df_copy[date_column] >= start_datetime) & (df_copy[date_column] <= end_datetime)
    return df_copy[mask]


@st.cache_data(show_spinner=False, ttl=600)
def filter_by_column_value(df: pd.DataFrame, column: str, value: any) -> pd.DataFrame:
    """
    Filter DataFrame based on a column value.
    
    Args:
        df: DataFrame to filter
        column: Column name to filter on
        value: Required value
        
    Returns:
        Filtered DataFrame
    """
    if column not in df.columns:
        return df
        
    return df[df[column] == value]


@st.cache_data(show_spinner=False, ttl=600)
def customers_with_geo(customers_df: pd.DataFrame, 
                      governorates_df: pd.DataFrame, 
                      cities_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge customer data with governorate and city information.
    
    Args:
        customers_df: Customer DataFrame
        governorates_df: Governorates DataFrame
        cities_df: Cities DataFrame
        
    Returns:
        DataFrame merged with governorate and city information
    """
    # Convert date columns
    customers_df = parse_dates(customers_df, ['created_at', 'updated_at'])
    
    # Merge governorates
    if 'governomate_id' in customers_df.columns and 'id' in governorates_df.columns:
        customers_df = customers_df.merge(
            governorates_df[['id', 'name']],
            left_on='governomate_id',
            right_on='id',
            how='left',
            suffixes=('', '_governorate')
        )
        # Rename name column
        if 'name_governorate' not in customers_df.columns and 'name_y' in customers_df.columns:
            customers_df = customers_df.rename(columns={'name_y': 'governorate_name'})
        elif 'name_governorate' in customers_df.columns:
            customers_df = customers_df.rename(columns={'name_governorate': 'governorate_name'})
    
    # Merge cities
    if 'city_id' in customers_df.columns and 'id' in cities_df.columns:
        customers_df = customers_df.merge(
            cities_df[['id', 'name']],
            left_on='city_id',
            right_on='id',
            how='left',
            suffixes=('', '_city')
        )
        # Rename name column
        if 'name_city' not in customers_df.columns and 'name_y' in customers_df.columns:
            customers_df = customers_df.rename(columns={'name_y': 'city_name'})
        elif 'name_city' in customers_df.columns:
            customers_df = customers_df.rename(columns={'name_city': 'city_name'})
    
    return customers_df


@st.cache_data(show_spinner=False, ttl=600)
def enrich_customers(customers_df: pd.DataFrame, 
                     companies_df: pd.DataFrame, 
                     users_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich customer data with company and user information.
    
    Args:
        customers_df: Customer DataFrame
        companies_df: Companies DataFrame
        users_df: Users DataFrame
        
    Returns:
        DataFrame merged with company and user information
    """
    # Merge companies
    if 'company_id' in customers_df.columns and not companies_df.empty and 'id' in companies_df.columns:
        customers_df = customers_df.merge(
            companies_df[['id', 'name']],
            left_on='company_id',
            right_on='id',
            how='left',
            suffixes=('', '_company')
        )
        # Rename name column
        if 'name_company' not in customers_df.columns and 'name_y' in customers_df.columns:
            customers_df = customers_df.rename(columns={'name_y': 'company_name'})
        elif 'name_company' in customers_df.columns:
            customers_df = customers_df.rename(columns={'name_company': 'company_name'})
    else:
        # Add empty company_name column if companies data is not available
        if 'company_name' not in customers_df.columns:
            customers_df['company_name'] = 'Unknown'
    
    # Merge users (created_by)
    if 'created_by' in customers_df.columns and 'id' in users_df.columns:
        customers_df = customers_df.merge(
            users_df[['id', 'name']],
            left_on='created_by',
            right_on='id',
            how='left',
            suffixes=('', '_user')
        )
        # Rename name column
        if 'name_user' not in customers_df.columns and 'name_y' in customers_df.columns:
            customers_df = customers_df.rename(columns={'name_y': 'created_by_name'})
        elif 'name_user' in customers_df.columns:
            customers_df = customers_df.rename(columns={'name_user': 'created_by_name'})
    
    return customers_df


@st.cache_data(show_spinner=False, ttl=600)
def tickets_with_details(tickets_df: pd.DataFrame, 
                        ticket_categories_df: pd.DataFrame,
                        customers_df: pd.DataFrame,
                        users_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge ticket data with categories, customers, and users information.
    
    Args:
        tickets_df: Tickets DataFrame
        ticket_categories_df: Ticket categories DataFrame
        customers_df: Customers DataFrame
        users_df: Users DataFrame
        
    Returns:
        DataFrame merged with categories, customers, and users information
    """
    # Convert date columns
    tickets_df = parse_dates(tickets_df, ['created_at', 'updated_at', 'closed_at'])
    
    # Calculate resolution time in days for closed tickets
    tickets_df['resolution_time_days'] = np.nan
    closed_mask = tickets_df['status'] == 'closed'
    if 'closed_at' in tickets_df.columns and 'created_at' in tickets_df.columns:
        tickets_df.loc[closed_mask, 'resolution_time_days'] = (
            tickets_df.loc[closed_mask, 'closed_at'] - 
            tickets_df.loc[closed_mask, 'created_at']
        ).dt.total_seconds() / (24 * 3600)
    
    # Merge ticket categories
    category_column = 'category_id'
    if 'ticket_cat_id' in tickets_df.columns:
        category_column = 'ticket_cat_id'
        
    if category_column in tickets_df.columns and 'id' in ticket_categories_df.columns:
        tickets_df = tickets_df.merge(
            ticket_categories_df[['id', 'name']],
            left_on=category_column,
            right_on='id',
            how='left',
            suffixes=('', '_category')
        )
        # Rename name column
        if 'name_category' not in tickets_df.columns and 'name_y' in tickets_df.columns:
            tickets_df = tickets_df.rename(columns={'name_y': 'category_name'})
        elif 'name_category' in tickets_df.columns:
            tickets_df = tickets_df.rename(columns={'name_category': 'category_name'})
    
    # Merge customers
    if 'customer_id' in tickets_df.columns and 'id' in customers_df.columns:
        tickets_df = tickets_df.merge(
            customers_df[['id', 'name']],
            left_on='customer_id',
            right_on='id',
            how='left',
            suffixes=('', '_customer')
        )
        # Rename name column
        if 'name_customer' not in tickets_df.columns and 'name_y' in tickets_df.columns:
            tickets_df = tickets_df.rename(columns={'name_y': 'customer_name'})
        elif 'name_customer' in tickets_df.columns:
            tickets_df = tickets_df.rename(columns={'name_customer': 'customer_name'})
    
    # Merge users (created_by)
    if 'created_by' in tickets_df.columns and 'id' in users_df.columns:
        tickets_df = tickets_df.merge(
            users_df[['id', 'name']],
            left_on='created_by',
            right_on='id',
            how='left',
            suffixes=('', '_created_by')
        )
        # Rename name column
        if 'name_created_by' not in tickets_df.columns and 'name_y' in tickets_df.columns:
            tickets_df = tickets_df.rename(columns={'name_y': 'created_by_name'})
        elif 'name_created_by' in tickets_df.columns:
            tickets_df = tickets_df.rename(columns={'name_created_by': 'created_by_name'})
    
    # Merge users (assigned_to)
    if 'assigned_to' in tickets_df.columns and 'id' in users_df.columns:
        tickets_df = tickets_df.merge(
            users_df[['id', 'name']],
            left_on='assigned_to',
            right_on='id',
            how='left',
            suffixes=('', '_assigned_to')
        )
        # Rename name column
        if 'name_assigned_to' not in tickets_df.columns and 'name_y' in tickets_df.columns:
            tickets_df = tickets_df.rename(columns={'name_y': 'assigned_to_name'})
        elif 'name_assigned_to' in tickets_df.columns:
            tickets_df = tickets_df.rename(columns={'name_assigned_to': 'assigned_to_name'})
    
    return tickets_df


@st.cache_data(show_spinner=False, ttl=600)
def calls_with_details(calls_df: pd.DataFrame, 
                      call_categories_df: pd.DataFrame,
                      call_types_df: Optional[pd.DataFrame],
                      customers_df: pd.DataFrame,
                      users_df: pd.DataFrame) -> pd.DataFrame:
    """
    دمج بيانات المكالمات مع الفئات والأنواع والعملاء والمستخدمين.
    
    Args:
        calls_df: DataFrame للمكالمات
        call_categories_df: DataFrame لفئات المكالمات
        call_types_df: DataFrame لأنواع المكالمات (اختياري)
        customers_df: DataFrame للعملاء
        users_df: DataFrame للمستخدمين
        
    Returns:
        DataFrame مدمج مع معلومات الفئات والأنواع والعملاء والمستخدمين
    """
    # تحويل أعمدة التاريخ
    calls_df = parse_dates(calls_df, ['created_at', 'updated_at'])
    
    # دمج فئات المكالمات
    if 'category_id' in calls_df.columns and 'id' in call_categories_df.columns:
        calls_df = calls_df.merge(
            call_categories_df[['id', 'name']],
            left_on='category_id',
            right_on='id',
            how='left',
            suffixes=('', '_category')
        )
        # إعادة تسمية عمود الاسم
        if 'name_category' not in calls_df.columns and 'name_y' in calls_df.columns:
            calls_df = calls_df.rename(columns={'name_y': 'category_name'})
        elif 'name_category' in calls_df.columns:
            calls_df = calls_df.rename(columns={'name_category': 'category_name'})
    
    # دمج أنواع المكالمات (إذا كانت متوفرة)
    if call_types_df is not None and 'call_type' in calls_df.columns and 'id' in call_types_df.columns:
        calls_df = calls_df.merge(
            call_types_df[['id', 'name']],
            left_on='call_type',
            right_on='id',
            how='left',
            suffixes=('', '_call_type')
        )
        # إعادة تسمية عمود الاسم
        if 'name_call_type' not in calls_df.columns and 'name_y' in calls_df.columns:
            calls_df = calls_df.rename(columns={'name_y': 'call_type_name'})
        elif 'name_call_type' in calls_df.columns:
            calls_df = calls_df.rename(columns={'name_call_type': 'call_type_name'})
    
    # دمج العملاء
    if 'customer_id' in calls_df.columns and 'id' in customers_df.columns:
        calls_df = calls_df.merge(
            customers_df[['id', 'name']],
            left_on='customer_id',
            right_on='id',
            how='left',
            suffixes=('', '_customer')
        )
        # إعادة تسمية عمود الاسم
        if 'name_customer' not in calls_df.columns and 'name_y' in calls_df.columns:
            calls_df = calls_df.rename(columns={'name_y': 'customer_name'})
        elif 'name_customer' in calls_df.columns:
            calls_df = calls_df.rename(columns={'name_customer': 'customer_name'})
    
    # دمج المستخدمين (created_by)
    if 'created_by' in calls_df.columns and 'id' in users_df.columns:
        calls_df = calls_df.merge(
            users_df[['id', 'name']],
            left_on='created_by',
            right_on='id',
            how='left',
            suffixes=('', '_user')
        )
        # إعادة تسمية عمود الاسم
        if 'name_user' not in calls_df.columns and 'name_y' in calls_df.columns:
            calls_df = calls_df.rename(columns={'name_y': 'created_by_name'})
        elif 'name_user' in calls_df.columns:
            calls_df = calls_df.rename(columns={'name_user': 'created_by_name'})
    
    return calls_df


@st.cache_data(show_spinner=False, ttl=600)
def group_by_period(df: pd.DataFrame, 
                   date_column: str, 
                   period: str = 'month', 
                   value_column: Optional[str] = None,
                   agg_func: str = 'count') -> pd.DataFrame:
    """
    تجميع البيانات حسب فترة زمنية.
    
    Args:
        df: DataFrame المراد تجميعه
        date_column: اسم عمود التاريخ
        period: الفترة الزمنية ('day', 'week', 'month', 'quarter', 'year')
        value_column: اسم العمود المراد تجميعه (اختياري، إذا كان None سيتم استخدام عمود التاريخ)
        agg_func: دالة التجميع ('count', 'sum', 'mean', 'min', 'max')
        
    Returns:
        DataFrame مجمع حسب الفترة الزمنية
    """
    if date_column not in df.columns:
        return pd.DataFrame()
    
    # تحويل عمود التاريخ إلى datetime إذا لم يكن كذلك
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    
    # إزالة الصفوف ذات القيم المفقودة في عمود التاريخ
    df = df.dropna(subset=[date_column])
    
    # تحديد العمود المراد تجميعه
    if value_column is None:
        value_column = date_column
    
    # تحديد دالة التجميع
    agg_function = {
        'count': 'count',
        'sum': 'sum',
        'mean': 'mean',
        'min': 'min',
        'max': 'max'
    }.get(agg_func, 'count')
    
    # تحديد تنسيق الفترة الزمنية
    period_format = {
        'day': '%Y-%m-%d',
        'week': '%Y-%U',
        'month': '%Y-%m',
        'quarter': '%Y-Q%q',
        'year': '%Y'
    }.get(period, '%Y-%m')
    
    # تجميع البيانات
    if period == 'quarter':
        # معالجة خاصة للربع السنوي
        df['period'] = df[date_column].dt.to_period('Q').astype(str)
    else:
        df['period'] = df[date_column].dt.strftime(period_format)
    
    # تجميع البيانات حسب الفترة
    result = df.groupby('period').agg({value_column: agg_function}).reset_index()
    result = result.rename(columns={value_column: 'value'})
    
    # ترتيب النتائج حسب الفترة
    result = result.sort_values('period')
    
    return result