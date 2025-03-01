# Scan Results Endpoint

Get results from previous scans.

**URL**: `/api/results`

**Method**: `GET`

**Auth required**: No

## Query Parameters

| Parameter | Type    | Required | Description                                 |
|-----------|---------|----------|---------------------------------------------|
| scan_id   | integer | No       | Filter results by scan ID                   |
| target    | string  | No       | Filter results by target IP or network      |

## Success Response

**Code**: `200 OK`

**Content example for port scan**:

```json
[
  {
    "additional_data": null,
    "discovered_at": "2025-03-01T09:00:20.049623",
    "port": 80,
    "protocol": "TCP",
    "result_id": 1,
    "scan_id": 1,
    "status": "Open",
    "target": "192.168.1.1"
  },
  {
    "additional_data": null,
    "discovered_at": "2025-03-01T09:00:20.049623",
    "port": 443,
    "protocol": "TCP",
    "result_id": 2,
    "scan_id": 1,
    "status": "Open",
    "target": "192.168.1.1"
  }
]
```

**Content example for host discovery**:

```json
[
  {
    "additional_data": null,
    "discovered_at": "2025-03-01T09:01:05.123456",
    "host": "192.168.1.1",
    "result_id": 3,
    "scan_id": 2,
    "status": "Active"
  },
  {
    "additional_data": null,
    "discovered_at": "2025-03-01T09:01:05.234567",
    "host": "192.168.1.5",
    "result_id": 4,
    "scan_id": 2,
    "status": "Active"
  }
]
```

## Usage Examples

Get all results:
```bash
curl http://localhost:5000/api/results
```

Get results for a specific scan:
```bash
curl 'http://localhost:5000/api/results?scan_id=1'
```

Get results for a specific target:
```bash
curl 'http://localhost:5000/api/results?target=192.168.1.1'
```

## Notes

- If no parameters are provided, all results are returned.
- Results are returned in chronological order (newest first).
- The `discovered_at` field is in ISO 8601 format.
