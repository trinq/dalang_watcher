# Scans Information Endpoint

Get information about previous scans.

**URL**: `/api/scans`

**Method**: `GET`

**Auth required**: No

## Query Parameters

| Parameter | Type    | Required | Description                                 |
|-----------|---------|----------|---------------------------------------------|
| limit     | integer | No       | Limit the number of scans returned          |

## Success Response

**Code**: `200 OK`

**Content example**:

```json
[
  {
    "created_at": "2025-03-01T09:01:00.519333",
    "parameters": {},
    "scan_id": 2,
    "scan_type": "host_discovery",
    "target": "192.168.1.0/29"
  },
  {
    "created_at": "2025-03-01T09:00:17.672978",
    "parameters": {
      "ports": [80, 443],
      "timeout": 1
    },
    "scan_id": 1,
    "scan_type": "port_scan_connect",
    "target": "1.1.1.1"
  }
]
```

## Usage Examples

Get all scans (default limit is 100):
```bash
curl http://localhost:5000/api/scans
```

Get the last 5 scans:
```bash
curl 'http://localhost:5000/api/scans?limit=5'
```

## Notes

- Scans are returned in chronological order (newest first).
- The `created_at` field is in ISO 8601 format.
- The `parameters` field contains scan-specific parameters.
- Default limit is 100 if not specified.
