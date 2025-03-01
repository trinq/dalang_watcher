#!/usr/bin/env python3
"""
Dalang Watcher API Client Example

This script demonstrates how to interact with the Dalang Watcher API
for network scanning and monitoring.
"""

import requests
import json
import time
import argparse
from tabulate import tabulate

API_BASE = "http://localhost:5000"

def check_health():
    """Check if the API is running"""
    response = requests.get(f"{API_BASE}/api/health")
    return response.json()

def scan_ports(target, ports, scan_type="connect"):
    """Scan ports on a target IP"""
    response = requests.post(
        f"{API_BASE}/api/scan/ports",
        json={"target": target, "ports": ports, "scan_type": scan_type}
    )
    return response.json()

def scan_hosts(network):
    """Discover active hosts in a network"""
    response = requests.post(
        f"{API_BASE}/api/scan/hosts",
        json={"network": network}
    )
    return response.json()

def get_results(scan_id=None, target=None):
    """Get results for a scan"""
    params = {}
    if scan_id:
        params["scan_id"] = scan_id
    if target:
        params["target"] = target
    
    response = requests.get(f"{API_BASE}/api/results", params=params)
    return response.json()

def get_scans(limit=10):
    """Get information about previous scans"""
    response = requests.get(f"{API_BASE}/api/scans", params={"limit": limit})
    return response.json()

def display_port_results(results):
    """Display port scan results in a table"""
    if not results:
        print("No results found.")
        return
    
    headers = ["Target", "Port", "Protocol", "Status", "Discovered At"]
    table_data = []
    
    for result in results:
        table_data.append([
            result["target"],
            result["port"],
            result["protocol"],
            result["status"],
            result["discovered_at"]
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def display_host_results(results):
    """Display host discovery results in a table"""
    if not results:
        print("No results found.")
        return
    
    headers = ["Host", "Status", "Discovered At"]
    table_data = []
    
    for result in results:
        table_data.append([
            result["host"],
            result["status"],
            result["discovered_at"]
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def display_scans(scans):
    """Display scan information in a table"""
    if not scans:
        print("No scans found.")
        return
    
    headers = ["ID", "Type", "Target", "Created At"]
    table_data = []
    
    for scan in scans:
        table_data.append([
            scan["scan_id"],
            scan["scan_type"],
            scan["target"],
            scan["created_at"]
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def main():
    parser = argparse.ArgumentParser(description="Dalang Watcher API Client")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Health check command
    subparsers.add_parser("health", help="Check API health")
    
    # Port scan command
    port_parser = subparsers.add_parser("scan-ports", help="Scan ports on a target")
    port_parser.add_argument("target", help="Target IP address")
    port_parser.add_argument("--ports", "-p", type=int, nargs="+", default=[80, 443, 22, 8080], 
                            help="Ports to scan (default: 80 443 22 8080)")
    port_parser.add_argument("--type", "-t", choices=["stealth", "connect", "udp"], default="connect",
                            help="Scan type (default: connect)")
    
    # Host discovery command
    host_parser = subparsers.add_parser("scan-hosts", help="Discover hosts in a network")
    host_parser.add_argument("network", help="Network CIDR (e.g., 192.168.1.0/24)")
    
    # Results command
    results_parser = subparsers.add_parser("results", help="Get scan results")
    results_parser.add_argument("--scan-id", "-s", type=int, help="Filter by scan ID")
    results_parser.add_argument("--target", "-t", help="Filter by target")
    
    # Scans command
    scans_parser = subparsers.add_parser("scans", help="Get scan information")
    scans_parser.add_argument("--limit", "-l", type=int, default=10, help="Limit number of scans (default: 10)")
    
    args = parser.parse_args()
    
    if args.command == "health":
        result = check_health()
        print(f"API Status: {result['status']}")
        print(f"Timestamp: {result['timestamp']}")
        print(f"User: {result['user']}")
    
    elif args.command == "scan-ports":
        print(f"Scanning ports {args.ports} on {args.target} using {args.type} scan...")
        result = scan_ports(args.target, args.ports, args.type)
        print(f"Scan started with ID: {result['scan_id']}")
        print("Waiting for results...")
        time.sleep(5)  # Wait for scan to complete
        
        results = get_results(scan_id=result['scan_id'])
        display_port_results(results)
    
    elif args.command == "scan-hosts":
        print(f"Discovering hosts in network {args.network}...")
        result = scan_hosts(args.network)
        print(f"Scan started with ID: {result['scan_id']}")
        print("Waiting for results...")
        time.sleep(10)  # Wait for scan to complete
        
        results = get_results(scan_id=result['scan_id'])
        display_host_results(results)
    
    elif args.command == "results":
        results = get_results(scan_id=args.scan_id, target=args.target)
        if "port" in results[0] if results else {}:
            display_port_results(results)
        else:
            display_host_results(results)
    
    elif args.command == "scans":
        scans = get_scans(limit=args.limit)
        display_scans(scans)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
