# Requirements Document (V1)
## Self-Hosted, Offline-First Documentation Engine

**Goal**: A lightweight, self-hostable platform that transforms speech/text into structured, continuous case files. Focus on security, zero-ops deployment, zero-trust principles, and configurable categories. No appointment scheduling.

### 1. Context & Guiding Principles

#### 1.1 Guiding Principles
*   **Stay lightweight**: No appointment scheduling, no complex case management beyond the case file concept.
*   **Offline-first**: Works without network (PWA), synchronization later.
*   **Zero-ops**: Deploy via Docker Compose, sensible defaults, automatic DB migrations.
*   **Zero-trust**: Every request authenticated, least privilege, strict scope model.
*   **Configurable not hardcoded**: Categories/guidelines/exports without code changes.
*   **Auditable**: Changes traceable (audit log, versioning).

#### 1.2 Non-Goals (explicitly not in V1)
*   Appointment scheduling/calendar/route planning
*   Billing, cash register processes, industry-specific workflows
*   Direct ePA/TI integration
*   Fully automatic integrations into HIS/DMS (only export/copy flows)

### 2. Terms & Domain Model

#### 2.1 Terms
*   **Tenant (Organization)**: Top-level entity for tenant separation.
*   **Group**: Work area/team within a tenant.
*   **Case File**: Smallest functional unit; container for continuous entries.
*   **Entry**: Append-only documentation entry (text + optional structured data).
*   **Category (CategoryDefinition)**: Configurable structure/guidance for entries.
*   **Role**: Permission set for users.
*   **Case Owner (Stakeholder)**: Stakeholder with read-only access to a specific case file for high transparency.

#### 2.2 Core Assumption
*   A case file is the smallest unit and is assigned to at least one group.
*   **Decision (Q1)**: A case file belongs to exactly one group (single-group case file).

### 3. Roles & Permissions (RBAC + Scope)

#### 3.1 Roles (V1)
*   **Admin (Tenant Admin)**: System setup, user management, global configuration, full rights.
*   **Superuser (Group Admin)**: Configuration within own group (categories, export templates), export of case files, case file administration if applicable.
*   **User**: Can view case files within scope and create entries.
*   **Viewer (optional V1)**: Read-only access to case files/exports.
*   **Stakeholder/Case Owner (Guest)**: Read-only access to a specific case file via case access.

#### 3.2 Permissions (Scope)
Permissions are always scoped (Tenant → Group → Case File):
*   **Case files**: view / create / archive / lock
*   **Entries**: create / view (append-only) / addendum / (no edit, no delete)
*   **Categories**: view / configure (Superuser in own group)
*   **Exports**: create / view export history
*   **Users**: create / disable / role assign (Admin globally; Superuser only in group if admin flag activated)
*   **Decision (Q2)**: Superusers may manage users within their group if the admin activates the `can_manage_users` right/flag.

#### 3.3 Multiple Group Membership
*   A user can belong to multiple groups.
*   The UI transparently shows the user which group they are currently in.
*   Do not create artificial hierarchies between groups.

### 4. Functional Requirements (V1)

#### 4.1 Authentication
*   Local authentication via username/password
*   Invite/reset flow (set password/forgotten password)
*   Session handling (access/refresh token)
    *   Access token lifetime: 15 minutes
    *   Refresh token lifetime: 14 days
*   Rate limiting: 100 requests per minute per user/IP
*   Account lockout: After 10 failed login attempts
*   Optional: 2FA (TOTP) as V1.1
*   Optional: OIDC (Keycloak/Azure AD) as V1.1

#### 4.2 Tenant Creation & Super Admin
*   Tenant creation: Standard approach via initial DB seeding or super admin interface
*   Super admin: System-wide administrator for tenant management
*   First admin user: Automatically created during tenant creation or set via migration

#### 4.3 Admin Interface
Admin can:
*   Configure tenant (name, policies)
*   Create/deactivate users
*   Assign roles
*   Create groups
*   Configure system-wide defaults (e.g., retention, export policies)

#### 4.4 Group Configuration (Superuser)
Superuser can within their own group:
*   Create/modify categories (with automatic versioning per save)
*   Maintain category descriptions/guidelines
*   Define export templates
*   Export case files
*   Archive/lock case files (optional)

#### 4.5 Case File Management
*   Create case file (minimum: title/identifier, optional external reference)
*   Select case file (PWA): Search + Recent + Favorites (not just dropdown)
*   Case file status: active / archived / locked
*   Case file access: User only sees case files they are authorized for (not “entire hospital”)

#### 4.6 Entries (Tamper-Resistant, Append-Only + Addenda)
*   Create entry via: Text, Audio upload/recording (PWA), Image capture (Photo).
*   Entry always belongs to exactly one case file
*   Entries are immutable (append-only): No direct editing, No deletion in V1
*   Corrections only as addendum:
    *   Addendum is a new entry and references the corrected entry (`parent_entry_id`)
    *   Flat versioning: No nesting, last version is displayed
    *   UI shows version chain: Original + addenda with version numbers
