# JanssenCRM Database Schema

This document provides a comprehensive overview of the JanssenCRM database schema and sample data.

## Database Overview

The JanssenCRM database contains 27 tables that manage customer relationships, calls, tickets, users, and system administration.

## Tables Overview

### Core Business Tables
- **companies** - Company information
- **customers** - Customer records
- **customercall** - Customer call logs
- **customer_phones** - Customer phone numbers
- **tickets** - Support tickets
- **ticketcall** - Ticket-related calls
- **ticket_items** - Ticket line items
- **ticket_item_maintenance** - Maintenance items
- **ticket_item_change_same** - Same item changes
- **ticket_item_change_another** - Different item changes
### Reference/Lookup Tables
- **call_categories** - Call categorization
- **ticket_categories** - Ticket categorization
- **request_reasons** - Reason codes for requests
- **product_info** - Product information
- **governorates** - Geographic regions
- **cities** - City information

### User Management
- **users** - System users
- **permissions** - System permissions

### System/Audit Tables
- **activities** - Activity definitions
- **activity_logs** - Activity tracking
- **audit_logs** - System audit trail
- **entities** - Entity definitions


## Detailed Schema

### companies
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| name | varchar | NO | null | |
| created_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED |

### customers
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| company_id | int | YES | null | |
| name | varchar | YES | null | |
| governomate_id | int | YES | null | |
| city_id | int | YES | null | |
| address | varchar | YES | null | |
| notes | text | YES | null | |
| created_by | int | YES | null | |
| created_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| updated_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

### customercall
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| company_id | int | YES | null | |
| customer_id | int | YES | null | |
| call_type | tinyint | YES | null | |
| category_id | int | YES | null | |
| description | text | YES | null | |
| call_notes | text | YES | null | |
| call_duration | varchar | YES | null | |
| created_by | int | YES | null | |
| created_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| updated_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

### customer_phones
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| company_id | int | NO | null | |
| customer_id | int | NO | null | |
| phone | varchar | YES | null | |
| phone_type | int | YES | null | |
| created_by | int | YES | null | |
| created_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| updated_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

### users
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| company_id | int | YES | null | |
| name | varchar | NO | null | |
| email | varchar | NO | null | |
| password | varchar | NO | null | |
| phone | varchar | YES | null | |
| is_active | tinyint | YES | 1 | |
| created_by | int | YES | null | |
| created_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| updated_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

### tickets
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| company_id | int | YES | null | |
| customer_id | int | YES | null | |
| category_id | int | YES | null | |
| reason_id | int | YES | null | |
| status | tinyint | YES | 1 | |
| priority | tinyint | YES | 1 | |
| description | text | YES | null | |
| notes | text | YES | null | |
| assigned_to | int | YES | null | |
| created_by | int | YES | null | |
| created_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| updated_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

### call_categories
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| name | varchar | YES | null | |
| created_by | int | YES | null | |
| created_at | datetime | YES | null | |
| updated_at | datetime | YES | null | |
| company_id | int | YES | null | |

### governorates
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| name | varchar | NO | null | |

### cities
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| name | varchar | NO | null | |
| governorate_id | int | NO | null | |

### roles
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | auto_increment |
| name | varchar | NO | null | |
| description | text | YES | null | |
| company_id | int | YES | null | |
| created_by | int | YES | null | |
| created_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| updated_at | datetime | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

### permissions
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | int | NO | null | |
| tittle | text | YES | null | |
| default_conditions | json | YES | null | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| updated_at | timestamp | YES | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |
| key | int | YES | null | |
| description | text | YES | null | |

### audit_logs
| Column | Type | Nullable | Default | Extra |
|--------|------|----------|---------|-------|
| id | bigint | NO | null | auto_increment |
| user_id | varchar | YES | null | |
| action | varchar | NO | null | |
| target_entity | varchar | YES | null | |
| target_id | varchar | YES | null | |
| old_value | text | YES | null | |
| new_value | text | YES | null | |
| timestamp | timestamp | NO | CURRENT_TIMESTAMP | DEFAULT_GENERATED |

## Sample Data

### Companies
| id | name | created_at |
|----|------|------------|
| 1 | janssen | 2025-07-26T15:57:46.000Z |
| 2 | englender | 2025-07-26T15:57:46.000Z |

