# JANSSEN CRM

A Streamlit-based Customer Relationship Management (CRM) system for data analysis and visualization.

## Project Overview

JANSSEN CRM is a web application built with Streamlit that provides comprehensive customer relationship management capabilities. The application offers various analytical features including customer analysis, call tracking, ticket management, and performance metrics.

## Features

- **Authentication System**: Secure login functionality
- **Data Management**: Tools for managing and uploading data
- **Customer Analysis**: Detailed customer insights and metrics
- **Call Analysis**: Track and analyze customer calls
- **Ticket Management**: Monitor and manage support tickets
- **Action Items**: Track action items and follow-ups
- **Performance Analysis**: Measure and visualize performance metrics

## Project Structure

```
├── .streamlit/            # Streamlit configuration
├── auth/                  # Authentication modules
├── filter/                # Data filtering components
├── lode_data/             # Data loading utilities
├── pages/                 # Application pages
├── process/               # Data processing modules
├── streamlit/             # Streamlit specific components
└── visualize/             # Visualization utilities
```

## Installation

1. Clone the repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables (if needed)

## Usage

To run the application:

```bash
streamlit run login.py
```

This will start the application with the login page as the entry point.

## Dependencies

- streamlit==1.30.0
- pandas==2.1.3
- numpy==1.26.2
- plotly==5.18.0
- google-api-python-client==2.108.0
- folium==0.14.0
- matplotlib==3.8.2
- seaborn==0.13.0
- sqlalchemy==2.0.25
- PyMySQL==1.1.0

For a complete list of dependencies, see `requirements.txt`.

## Pages

- Data Management
- Customer Analysis
- Customer Call Analysis
- Tickets and Calls Analysis
- Ticket Items
- Actions Items Analysis
- Descriptions Analysis
- Performance Analysis

## License

[Specify License Information]