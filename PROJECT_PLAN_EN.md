# Data & Analytics Project Plan – Janssen CRM (Updated)

This document defines a structured, practical plan to build the Janssen CRM data pipeline and dashboard using Google Drive as a data source and a modular architecture. This update adds the main app entry file, login, and display pages.

## Goals
- Clear end-to-end data flow from source (DB/Drive) to analytics/visuals.
- Modular structure per stage (Load → Process → Visualize → Filter).
- Support incremental export to Drive and direct in-memory reads from Drive.
- Deliver a Streamlit app with pages, authentication, and filters.

## Project Directory Structure
```
dashboard/
├─ app.py                                 # Main entrypoint (Streamlit Home)
├─ pages/                                  # Display pages
│  ├─ 1_Customer_Page.py
│  ├─ 2_Calls_Page.py
│  ├─ 3_Tickets_Page.py
│  └─ 4_Requests_Page.py
├─ auth/
│  └─ login.py                             # Simple login (admin/admin)
├─ load_data/
│  ├─ load_database_and_upload_drive.py    # Incremental export from DB to Drive
│  └─ load_data_in_drive.py                # Read tables directly from Drive
├─ process/
│  ├─ kpis.py                              # KPIs functions
│  └─ table_query.py                       # Joins, grouping, parsing, enrich
├─ visualize/
│  ├─ charts.py                            # Plotly/Altair charts
│  └─ style.py                             # Theme & styles
└─ filter/
   ├─ filter_page.py                       # Filters logic (optional standalone)
   └─ mappings.py                          # ID→Name mappings (companies, cities,...)
```

Note: You can add `utils/` later if common helpers emerge.

## Authentication (Login)
- Purpose: Gate access to pages until the user is authenticated.
- Simple initial approach:
  - In auth/login.py, implement a small login form that validates username == "admin" and password == "admin".
  - Use st.session_state["authenticated"] to control access.
  - In app.py, if not authenticated, show the login form (hide content). On success, set authenticated and rerun. Add a Logout button to clear the session.
  - Later, this can be replaced with environment vars or a DB-backed auth.
- Page guard:
  - At the top of each file under pages/, add a lightweight guard: if not session_state["authenticated"], display an error and stop the script. This prevents viewing pages without login (even if visible in the sidebar).

## Quick Start – Practical Steps (Phase 1)
0) Add login: create auth/login.py and integrate it in app.py with admin/admin and session_state.
1) Create folders and empty modules: load_data/, process/, visualize/, filter/.
2) Move Google Drive helpers from database.py to load_data/load_data_in_drive.py (get_drive_service, get_file_id_by_name, read_csv_from_drive_by_name, upload_or_update_csv_on_drive if needed).
3) Implement load_tables_from_drive(table_names) returning {table_name: DataFrame} using DRIVE_FOLDER_ID.
4) Build process/table_query.py with main joins (customers_with_geo, enrich_customers, tickets_with_details, calls_with_details) and parse_dates.
5) Implement KPIs in process/kpis.py.
6) Build filter/mappings.py to extract mappings (ID→Name) and cache them.
7) Build filter/filter_page.py for UI filters; return selected values to apply on DataFrames.
8) Wire pages/1..4 to use the new functions; enable caches.
9) Add Refresh Data button to trigger export_incremental_tables_to_drive, then clear caches and reload.
10) Smoke tests: key columns present, UTF-8 encodings, datetime conversions.

The rest of the plan (data flow, joins, function contracts, roadmap, and quality checks) remains as previously documented below.

---

1) Quick Start (Practical Steps)
- Create folders and files: load_data/, process/, visualize/, filter/
- Extract Drive helpers into load_data/load_data_in_drive.py: get_drive_service, get_file_id_by_name, read_csv_from_drive_by_name, upload_or_update_csv_on_drive (optional)
- Implement load_tables_from_drive(table_names) to return a dict {table_name: DataFrame} from DRIVE_FOLDER_ID
- Build process/table_query.py: joins for customers, tickets, calls + parse_dates
- Build process/kpis.py: initial KPIs (totals, distributions, average resolution time)
- Build filter/mappings.py: ID→Name mappings with caching
- Build filter/filter_page.py: UI for filters and apply_filters
- Wire pages/1..4 to the new modules, enable caching
- Add a Refresh Data button to run export_incremental_tables_to_drive, clear cache, reload
- Sanity checks: keys (IDs), UTF-8 encoding, datetime conversion

2) Directory Structure
- dashboard/
  - load_data/
    - load_database_and_upload_drive.py   # Pull from DB and upload to Drive (CSV/Excel), incremental
    - load_data_in_drive.py               # Read Drive files by name directly to DataFrame
  - process/
    - kpis.py                             # KPI computations
    - table_query.py                      # Joins, transformations, groupby helpers
  - visualize/
    - charts.py                           # Plotly/Altair chart builders
    - style.py                            # Theme, colors, styles
  - filter/
    - filter_page.py                      # Filter logic to power the app page
    - mappings.py                         # ID→Name dictionaries (Companies, Cities, ...)

3) Drive Tables (as-is, matching DB names)
- call_categories, call_types, cities, companies, customer_phones,
  governorates, product_info, request_reasons, ticket_categories, ticket_item_change_another,
  ticket_item_change_same, ticket_item_maintenance, ticket_items, ticketcall, tickets, users