*   Entry contains: Category, Free text, Optional structured JSON data, Author, Timestamp, Optional `parent_entry_id`, Version (integer, starts at 1)

#### 4.7 Offline-First PWA
*   Recording/entry possible without network
*   Local queue (pending uploads)
*   Sync as soon as connection available
*   Visible sync status per entry
*   Conflict strategy: Timestamp + user ID + client ID for unique sorting. Append-only minimizes conflicts.

#### 4.7.1 Voice Interpretation (Tasks) – Minimal Spec (MVP)
*   **Mode**: C – Default: Suggestion, optional auto-actions per group.
*   **Trigger keywords**: Configurable (e.g., "next time", "don't forget"). Multilingual support via translated keywords.
*   **Heuristic**: Transcript checked for trigger phrases -> task candidate created.
*   **Offline**: Suggestions stored locally, applied server-side on sync.

#### 4.8 Tasks / Plan per Case File
*   Tasks are independent plan objects within a case file (not entries).
*   **Types**:
    *   `one_shot`: Disappears after check-off.
    *   `reminder_once`: Appears once at next case open, then disappears.
    *   `recurring_always`: Recurrs at every case open.
    *   `recurring_interval`: Recurrs with time interval.
*   Visible only to internal roles (Admin/Super/User/Viewer), not Stakeholders.
*   **API**: GET, POST, PATCH, CHECK, REACTIVATE.

#### 4.9 Export
*   Formats: PDF, JSON, Copy block.
*   Templates per group/category.
*   Audit log of exports.

#### 4.10 Audio Lifecycle (V1)
*   Human audio deleted after successful transcription (privacy).
*   TTS audio (generated) may be stored permanently.

#### 4.11 Audit & Logging
*   Audit log for: Login/logout, Role/permission changes, Category/template changes, Export, Addenda, Case-open events.
*   Searchable by Admin.

### 5. Technical Requirements

#### 5.1 Technology Stack (V1)
*   **Backend**: FastAPI (Python 3.12+)
*   **Database**: PostgreSQL 16+ (separate DB per tenant: `tenant_db_<id>`)
*   **Migrations**: Liquibase (or Alembic for V1/MVP simplicity initially?) -> Requirement says Liquibase.
*   **Control DB**: Central DB for Tenant->DSN mapping.
*   **STT**: faster-whisper (local).
*   **LLM**: Ollama (optional).
*   **Frontend**: React + PWA (Service Worker, IndexedDB).
*   **Storage**: Docker Volume or MinIO.
*   **Auth**: JWT (separate token set per tenant).

#### 5.2 Deployment (Zero-Ops)
*   Single-host Docker Compose.
*   Sensible defaults, auto-migrations.
*   Health checks.

#### 5.3 Data Model (Core Tables)
*   `Tenants`, `Groups`, `Users`, `User_Group_Roles`
*   `Case_Files`: id, group_id, title, external_ref, status, owner_user_id
*   `Case_Access`: for stakeholders
*   `Entries`: id, case_id, category_id, text, structured_data, audio_object_key, parent_entry_id, version
*   `Tasks`: id, case_id, title, task_type, status, recurrence fields
*   `Category_Definitions`: group_id, name, guidelines, schema
*   `Invites`: for stakeholders
*   `Jobs`: for async processing (STT, cleanup)
*   `Audit_Events`

#### 5.4 Security (Zero-Trust)
*   JWT (15min/14days)
*   Scope check at every level.
*   TLS-only prod.
*   Input validation (Pydantic).

#### 5.5 Offline Capability
*   Service Worker cache-first.
*   IndexedDB.
*   Background Sync API.

### 6. Data Privacy
*   Data minimization.
*   Delete human audio after transcription.
*   Right to access (Export).
*   Pseudonymization in Audit Log.

### 7. Monitoring
*   Structured logging (JSON).
*   Metrics (Prometheus).
*   Tracing (optional).

### 8. Key Decisions (Summary)
*   Single-group case files.
*   Whisper (faster-whisper) for STT.
*   Append-only entries.
*   Guest tokens for stakeholders.

### 9. Specifications (Implementable)
*   **Permission Matrix**: Defined for all roles.
*   **Invite Flow**: Magic link or Password set.
*   **DB Job System**: `jobs` table, SKIP LOCKED polling.
*   **Search**: Postgres FTS (GIN index) on Entries/Cases.

### 10. MVP Scope
*   **Included**: Case files, Append-only entries, Offline PWA, Basic Tasks, Whisper STT, Export, RBAC/Guest, Docker Compose.
*   **Excluded**: Complex automation, HIS integration, Cross-tenant search, ML task recognition.
