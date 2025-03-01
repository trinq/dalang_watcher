#!/usr/bin/env python3
"""
Delta Detection Script for Dalang Watcher

This script compares the current scan results with previous scan results
to detect new open ports or closed ports that were previously open.
"""

import requests
import json
import time
import argparse
import os
from datetime import datetime, timedelta
from tabulate import tabulate

API_BASE = "http://localhost:5000"

def get_scan_history(target_ip, days=7):
    """Get all scans for a specific target IP in the last X days"""
    scans = requests.get(f"{API_BASE}/api/scans").json()
    
    # Filter scans for the target IP and port scans only
    target_scans = [
        scan for scan in scans 
        if scan['target'] == target_ip and 'port_scan' in scan['scan_type']
    ]
    
    return target_scans

def get_port_results(scan_id):
    """Get port scan results for a specific scan ID"""
    results = requests.get(f"{API_BASE}/api/results?scan_id={scan_id}").json()
    
    # Extract open ports
    open_ports = {}
    for result in results:
        if result['status'] == 'Open':
            port = result['port']
            protocol = result['protocol']
            open_ports[port] = {
                'protocol': protocol,
                'discovered_at': result['discovered_at']
            }
    
    return open_ports

def scan_ports(target_ip, port_range, scan_type="connect"):
    """Run a new port scan and return the scan ID"""
    # Convert port range to list of ports
    if isinstance(port_range, str) and '-' in port_range:
        start, end = map(int, port_range.split('-'))
        ports = list(range(start, end + 1))
    else:
        ports = port_range if isinstance(port_range, list) else [int(port_range)]
    
    # Run the scan
    response = requests.post(
        f"{API_BASE}/api/scan/ports",
        json={"target": target_ip, "ports": ports, "scan_type": scan_type}
    ).json()
    
    return response.get('scan_id')

def detect_changes(target_ip, port_range="1-1024", scan_type="connect", wait_time=10):
    """
    Detect changes in open ports for a target IP
    
    1. Run a new scan
    2. Get the most recent previous scan
    3. Compare the results
    4. Report changes
    """
    print(f"Running port scan on {target_ip} (ports {port_range})...")
    
    # Run a new scan
    scan_id = scan_ports(target_ip, port_range, scan_type)
    if not scan_id:
        print("Error: Failed to start scan")
        return
    
    print(f"Scan started with ID: {scan_id}")
    print(f"Waiting {wait_time} seconds for scan to complete...")
    time.sleep(wait_time)
    
    # Get current open ports
    current_ports = get_port_results(scan_id)
    
    # Get previous scans
    previous_scans = get_scan_history(target_ip)
    
    # Find the most recent previous scan (excluding the one we just ran)
    previous_scan = None
    for scan in previous_scans:
        if scan['scan_id'] != scan_id:
            previous_scan = scan
            break
    
    if not previous_scan:
        print(f"No previous scans found for {target_ip}. This is the baseline scan.")
        display_current_ports(target_ip, current_ports)
        return
    
    # Get previous open ports
    previous_ports = get_port_results(previous_scan['scan_id'])
    
    # Compare and report changes
    new_ports = {port: info for port, info in current_ports.items() if port not in previous_ports}
    closed_ports = {port: info for port, info in previous_ports.items() if port not in current_ports}
    
    # Display results
    print(f"\nDelta Detection Results for {target_ip}")
    print(f"Current scan: {scan_id} at {datetime.now().isoformat()}")
    print(f"Previous scan: {previous_scan['scan_id']} at {previous_scan['created_at']}")
    
    if new_ports:
        print(f"\n🚨 NEW OPEN PORTS DETECTED: {len(new_ports)}")
        headers = ["Port", "Protocol", "Discovered At"]
        table_data = [[port, info['protocol'], info['discovered_at']] for port, info in new_ports.items()]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if closed_ports:
        print(f"\n📉 PREVIOUSLY OPEN PORTS NOW CLOSED: {len(closed_ports)}")
        headers = ["Port", "Protocol", "Last Seen At"]
        table_data = [[port, info['protocol'], info['discovered_at']] for port, info in closed_ports.items()]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if not new_ports and not closed_ports:
        print("\n✅ No changes detected in open ports")
    
    # Display current state
    display_current_ports(target_ip, current_ports)

def display_current_ports(target_ip, open_ports):
    """Display the current open ports"""
    print(f"\nCurrent Open Ports for {target_ip}: {len(open_ports)}")
    
    if open_ports:
        headers = ["Port", "Protocol", "Service", "Discovered At"]
        table_data = []
        
        # Common port to service mapping
        service_map = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 
            80: "HTTP", 110: "POP3", 115: "SFTP", 135: "RPC", 139: "NetBIOS",
            143: "IMAP", 194: "IRC", 443: "HTTPS", 445: "SMB", 1433: "MSSQL",
            3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 
            8080: "HTTP-Alt"
        }
        
        for port, info in sorted(open_ports.items()):
            service = service_map.get(port, "Unknown")
            table_data.append([port, info['protocol'], service, info['discovered_at']])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    else:
        print("No open ports found.")

def main():
    parser = argparse.ArgumentParser(description="Dalang Watcher Delta Detection")
    parser.add_argument("target", help="Target IP address to scan")
    parser.add_argument("--ports", "-p", default="1-1024", 
                        help="Port range to scan (e.g., '1-1024' or '80,443,8080')")
    parser.add_argument("--type", "-t", choices=["stealth", "connect", "udp"], default="connect",
                        help="Scan type (default: connect)")
    parser.add_argument("--wait", "-w", type=int, default=10,
                        help="Wait time in seconds for scan to complete (default: 10)")
    
    args = parser.parse_args()
    
    # Convert comma-separated ports to list
    if ',' in args.ports:
        port_range = [int(p) for p in args.ports.split(',')]
    else:
        port_range = args.ports
    
    detect_changes(args.target, port_range, args.type, args.wait)

if __name__ == "__main__":
    main()
