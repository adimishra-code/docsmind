# DocsMind API Specification

All endpoints are prefixed with the base API version: `/api/v1`.

---

## 1. Authentication Service

### Register Account
*   **Method:** `POST`
*   **URL:** `/auth/register`
*   **Request Headers:** `Content-Type: application/json`
*   **Request Body:**
    ```json
    {
      "email": "user@example.com",
      "password": "SecurePassword123!"
    }
    ```
*   **Response (201 Created):**
    ```json
    {
      "id": "c62047cb-bbf8-466d-97e3-0d531bb3ee82",
      "email": "user@example.com",
      "is_active": true,
      "is_admin": false,
      "created_at": "2026-06-29T10:43:00Z",
      "updated_at": "2026-06-29T10:43:00Z"
    }
    ```
*   **Validation Rules:** 
    *   `email` must be a valid RFC 5322 string.
    *   `password` must be at least 8 characters, containing uppercase, lowercase, numeric, and special characters.
*   **Errors:**
    *   `400 Bad Request` (Validation errors: `code="validation_error"`).
    *   `409 Conflict` (Email already registered: `code="conflict"`).

### Login (Obtain Tokens)
*   **Method:** `POST`
*   **URL:** `/auth/login`
*   **Request Body:** Same as Register.
*   **Response (200 OK):**
    ```json
    {
      "access_token": "eyJhbG...",
      "refresh_token": "eyJyN...",
      "token_type": "bearer"
    }
    ```
*   **Errors:**
    *   `401 Unauthorized` (Incorrect email or password, or inactive account: `code="authentication_error"`).

### Refresh Access Token
*   **Method:** `POST`
*   **URL:** `/auth/refresh`
*   **Request Body:**
    ```json
    {
      "refresh_token": "eyJyN..."
    }
    ```
*   **Response (200 OK):** New JWT token pair.
*   **Errors:**
    *   `401 Unauthorized` (Token expired or invalid: `code="token_expired"`).
    *   `401 Unauthorized` (Suspected replay attack: `code="token_revoked"`).

---

## 2. Document Ingestion Service

### Upload Document
*   **Method:** `POST`
*   **URL:** `/documents/upload`
*   **Request Headers:** `Authorization: Bearer <access_token>`, `Content-Type: multipart/form-data`
*   **Request Body:**
    *   `file`: Binary (Required)
    *   `chunk_size`: Integer (Optional, default: 512)
    *   `chunk_overlap`: Integer (Optional, default: 64)
*   **Response (202 Accepted):**
    ```json
    {
      "id": "e21010bb-a302-47df-ba54-d852093cdabf",
      "filename": "annual_report.pdf",
      "status": "pending",
      "created_at": "2026-06-29T10:43:10Z"
    }
    ```
*   **Validation Rules:** File extension must be `.pdf`, `.docx`, `.txt`, `.csv`, `.pptx`, or `.md`. Max size 50MB.

### List Documents
*   **Method:** `GET`
*   **URL:** `/documents?skip=0&limit=20`
*   **Response (200 OK):**
    ```json
    {
      "items": [
        {
          "id": "e21010bb-a302-47df-ba54-d852093cdabf",
          "filename": "annual_report.pdf",
          "file_size": 1421098,
          "status": "completed",
          "doc_metadata": { "pages": 15, "language": "en" },
          "created_at": "2026-06-29T10:43:10Z"
        }
      ],
      "total": 1
    }
    ```

### Get Ingestion Status
*   **Method:** `GET`
*   **URL:** `/documents/{id}/status`
*   **Response (200 OK):**
    ```json
    {
      "id": "e21010bb-a302-47df-ba54-d852093cdabf",
      "status": "processing",
      "progress_pct": 45.5,
      "error_message": null
    }
    ```

---

## 3. Chat & Conversation Service

### Create Chat Session
*   **Method:** `POST`
*   **URL:** `/chats`
*   **Request Body:**
    ```json
    {
      "title": "New Document Discussion"
    }
    ```
*   **Response (201 Created):** Returns session details.

### Send Message (Streaming)
*   **Method:** `POST`
*   **URL:** `/chats/{session_id}/messages`
*   **Request Headers:** `Accept: text/event-stream`
*   **Request Body:**
    ```json
    {
      "message": "What is the primary revenue source?",
      "document_ids": ["e21010bb-a302-47df-ba54-d852093cdabf"]
    }
    ```
*   **Response:** `text/event-stream` sending tokens (`chunk` event) and final metadata (`citations` event).
