from flask import Flask, request, jsonify
import threading
import ipaddress
import json
import os
from datetime import datetime
from modules.scanner import NetworkScanner
from modules.db import DatabaseManager

app = Flask(__name__)
db_manager = DatabaseManager()

# Initialize database when the app starts
@app.before_first_request
def init_app():
    db_manager.init_db()

@app.route('/api/scan/ports', methods=['POST'])
def scan_ports():
    data = request.json
    target_ip = data.get('target')
    ports = data.get('ports', [])
    scan_type = data.get('scan_type', 'stealth')
    timeout = data.get('timeout', 1)
    
    # Validate input
    try:
        ipaddress.ip_address(target_ip)
    except ValueError:
        return jsonify({"error": "Invalid IP address"}), 400
    
    if not ports:
        return jsonify({"error": "No ports specified"}), 400
    
    # Create scan record in database
    scan_id = db_manager.create_scan(
        f"port_scan_{scan_type}", target_ip, {"ports": ports, "timeout": timeout}
    )
    
    # Start scanning in a separate thread
    scan_thread = threading.Thread(
        target=perform_port_scan,
        args=(scan_id, target_ip, ports, scan_type, timeout)
    )
    scan_thread.start()
    
    return jsonify({
        "message": "Scan started",
        "scan_id": scan_id,
        "timestamp": datetime.now().isoformat()
    })

def perform_port_scan(scan_id, target_ip, ports, scan_type, timeout):
    """Execute port scan in background thread and store results."""
    try:
        results = NetworkScanner.scan_ports_async(scan_type, target_ip, ports, timeout)
        db_manager.store_port_results(scan_id, target_ip, results, scan_type)
    except Exception as e:
        print(f"Error during port scan: {str(e)}")

@app.route('/api/scan/hosts', methods=['POST'])
def scan_hosts():
    data = request.json
    network = data.get('network')  # CIDR notation (e.g., 192.168.1.0/24)
    
    # Validate input
    try:
        ipaddress.ip_network(network)
    except ValueError:
        return jsonify({"error": "Invalid network CIDR"}), 400
    
    # Create scan record
    scan_id = db_manager.create_scan("host_discovery", network, {})
    
    # Start scanning in a separate thread
    scan_thread = threading.Thread(
        target=perform_host_scan,
        args=(scan_id, network)
    )
    scan_thread.start()
    
    return jsonify({
        "message": "Host scan started",
        "scan_id": scan_id,
        "timestamp": datetime.now().isoformat()
    })

def perform_host_scan(scan_id, network):
    """Execute host discovery in background thread and store results."""
    try:
        active_hosts = NetworkScanner.discover_hosts(network)
        db_manager.store_host_results(scan_id, active_hosts)
    except Exception as e:
        print(f"Error during host scan: {str(e)}")

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get scan results with optional filtering."""
    scan_id = request.args.get('scan_id')
    target = request.args.get('target')
    
    results = db_manager.get_results(scan_id, target)
    
    # Convert datetime objects to ISO format strings for JSON serialization
    for result in results:
        if 'discovered_at' in result and result['discovered_at']:
            result['discovered_at'] = result['discovered_at'].isoformat()
    
    return jsonify(results)

@app.route('/api/scans', methods=['GET'])
def get_scans():
    """Get information about previous scans."""
    limit = request.args.get('limit', 100, type=int)
    scans = db_manager.get_scans(limit)
    
    # Convert datetime objects to ISO format strings for JSON serialization
    for scan in scans:
        if 'created_at' in scan and scan['created_at']:
            scan['created_at'] = scan['created_at'].isoformat()
    
    return jsonify(scans)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "user": os.environ.get('CURRENT_USER', 'trinq')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)