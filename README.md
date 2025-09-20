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
- **Google Drive Integration**: Data storage and retrieval using Google Drive API

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

## Google Drive Authentication Setup

This application uses Google Drive API for data storage and retrieval. When you encounter the error `invalid_grant: Token has been expired or revoked`, follow these steps to refresh your authentication:

### Setting Up Google Drive API Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API for your project
4. Create OAuth 2.0 credentials (Client ID and Client Secret)
5. Set up the OAuth consent screen with appropriate scopes (`https://www.googleapis.com/auth/drive`)

### Configuring Authentication in the Application

Store your Google API credentials in one of these locations:

1. **Environment Variables** (recommended for local development):
   Create a `.env` file in the project root with:
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   GOOGLE_TOKEN=your_access_token
   GOOGLE_REFRESH_TOKEN=your_refresh_token
   GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token
   DRIVE_FOLDER_ID=your_drive_folder_id
   ```

2. **Streamlit Secrets** (recommended for deployment):
   Create a `.streamlit/secrets.toml` file with:
   ```toml
   [google]
   client_id = "your_client_id"
   client_secret = "your_client_secret"
   token = "your_access_token"
   refresh_token = "your_refresh_token"
   token_uri = "https://oauth2.googleapis.com/token"
   
   [drive]
   folder_id = "your_drive_folder_id"
   ```

### Refreshing Expired Tokens

When you encounter a token expiration error:

1. Generate a new access token using your refresh token:
   - Use the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
   - Configure it with your Client ID and Client Secret
   - Select the Drive API v3 scope
   - Exchange authorization code for tokens
   - Copy the new access token

2. Update your credentials:
   - Replace the expired `GOOGLE_TOKEN` in your `.env` file or
   - Update the `token` value in `.streamlit/secrets.toml`

3. Restart the application

### Troubleshooting Authentication Issues

- Ensure all required credentials are provided
- Verify the refresh token is valid and has not been revoked
- Check that the correct scopes are configured
- Confirm the Drive folder ID exists and is accessible
- Clear the application cache from the Data Management page if needed

## License

[Specify License Information]