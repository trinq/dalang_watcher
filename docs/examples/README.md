# Dalang Watcher API Examples

This directory contains example code for using the Dalang Watcher API.

## Python API Client

The `api_client.py` script demonstrates how to interact with the Dalang Watcher API using Python.

### Prerequisites

Install the required dependencies:

```bash
pip install requests tabulate
```

### Usage

```bash
# Check API health
./api_client.py health

# Scan ports on a target
./api_client.py scan-ports 192.168.1.1 --ports 80 443 22 8080 --type connect

# Discover hosts in a network
./api_client.py scan-hosts 192.168.1.0/24

# Get results for a specific scan
./api_client.py results --scan-id 1

# Get results for a specific target
./api_client.py results --target 192.168.1.1

# List recent scans
./api_client.py scans --limit 5
```

### Example Output

Port scan results:
```
+-------------+------+----------+--------+-------------------------+
| Target      | Port | Protocol | Status | Discovered At           |
+=============+======+==========+========+=========================+
| 192.168.1.1 |   80 | TCP      | Open   | 2025-03-01T09:02:50.52 |
+-------------+------+----------+--------+-------------------------+
| 192.168.1.1 |  443 | TCP      | Open   | 2025-03-01T09:02:50.52 |
+-------------+------+----------+--------+-------------------------+
```

## Shell Script Examples

### Basic curl commands

```bash
# Health check
curl http://localhost:5000/api/health

# Port scan
curl -X POST -H "Content-Type: application/json" \
  -d '{"target": "192.168.1.1", "ports": [80, 443], "scan_type": "connect"}' \
  http://localhost:5000/api/scan/ports

# Host discovery
curl -X POST -H "Content-Type: application/json" \
  -d '{"network": "192.168.1.0/24"}' \
  http://localhost:5000/api/scan/hosts

# Get results
curl 'http://localhost:5000/api/results?scan_id=1'

# List scans
curl 'http://localhost:5000/api/scans?limit=5'
```
