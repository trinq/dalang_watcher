# Host Discovery Endpoint

Discover active hosts in a network range.

**URL**: `/api/scan/hosts`

**Method**: `POST`

**Auth required**: No

## Request Body

```json
{
  "network": "192.168.1.0/24"
}
```

### Parameters

| Parameter | Type   | Required | Description                              |
|-----------|--------|----------|------------------------------------------|
| network   | string | Yes      | Network range in CIDR notation           |

## Success Response

**Code**: `200 OK`

**Content example**:

```json
{
  "message": "Host scan started",
  "scan_id": 124,
  "timestamp": "2025-03-01T09:01:00.530126"
}
```

## Error Response

**Condition**: If network CIDR is invalid

**Code**: `400 BAD REQUEST`

**Content**:

```json
{
  "error": "Invalid network CIDR"
}
```

## Usage Example

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"network": "192.168.1.0/24"}' \
  http://localhost:5000/api/scan/hosts
```

## Notes

- The scan runs asynchronously. Use the returned `scan_id` to query results.
- For smaller networks (e.g., /29), the scan completes quickly.
- For larger networks, the scan may take longer to complete.
- Host discovery uses ICMP echo requests (ping) and TCP SYN packets to port 80.
