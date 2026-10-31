# TestGuard API Reference

The TestGuard Demo API is versioned under `/api/v1`. All endpoints accept and return JSON payloads.

---

## 1. Authentication & Security
TestGuard uses HTTP Bearer authentication with JSON Web Tokens (JWT).
Include the token in the `Authorization` header for protected endpoints:
```http
Authorization: Bearer <ACCESS_TOKEN>
```

### Standard HTTP Status Codes
| Status Code | Reason | Meaning |
| :--- | :--- | :--- |
| `200 OK` | Success | Request succeeded and returned requested data |
| `201 Created` | Created | Resource successfully created |
| `400 Bad Request` | Client Error | Malformed request syntax or parameters |
| `401 Unauthorized` | Auth Error | Missing, invalid, expired, or tampered access token |
| `403 Forbidden` | Perms Error | Authenticated user lacks role permissions (e.g. member attempting admin action) |
| `404 Not Found` | Not Found | Resource does not exist OR belongs to another tenant (IDOR prevention) |
| `409 Conflict` | Conflict | Uniqueness constraint violated (e.g. duplicate project name within tenant) |
| `422 Unprocessable` | Validation | Pydantic schema validation failure (e.g. empty or invalid data types) |

---

## 2. Endpoints Summary

### System & Health
- `GET /health`: Health status, service version, environment.
- `GET /docs`: Interactive OpenAPI Swagger UI documentation.
- `GET /redoc`: Interactive ReDoc documentation.
- `GET /api/v1/openapi.json`: Machine-readable OpenAPI 3.0 specification.

### Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Authenticate with `email` and `password`. Returns `{ access_token, token_type, expires_in }`.
- `GET /api/v1/auth/me`: Retrieve profile of currently authenticated user.

### Projects (`/api/v1/projects`)
- `GET /api/v1/projects`: List projects for caller's tenant. Supports `page`, `size`, `status`.
- `POST /api/v1/projects`: Create project in caller's tenant. **(Admin only)**
- `GET /api/v1/projects/{id}`: Get project by ID in caller's tenant.
- `PATCH /api/v1/projects/{id}`: Update project in caller's tenant. **(Admin only)**
- `DELETE /api/v1/projects/{id}`: Delete project and cascade child tasks. **(Admin only)**

### Tasks (`/api/v1/tasks`)
- `GET /api/v1/tasks`: List tasks for caller's tenant. Supports `page`, `size`, `project_id`, `status`.
- `POST /api/v1/tasks`: Create task in a tenant-owned project. **(Admin & Member)**
- `GET /api/v1/tasks/{id}`: Get task by ID in caller's tenant.
- `PATCH /api/v1/tasks/{id}`: Update task title, description, or status. **(Admin & Member)**
- `DELETE /api/v1/tasks/{id}`: Delete task in caller's tenant. **(Admin only)**
