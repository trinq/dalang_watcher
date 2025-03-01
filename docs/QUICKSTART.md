# Dalang Watcher Quick Start Guide

This guide will help you get started with using the Dalang Watcher API for network scanning and monitoring.

## Running the API

### Using Docker (Recommended for Production)

1. Start the entire stack:
   ```bash
   docker-compose up -d
   ```

2. Or start just the database and run the API locally (for development):
   ```bash
   # Start just the database
   docker-compose up -d timescaledb
   
   # Run the API locally
   ./run_dev.sh
   ```

## Basic API Usage

### Health Check

Verify the API is running:

```bash
curl http://localhost:5000/api/health
```

### Port Scanning

Scan specific ports on a target:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"target": "192.168.1.1", "ports": [80, 443, 22, 8080], "scan_type": "connect"}' \
  http://localhost:5000/api/scan/ports
```

### Host Discovery

Find active hosts in a network:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"network": "192.168.1.0/24"}' \
  http://localhost:5000/api/scan/hosts
```

### Get Scan Results

Retrieve results from a scan:

```bash
# Replace 1 with your scan_id
curl 'http://localhost:5000/api/results?scan_id=1'
```

### List All Scans

View information about previous scans:

```bash
curl http://localhost:5000/api/scans
```

## Python Client Example

Here's a simple Python script to interact with the API:

```python
import requests
import json
import time

API_BASE = "http://localhost:5000"

# Scan ports on a target
def scan_ports(target, ports, scan_type="connect"):
    response = requests.post(
        f"{API_BASE}/api/scan/ports",
        json={"target": target, "ports": ports, "scan_type": scan_type}
    )
    return response.json()

# Get results for a scan
def get_results(scan_id):
    response = requests.get(f"{API_BASE}/api/results?scan_id={scan_id}")
    return response.json()

# Example usage
if __name__ == "__main__":
    # Start a port scan
    scan_result = scan_ports("192.168.1.1", [80, 443, 22, 8080])
    print(f"Scan started: {scan_result}")
    
    # Wait for scan to complete
    scan_id = scan_result["scan_id"]
    time.sleep(5)
    
    # Get the results
    results = get_results(scan_id)
    print(f"Scan results: {json.dumps(results, indent=2)}")
```

## Next Steps

- Check the [API Documentation](api/README.md) for detailed information about all endpoints
- Explore different scan types (stealth, connect, udp) for different use cases
- Use the API to build automated network monitoring solutions