### Users
| id | company_id | name | username | password | created_by | is_active | created_at | updated_at |
|----|------------|------|----------|----------|------------|-----------|------------|------------|
| 1 | 1 | 1 | janssen | 1 | 1 | 1 | 2025-07-20T11:06:34.000Z | 2025-07-26T16:00:11.000Z |
| 2 | 2 | englender | englender | 1 | 1 | 1 | 2025-07-26T16:00:23.000Z | 2025-07-26T16:00:23.000Z |

### Customers
| id | company_id | name | governomate_id | city_id | address | notes | created_by | created_at | updated_at |
|----|------------|------|----------------|---------|---------|-------|------------|------------|------------|
| 1 | 1 | محمد خالد محمدfsdds | 1 | 1 | بجوار الموقفaf | ssf | 1 | 2025-07-26T15:56:27.000Z | 2025-08-04T08:25:10.000Z |
| 2 | 1 | 0123333 | 2 | 2 | السعيديه مركز بلبيس محافظه الشرقيه جوار مسجد التوحيد4f33 | 333 | 1 | 2025-07-26T16:01:23.000Z | 2025-08-04T06:50:08.000Z |
| 3 | 2 | 0123456f | 1 | 1 | 4d | 45d | 2 | 2025-07-26T16:11:11.000Z | 2025-08-04T07:28:01.000Z |

### Customer Calls
| id | company_id | customer_id | call_type | category_id | description | call_notes | call_duration | created_by | created_at | updated_at |
|----|------------|-------------|-----------|-------------|-------------|------------|---------------|------------|------------|------------|
| 1 | 1 | 1 | 2 | 1 | يبببب | يبببب | 04:00 | 1 | 2025-07-26T15:56:27.000Z | 2025-07-26T15:56:27.000Z |
| 2 | 1 | 2 | 1 | 1 | 12 | 12 | 01:00 | 1 | 2025-07-26T16:01:23.000Z | 2025-07-26T16:01:23.000Z |
| 3 | 2 | 3 | 1 | 1 | 4 | 4 | 01:00 | 2 | 2025-07-26T16:11:11.000Z | 2025-07-26T16:11:11.000Z |

### Governorates
| id | name |
|----|------|
| 1 | الشرقيه |
| 2 | القاهره |

### Cities
| id | name | governorate_id |
|----|------|----------------|
| 1 | بلبيس | 1 |
| 2 | مدينه نصر | 2 |

### Call Categories
| id | name | created_by | created_at | updated_at | company_id |
|----|------|------------|------------|------------|------------|
| 1 | 111 | null | null | null | null |

### Tickets
| id | company_id | customer_id | ticket_cat_id | description | status | priority | created_by | created_at | closed_at | updated_at | closing_notes | closed_by |
|----|------------|-------------|---------------|-------------|--------|----------|------------|------------|-----------|------------|---------------|----------|
| 1 | 1 | 1 | 1 | ثق | 0 | 0 | 1 | 2025-07-26T15:59:17.000Z | null | 2025-07-26T15:59:17.000Z | null | null |
| 2 | 2 | 1 | 1 | 90- | 0 | 0 | 2 | 2025-07-26T16:10:22.000Z | null | 2025-07-26T16:10:22.000Z | null | null |

### Customer Phones
| id | company_id | customer_id | phone | phone_type | created_by | created_at | updated_at |
|----|------------|-------------|-------|------------|------------|------------|------------|
| 1 | 1 | 1 | 01234567890 | 1 | 1 | 2025-07-26T15:56:27.000Z | 2025-07-26T15:56:27.000Z |

### Activities
| id | name | description | created_at |
|----|------|-------------|------------|
| 1 | User login | تسجيل دخول المستخدم إلى النظام | 2025-08-03T08:31:53.000Z |
| 2 | User logout | تسجيل خروج المستخدم من النظام | 2025-08-03T08:31:53.000Z |

### Activity Logs
| id | entity_id | record_id | activity_id | user_id | details | created_at |
|----|-----------|-----------|-------------|---------|---------|------------|
| 323 | 2 | 1 | 112 | 1 | null | 2025-08-04T07:15:16.000Z |
| 324 | 2 | 1 | 112 | 1 | null | 2025-08-04T07:15:46.000Z |

### Entities
| id | name | created_at |
|----|------|------------|
| 1 | users | 2025-08-02T06:12:03.000Z |
| 2 | customers | 2025-08-02T06:12:03.000Z |

### Permissions
*No sample data available - table is empty*