4) Integration with current code
- Use existing logic in database.py where available:
  - get_engine() for DB connectivity
  - get_drive_service() to authenticate Drive
  - get_file_id_by_name(), read_csv_from_drive_by_id(), upload_or_update_csv_on_drive()
  - export_incremental_tables_to_drive() to upload all tables incrementally to Drive
- Keep Drive filenames identical to table names (customers.csv, tickets.csv, ...)
- Use janssencrm_database_schema.md for join keys and field definitions

5) Function Contracts (by layer)
- load_data/load_data_in_drive.py
  - get_drive_service() -> service
  - get_file_id_by_name(filename: str, service, folder_id: Optional[str]) -> Optional[str]
  - read_csv_from_drive_by_name(filename: str, service, folder_id: Optional[str]) -> pd.DataFrame
  - load_tables_from_drive(table_names: List[str], service, folder_id: Optional[str]) -> Dict[str, pd.DataFrame]
- load_data/load_database_and_upload_drive.py
  - export_incremental_tables_to_drive(table_names: List[str], folder_id: str, pk_column_map: Optional[Dict[str, str]] = None) -> Dict[str, Dict]
  - upsert_single_table(tbl: str, pk: str, engine, service, folder_id: str) -> Dict
- process/table_query.py
  - parse_dates(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame
  - customers_with_geo(customers, cities, governorates) -> pd.DataFrame
  - enrich_customers(customers, companies, users) -> pd.DataFrame
  - tickets_with_details(tickets, ticket_categories, users, customers) -> pd.DataFrame
  - calls_with_details(ticketcall, call_types, call_categories, users, customers) -> pd.DataFrame
  - groupby_count(df, by: List[str], date_col: Optional[str] = None, freq: Optional[str] = None) -> pd.DataFrame
- process/kpis.py
  - kpi_total_customers(customers) -> int
  - kpi_active_customers(ticketcall, tickets, period_days: int) -> int
  - kpi_tickets_by_status(tickets) -> pd.DataFrame (status, count)
  - kpi_avg_resolution_time(tickets) -> float (hours/days)
  - kpi_calls_distribution_by_type(ticketcall, call_types) -> pd.DataFrame
  - kpi_requests_per_company(tickets, companies) -> pd.DataFrame
- visualize/style.py
  - get_theme() -> Dict
  - apply_streamlit_theme() -> None
- visualize/charts.py
  - chart_trend(df, x: str, y: str, color: Optional[str] = None)
  - chart_bar(df, x: str, y: str)
  - chart_pie(df, names: str, values: str)
  - chart_heatmap(df, rows: str, cols: str, values: str)
- filter/mappings.py
  - build_mappings(dfs: Dict[str, pd.DataFrame]) -> Dict[str, Dict]
  - map_id_to_name(df, col: str, mapping: Dict, new_col: str) -> pd.DataFrame
- filter/filter_page.py
  - build_filters_ui(dfs: Dict[str, pd.DataFrame], mappings: Dict[str, Dict]) -> Dict[str, Any]
  - apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame

6) Data Flow
- Load:
  - From DB (if available) -> upload to Drive as CSV/Excel with consistent naming
  - Or read directly from Drive into memory (no local downloads)
- Process:
  - Clean, parse dates, join tables, compute analysis-ready frames
  - Compute KPIs
- Visualize:
  - Build consistent charts and cards for KPIs
- Filter:
  - A unified filter layer feeding all pages

7) Join Map (based on the schema)
- customers.company_id -> companies.id -> companies.name as company_name
- customers.governorate_id -> governorates.id -> governorates.name as governorate_name
- customers.city_id -> cities.id -> cities.name as city_name
- customers.created_by -> users.id -> users.name as created_by_name
- tickets.customer_id -> customers.id
- tickets.category_id -> ticket_categories.id -> ticket_categories.name as ticket_category_name
- tickets.created_by / tickets.closed_by -> users.id -> users.name
- ticketcall.customer_id -> customers.id
- ticketcall.call_type -> call_types.id -> call_types.name as call_type_name
- ticketcall.category_id -> call_categories.id -> call_categories.name as call_category_name

8) Filter Design (App Page)
- Fields: [company_id, name, governorate_id, city_id, created_by, created_at]
- Replace IDs with names via mappings
- Return selected values and a filtered DataFrame usable by all pages

9) Visualization Guidelines
- Time series (trend) by created_at
- Bar charts for categorical breakdowns
- Pie/Donut for distributions
- Optional heatmap/treemap
- Centralized theme (colors, fonts, spacing) in style.py

10) Caching and Config
- Use st.cache_data for Drive reads and mapping builds
- Clear cache after running incremental upload (Refresh Data)
- Central constants (temporary): DRIVE_FOLDER_ID, SCOPES, TOKEN_FILE, CLIENT_SECRETS_FILE

11) Roadmap (Milestones)
- M1: Move Drive helpers, implement load_tables_from_drive
- M2: Build table_query joins and parse_dates
- M3: Implement first KPIs (6–8)
- M4: Theme and core charts
- M5: Filter mappings and filter page
- M6: Wire existing pages to new modules, add caching
- M7: Admin/Refresh button to trigger export_incremental_tables_to_drive
- M8: Functional tests, edge-case handling (missing tables, column diffs, encoding)

12) Quality Checks
- Referential keys (IDs) are valid integers with no stray spaces
- UTF-8 encoding for reads/writes
- Convert date columns to timezone-aware datetime where applicable

13) Expected Outcomes
- One-click incremental updates to Drive tables
- Instant in-memory reads for the app
- Unified processing layer to accelerate new KPIs and dashboards
- A flexible filter page feeding all analytics pages