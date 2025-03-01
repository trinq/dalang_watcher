# Port Scanning Endpoint

Scan for open ports on a target IP address.

**URL**: `/api/scan/ports`

**Method**: `POST`

**Auth required**: No

## Request Body

```json
{
  "target": "192.168.1.1",
  "ports": [22, 80, 443, 8080],
  "scan_type": "connect",
  "timeout": 1
}
```

### Parameters

| Parameter  | Type    | Required | Description                                                 | Default   |
|------------|---------|----------|-------------------------------------------------------------|-----------|
| target     | string  | Yes      | Target IP address to scan                                   | -         |
| ports      | array   | Yes      | Array of port numbers to scan                               | -         |
| scan_type  | string  | No       | Scan type: "stealth", "connect", or "udp"                   | "stealth" |
| timeout    | integer | No       | Timeout in seconds for each port scan                       | 1         |

## Success Response

**Code**: `200 OK`

**Content example**:

```json
{
  "message": "Scan started",
  "scan_id": 123,
  "timestamp": "2025-03-01T09:00:17.689133"
}
```

## Error Responses

**Condition**: If target IP is invalid

**Code**: `400 BAD REQUEST`

**Content**:

```json
{
  "error": "Invalid IP address"
}
```

**Condition**: If no ports are specified

**Code**: `400 BAD REQUEST`

**Content**:

```json
{
  "error": "No ports specified"
}
```

## Usage Example

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"target": "192.168.1.1", "ports": [80, 443], "scan_type": "connect"}' \
  http://localhost:5000/api/scan/ports
```

## Notes

- The scan runs asynchronously. Use the returned `scan_id` to query results.
- Different scan types have different visibility on networks:
  - `stealth`: Less detectable but requires root privileges
  - `connect`: More detectable but works without special privileges
  - `udp`: For scanning UDP ports
