# DocsMind Database Specification

DocsMind uses PostgreSQL as its primary transactional database. The schema is optimized for multi-tenancy, rapid metadata retrieval, and audit logging.

---

## 1. Schema Tables & Columns

### 1. `users`
Tracks user credentials, status, and permissions.
*   `id` `UUID` (PK, Default: `gen_random_uuid()`): Unique identifier.
*   `email` `VARCHAR(255)` (Unique, Index): User email address. Lowercase index is applied.
*   `hashed_password` `VARCHAR(255)`: Encrypted bcrypt password.
*   `is_active` `BOOLEAN` (Default: `TRUE`): Active account flag.
*   `is_admin` `BOOLEAN` (Default: `FALSE`): Admin privileges.
*   `created_at` `TIMESTAMPTZ` (Default: `NOW()`): Creation timestamp.
*   `updated_at` `TIMESTAMPTZ` (Default: `NOW()`): Update timestamp.

### 2. `refresh_tokens`
Manages JWT refresh sessions and rotates credentials.
*   `id` `UUID` (PK).
*   `user_id` `UUID` (FK -> `users.id` ON DELETE CASCADE, Index).
*   `token` `VARCHAR(512)` (Unique).
*   `jti` `VARCHAR(255)` (Unique, Index): JWT ID for token verification and denylisting.
*   `expires_at` `TIMESTAMPTZ`.
*   `revoked_at` `TIMESTAMPTZ` (Nullable).

### 3. `documents`
Tracks uploaded files and parsing progress.
*   `id` `UUID` (PK).
*   `user_id` `UUID` (FK -> `users.id` ON DELETE CASCADE, Index).
*   `filename` `VARCHAR(255)`: Uploaded file name.
*   `file_type` `VARCHAR(50)`: PDF, DOCX, CSV, etc.
*   `storage_path` `VARCHAR(1024)`: Path inside S3 bucket or local store.
*   `file_size` `BIGINT`: File size in bytes.
*   `status` `VARCHAR(50)` (Default: `'pending'`, Index): `pending`, `processing`, `completed`, `failed`.
*   `error_message` `TEXT` (Nullable): Stacktrace if parsing fails.
*   `doc_metadata` `JSONB` (Nullable): Extracted metadata (author, title, keywords, pages).

### 4. `document_chunks`
Stores text segments mapped to vector embedding IDs.
*   `id` `UUID` (PK).
*   `document_id` `UUID` (FK -> `documents.id` ON DELETE CASCADE, Index).
*   `chunk_index` `INT`: Index order.
*   `content` `TEXT`: Actual raw chunk content.
*   `embedding_id` `VARCHAR(255)` (Unique, Index): Mapped ID inside Qdrant/Pinecone.
*   `page_number` `INT` (Nullable): Bounding page context.
*   `chunk_metadata` `JSONB` (Nullable): Page coordinate bounding boxes.

### 5. `usage_logs`
SaaS analytics log.
*   `id` `UUID` (PK).
*   `user_id` `UUID` (FK -> `users.id` ON DELETE SET NULL, Index).
*   `action` `VARCHAR(100)`: `upload`, `chat`, `search`.
*   `token_count` `INT` (Default: 0).
*   `latency_ms` `INT` (Default: 0).
*   `cost` `NUMERIC(10, 6)` (Default: 0.000000).
*   `created_at` `TIMESTAMPTZ` (Default: `NOW()`, Index).

---

## 2. Key Indexes & Performance Constraints
1.  **Lowercase Unique Email Index**:
    ```sql
    CREATE UNIQUE INDEX ix_users_email_lower ON users (LOWER(email));
    ```
2.  **Document Multi-Tenant Composite Index**:
    ```sql
    CREATE INDEX ix_documents_user_status ON documents (user_id, status);
    ```
3.  **Audit Logs Partitioning**:
    For heavy logging, `audit_logs` is range-partitioned by month on the `created_at` column.
