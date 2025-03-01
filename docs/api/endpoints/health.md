# Health Check Endpoint

Check if the API is running and get basic information.

**URL**: `/api/health`

**Method**: `GET`

**Auth required**: No

## Success Response

**Code**: `200 OK`

**Content example**:

```json
{
  "status": "ok",
  "timestamp": "2025-03-01T09:00:17.689133",
  "user": "trinq"
}
```

## Usage Example

```bash
curl http://localhost:5000/api/health
```
