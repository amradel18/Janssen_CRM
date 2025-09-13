import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta


def create_pie_chart(data, names, values, title, color_discrete_sequence=None):
    """
    Create a pie chart using Plotly
    
    Args:
        data: DataFrame containing the data
        names: Column name for pie chart segments
        values: Column name for pie chart values
        title: Chart title
        color_discrete_sequence: Optional color sequence
        
    Returns:
        Plotly figure object
    """
    fig = px.pie(
        data, 
        names=names, 
        values=values, 
        title=title,
        color_discrete_sequence=color_discrete_sequence
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': -0.2,
            'xanchor': 'center',
            'x': 0.5
        }
    )
    
    return fig


def create_bar_chart(data, x, y, title, color=None, orientation='v'):
    """
    Create a bar chart using Plotly
    
    Args:
        data: DataFrame containing the data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Optional column name for color
        orientation: 'v' for vertical bars, 'h' for horizontal bars
        
    Returns:
        Plotly figure object
    """
    fig = px.bar(
        data, 
        x=x, 
        y=y, 
        title=title,
        color=color,
        orientation=orientation
    )
    
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title=x,
        yaxis_title=y
    )
    
    return fig


def create_line_chart(data, x, y, title, color=None):
    """
    Create a line chart using Plotly
    
    Args:
        data: DataFrame containing the data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Optional column name for color
        
    Returns:
        Plotly figure object
    """
    fig = px.line(
        data, 
        x=x, 
        y=y, 
        title=title,
        color=color
    )
    
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title=x,
        yaxis_title=y
    )
    
    return fig


def create_scatter_chart(data, x, y, title, color=None, size=None, hover_name=None):
    """
    Create a scatter chart using Plotly
    
    Args:
        data: DataFrame containing the data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Optional column name for color
        size: Optional column name for point size
        hover_name: Optional column name for hover text
        
    Returns:
        Plotly figure object
    """
    fig = px.scatter(
        data, 
        x=x, 
        y=y, 
        title=title,
        color=color,
        size=size,
        hover_name=hover_name
    )
    
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title=x,
        yaxis_title=y
    )
    
    return fig


# Alias for create_scatter_chart to maintain compatibility
def create_scatter_plot(data, x, y, title, color=None, size=None, hover_name=None):
    """
    Alias for create_scatter_chart function
    
    Args:
        data: DataFrame containing the data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Optional column name for color
        size: Optional column name for point size
        hover_name: Optional column name for hover text
        
    Returns:
        Plotly figure object
    """
    return create_scatter_chart(data, x, y, title, color, size, hover_name)


def create_heatmap(data, x, y, z, title):
    """
    Create a heatmap using Plotly
    
    Args:
        data: DataFrame containing the data
        x: Column name for x-axis
        y: Column name for y-axis
        z: Column name for z-axis (values)
        title: Chart title
        
    Returns:
        Plotly figure object
    """
    # Pivot the data for heatmap
    pivot_table = data.pivot_table(index=y, columns=x, values=z, aggfunc='mean')
    
    fig = px.imshow(
        pivot_table,
        title=title,
        labels=dict(x=x, y=y, color=z),
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    
    return fig


def create_time_series(data, date_column, value_column, title, color=None):
    """
    Create a time series chart using Plotly
    
    Args:
        data: DataFrame containing the data
        date_column: Column name for dates
        value_column: Column name for values
        title: Chart title
        color: Optional column name for color
        
    Returns:
        Plotly figure object
    """
    # Ensure date column is datetime
    data[date_column] = pd.to_datetime(data[date_column], errors='coerce')
    
    fig = px.line(
        data, 
        x=date_column, 
        y=value_column, 
        title=title,
        color=color
    )
    
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='Date',
        yaxis_title=value_column
    )
    
    return fig


def create_metric_card(label, value, delta=None, delta_suffix="%"):
    """
    Create a metric card using Streamlit
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta value
        delta_suffix: Suffix for delta value
    """
    if delta is not None:
        st.metric(label=label, value=value, delta=f"{delta:.1f}{delta_suffix}")
    else:
        st.metric(label=label, value=value)


def create_multi_metric_row(metrics_data):
    """
    Create a row of metric cards
    
    Args:
        metrics_data: List of dictionaries with keys 'label', 'value', and optionally 'delta'
    """
    cols = st.columns(len(metrics_data))
    
    for i, metric in enumerate(metrics_data):
        with cols[i]:
            if 'delta' in metric:
                create_metric_card(metric['label'], metric['value'], metric['delta'])
            else:
                create_metric_card(metric['label'], metric['value'])


def create_gauge_chart(value, title, min_value=0, max_value=100, threshold_value=None):
    """
    Create a gauge chart using Plotly
    
    Args:
        value: Value to display
        title: Chart title
        min_value: Minimum value
        max_value: Maximum value
        threshold_value: Optional threshold value
        
    Returns:
        Plotly figure object
    """
    # Determine color based on value and threshold
    if threshold_value is not None:
        if value < threshold_value:
            color = "red"
        else:
            color = "green"
    else:
        color = "blue"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        gauge={
            'axis': {'range': [min_value, max_value]},
            'bar': {'color': color},
            'steps': [
                {'range': [min_value, max_value/2], 'color': "lightgray"},
                {'range': [max_value/2, max_value], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': threshold_value if threshold_value is not None else max_value
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    
    return fig


def create_funnel_chart(data, x, y, title):
    """
    Create a funnel chart using Plotly
    
    Args:
        data: DataFrame containing the data
        x: Column name for x-axis (values)
        y: Column name for y-axis (stages)
        title: Chart title
        
    Returns:
        Plotly figure object
    """
    fig = px.funnel(
        data, 
        x=x, 
        y=y, 
        title=title
    )
    
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    
    return fig


def create_sunburst_chart(data, path, values, title):
    """
    Create a sunburst chart using Plotly
    
    Args:
        data: DataFrame containing the data
        path: List of column names for hierarchical path
        values: Column name for values
        title: Chart title
        
    Returns:
        Plotly figure object
    """
    fig = px.sunburst(
        data, 
        path=path, 
        values=values, 
        title=title
    )
    
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    
    return fig