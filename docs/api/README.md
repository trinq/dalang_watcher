# Dalang Watcher API Documentation

The Dalang Watcher API provides network scanning and monitoring capabilities through a RESTful interface.

## Base URL

When running locally or in Docker:
```
http://localhost:5000
```

## Authentication

Currently, the API does not require authentication.

## API Endpoints

### Health Check
- [GET /api/health](endpoints/health.md) - Check if the API is running

### Scanning
- [POST /api/scan/ports](endpoints/scan_ports.md) - Scan ports on a target IP
- [POST /api/scan/hosts](endpoints/scan_hosts.md) - Discover active hosts in a network

### Results
- [GET /api/results](endpoints/results.md) - Get scan results
- [GET /api/scans](endpoints/scans.md) - Get information about previous scans

## Response Format

All responses are in JSON format. Successful responses typically include:

```json
{
  "message": "Operation description",
  "scan_id": 123,
  "timestamp": "2025-03-01T09:00:17.689133"
}
```

Error responses include:

```json
{
  "error": "Error description"
}
```

## Status Codes

- `200 OK` - The request was successful
- `400 Bad Request` - The request was invalid
- `404 Not Found` - The requested resource was not found
- `500 Internal Server Error` - An error occurred on the server
