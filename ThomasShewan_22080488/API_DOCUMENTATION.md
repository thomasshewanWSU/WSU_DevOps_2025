# Web Crawler CRUD API Documentation

## Overview
RESTful API for managing web monitoring targets. Built with API Gateway and Lambda, backed by DynamoDB.

## Base URL
```
https://[your-api-id].execute-api.ap-southeast-2.amazonaws.com/prod/
```

Get your API URL after deployment:
```bash
aws cloudformation describe-stacks --stack-name prod-ThomasShewan22080488Stack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text
```

## Authentication
Currently public (no authentication required). For production, consider adding API keys or IAM authentication.

## Endpoints

### 1. List All Targets
**GET** `/targets`

Returns all monitoring targets in the system.

**Response 200 OK:**
```json
{
  "targets": [
    {
      "TargetId": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Google",
      "url": "https://www.google.com",
      "enabled": true,
      "created_at": "2025-10-04T10:30:00.000Z",
      "updated_at": "2025-10-04T10:30:00.000Z"
    }
  ],
  "count": 1
}
```

**Example:**
```bash
curl https://your-api.execute-api.ap-southeast-2.amazonaws.com/prod/targets
```

---

### 2. Create Target
**POST** `/targets`

Creates a new monitoring target.

**Request Body:**
```json
{
  "name": "string (required)",
  "url": "string (required, must be valid URL)",
  "enabled": "boolean (optional, default: true)"
}
```

**Response 201 Created:**
```json
{
  "TargetId": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Example Site",
  "url": "https://example.com",
  "enabled": true,
  "created_at": "2025-10-04T10:30:00.000Z",
  "updated_at": "2025-10-04T10:30:00.000Z"
}
```

**Response 400 Bad Request:**
```json
{
  "error": "Missing required fields: name and url"
}
```

**Example:**
```bash
curl -X POST https://your-api.execute-api.ap-southeast-2.amazonaws.com/prod/targets \
  -H "Content-Type: application/json" \
  -d '{"name": "Example", "url": "https://example.com"}'
```

---

### 3. Get Single Target
**GET** `/targets/{id}`

Retrieves a specific target by ID.

**Path Parameters:**
- `id` (string, required): Target UUID

**Response 200 OK:**
```json
{
  "TargetId": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Example Site",
  "url": "https://example.com",
  "enabled": true,
  "created_at": "2025-10-04T10:30:00.000Z",
  "updated_at": "2025-10-04T10:30:00.000Z"
}
```

**Response 404 Not Found:**
```json
{
  "error": "Target 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

**Example:**
```bash
curl https://your-api.execute-api.ap-southeast-2.amazonaws.com/prod/targets/123e4567-e89b-12d3-a456-426614174000
```

---

### 4. Update Target
**PUT** `/targets/{id}`

Updates an existing target. All fields are optional.

**Path Parameters:**
- `id` (string, required): Target UUID

**Request Body:**
```json
{
  "name": "string (optional)",
  "url": "string (optional)",
  "enabled": "boolean (optional)"
}
```

**Response 200 OK:**
```json
{
  "TargetId": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Updated Name",
  "url": "https://example.com",
  "enabled": false,
  "created_at": "2025-10-04T10:30:00.000Z",
  "updated_at": "2025-10-04T11:45:00.000Z"
}
```

**Response 404 Not Found:**
```json
{
  "error": "Target 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

**Example:**
```bash
curl -X PUT https://your-api.execute-api.ap-southeast-2.amazonaws.com/prod/targets/123e4567-e89b-12d3-a456-426614174000 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

---

### 5. Delete Target
**DELETE** `/targets/{id}`

Deletes a target permanently.

**Path Parameters:**
- `id` (string, required): Target UUID

**Response 200 OK:**
```json
{
  "message": "Target 123e4567-e89b-12d3-a456-426614174000 deleted successfully"
}
```

**Response 404 Not Found:**
```json
{
  "error": "Target 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

**Example:**
```bash
curl -X DELETE https://your-api.execute-api.ap-southeast-2.amazonaws.com/prod/targets/123e4567-e89b-12d3-a456-426614174000
```

---

## Performance Metrics

Based on integration testing with DynamoDB:
- **CREATE**: ~200-500ms
- **READ**: ~100-300ms  
- **UPDATE**: ~200-500ms
- **DELETE**: ~100-300ms
- **LIST**: ~300-1000ms (depends on item count)

## Error Handling

All errors return consistent JSON format:
```json
{
  "error": "Error message description"
}
```

### Common HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource doesn't exist
- `500 Internal Server Error`: Server-side error

## Integration with Monitoring Lambda

The monitoring Lambda automatically reads enabled targets from this API:
- Queries DynamoDB for `enabled=true` targets every 5 minutes
- Falls back to environment variable `WEBSITES` if DynamoDB is empty
- Publishes metrics to CloudWatch for each target

To add a website to monitoring:
```bash
curl -X POST https://your-api.execute-api.ap-southeast-2.amazonaws.com/prod/targets \
  -H "Content-Type: application/json" \
  -d '{"name": "MyWebsite", "url": "https://mywebsite.com", "enabled": true}'
```

The site will be monitored within 5 minutes.

## Rate Limits
Currently no rate limiting implemented. Consider adding for production use.

## Support
For issues or questions: 22080488@student.westernsydney.edu.au