### Product Info
| id | company_id | product_name | created_by | created_at | updated_at |
|----|------------|--------------|------------|------------|------------|
| 1 | 1 | كتراكت | 1 | 2025-07-26T15:58:19.000Z | 2025-07-26T15:58:19.000Z |
| 2 | 1 | المانى | 1 | 2025-07-26T15:58:30.000Z | 2025-07-26T15:58:30.000Z |

### Request Reasons
| id | name | created_by | created_at | updated_at | company_id |
|----|------|------------|------------|------------|------------|
| 1 | مشكله ب السوست | 1 | 2025-07-26T15:57:10.000Z | 2025-07-26T15:57:10.000Z | 1 |

### Ticket Categories
| id | name | created_by | created_at | updated_at | company_id |
|----|------|------------|------------|------------|------------|
| 1 | شكوى | 1 | 2025-07-26T15:57:00.000Z | 2025-07-26T15:57:00.000Z | 1 |
| 2 | اخرى | 1 | 2025-08-02T06:24:32.000Z | 2025-08-02T06:24:32.000Z | 1 |

### Ticket Items
| id | company_id | ticket_id | product_id | product_size | quantity | purchase_date | purchase_location | request_reason_id | request_reason_detail | inspected | created_by | created_at |
|----|------------|-----------|------------|--------------|----------|---------------|-------------------|-------------------|----------------------|-----------|------------|------------|
| 1 | 1 | 1 | 3 | 120*200*3 | 1 | 2025-07-25T21:00:00.000Z | 12 | 1 | 12 | null | 1 | 2025-07-26T15:59:17.000Z |
| 2 | 2 | 2 | 3 | 120*200*3 | 1 | 2025-07-25T21:00:00.000Z | 12 | 1 | i0- | 1 | 2 | 2025-07-26T16:10:22.000Z |

### Ticket Calls
| id | company_id | ticket_id | call_type | call_cat_id | description | call_notes | call_duration | created_by | created_at |
|----|------------|-----------|-----------|-------------|-------------|------------|---------------|------------|------------|
| 1 | 1 | 1 | 0 | 1 | 12212 |  | 0 | 1 | 2025-07-26T15:59:17.000Z |
| 2 | 2 | 2 | 0 | 1 | 0- |  | 0 | 2 | 2025-07-26T16:10:22.000Z |

### Ticket Item Change Another
| ticket_item_id | product_id | product_size | cost | client_approval | refusal_reason | pulled | delivered | created_by | created_at | company_id |
|----------------|------------|--------------|------|-----------------|----------------|--------|-----------|------------|------------|------------|
| 12 | 3 | fgfgg | 1 | 0 | sdf | 0 | null | 2 | 2025-08-02T10:51:45.000Z | 2 |

### Ticket Item Change Same
| ticket_item_id | product_id | product_size | cost | client_approval | pulled | delivered | created_by | created_at | company_id |
|----------------|------------|--------------|------|-----------------|--------|-----------|------------|------------|------------|
| 2 | 3 | null | null | null | null | null | 2 | 2025-08-04T11:09:10.000Z | 2 |

### Ticket Item Maintenance
| ticket_item_id | maintenance_steps | maintenance_cost | client_approval | pulled | delivered | created_by | created_at | company_id |
|----------------|-------------------|------------------|-----------------|--------|-----------|------------|------------|------------|
| 6 | ddff | 23 | 1 | 1 | 1 | 1 | 2025-07-30T09:17:02.000Z | 1 |
| 7 | df | 1 | null | 1 | null | 1 | 2025-07-31T06:24:07.000Z | 1 |

## Key Relationships

1. **Companies** → **Customers**: One-to-many relationship
2. **Customers** → **Customer Calls**: One-to-many relationship
3. **Customers** → **Customer Phones**: One-to-many relationship
4. **Customers** → **Tickets**: One-to-many relationship
5. **Governorates** → **Cities**: One-to-many relationship
6. **Cities** → **Customers**: One-to-many relationship
7. **Users** → **Customers**: One-to-many (created_by)
8. **Users** → **Customer Calls**: One-to-many (created_by)
9. **Call Categories** → **Customer Calls**: One-to-many relationship

## Notes

- The database uses UTF-8 encoding to support Arabic text
- Most tables include audit fields (created_by, created_at, updated_at)
- The system supports multi-company architecture through company_id fields
- Call descriptions and notes support Arabic language content
