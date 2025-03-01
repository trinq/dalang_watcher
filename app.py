from flask import Flask, request, jsonify
from scapy.all import IP, TCP, UDP, ICMP, sr1, srp, Ether, ARP
import psycopg2
from datetime import datetime
import json
import ipaddress
import os
import threading
import time

app = Flask(__name__)

# Database configuration
DB_HOST = os.environ.get('DB_HOST', 'timescaledb')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'asm')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASSWORD', 'asmadmin')

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create tables if they don't exist
    cur.execute('''
    CREATE TABLE IF NOT EXISTS scans (
        scan_id SERIAL PRIMARY KEY,
        scan_type VARCHAR(50),
        target TEXT,
        parameters JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS scan_results (
        result_id SERIAL PRIMARY KEY,
        scan_id INTEGER REFERENCES scans(scan_id),
        target TEXT,
        port INTEGER,
        protocol VARCHAR(10),
        status VARCHAR(20),
        additional_data JSONB,
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Convert to TimescaleDB hypertable
    try:
        cur.execute("SELECT create_hypertable('scan_results', 'discovered_at', if_not_exists => TRUE)")
    except psycopg2.Error:
        conn.rollback()
        # If hypertable conversion fails, continue anyway
    
    conn.commit()
    cur.close()
    conn.close()

# Initialize database when the app starts
init_db()

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
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scans (scan_type, target, parameters) VALUES (%s, %s, %s) RETURNING scan_id",
        (f"port_scan_{scan_type}", target_ip, json.dumps({"ports": ports, "timeout": timeout}))
    )
    scan_id = cur.fetchone()[0]
    conn.commit()
    
    # Start scanning in a separate thread
    scan_thread = threading.Thread(
        target=perform_port_scan,
        args=(scan_id, target_ip, ports, scan_type, timeout)
    )
    scan_thread.start()
    
    return jsonify({
        "message": "Scan started",
        "scan_id": scan_id
    })

def perform_port_scan(scan_id, target_ip, ports, scan_type, timeout):
    results = {}
    
    for port in ports:
        if scan_type == 'stealth':
            # SYN scan
            response = sr1(IP(dst=target_ip)/TCP(dport=port, flags="S"), timeout=timeout, verbose=0)
            if response and response.haslayer(TCP):
                if response[TCP].flags == 0x12:  # SYN-ACK
                    results[port] = "Open"
                    # Send RST to close connection
                    sr1(IP(dst=target_ip)/TCP(dport=port, flags="R"), timeout=timeout, verbose=0)
                elif response[TCP].flags == 0x14:  # RST-ACK
                    results[port] = "Closed"
            else:
                results[port] = "Filtered"
        elif scan_type == 'connect':
            # Connect scan (full TCP handshake)
            response = sr1(IP(dst=target_ip)/TCP(dport=port, flags="S"), timeout=timeout, verbose=0)
            if response and response.haslayer(TCP):
                if response[TCP].flags == 0x12:
                    # Send ACK to complete handshake
                    sr1(IP(dst=target_ip)/TCP(dport=port, flags="A"), timeout=timeout, verbose=0)
                    # Send RST to close connection
                    sr1(IP(dst=target_ip)/TCP(dport=port, flags="R"), timeout=timeout, verbose=0)
                    results[port] = "Open"
                else:
                    results[port] = "Closed"
            else:
                results[port] = "Filtered"
        elif scan_type == 'udp':
            # UDP scan
            response = sr1(IP(dst=target_ip)/UDP(dport=port), timeout=timeout, verbose=0)
            if response is None:
                results[port] = "Open|Filtered"  # No response could mean open or filtered
            elif response.haslayer(ICMP):
                if response[ICMP].type == 3 and response[ICMP].code == 3:
                    results[port] = "Closed"  # Port unreachable
                else:
                    results[port] = "Filtered"
            else:
                results[port] = "Open"
    
    # Store results in database
    conn = get_db_connection()
    cur = conn.cursor()
    for port, status in results.items():
        if status == "Open" or status == "Open|Filtered":
            cur.execute(
                "INSERT INTO scan_results (scan_id, target, port, protocol, status) VALUES (%s, %s, %s, %s, %s)",
                (scan_id, target_ip, port, "TCP" if scan_type != 'udp' else "UDP", status)
            )
    conn.commit()
    cur.close()
    conn.close()

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
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scans (scan_type, target, parameters) VALUES (%s, %s, %s) RETURNING scan_id",
        ("host_discovery", network, json.dumps({}))
    )
    scan_id = cur.fetchone()[0]
    conn.commit()
    
    # Start scanning in a separate thread
    scan_thread = threading.Thread(
        target=perform_host_scan,
        args=(scan_id, network)
    )
    scan_thread.start()
    
    return jsonify({
        "message": "Host scan started",
        "scan_id": scan_id
    })

def perform_host_scan(scan_id, network):
    network = ipaddress.ip_network(network)
    
    # Create ARP request for all hosts in the network
    ans, unans = srp(
        Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=str(network)),
        timeout=5,
        verbose=0
    )
    
    active_hosts = []
    for sent, received in ans:
        active_hosts.append({"ip": received.psrc, "mac": received.hwsrc})
    
    # Store results in database
    conn = get_db_connection()
    cur = conn.cursor()
    for host in active_hosts:
        cur.execute(
            "INSERT INTO scan_results (scan_id, target, status, additional_data) VALUES (%s, %s, %s, %s)",
            (scan_id, host["ip"], "Active", json.dumps({"mac": host["mac"]}))
        )
    conn.commit()
    cur.close()
    conn.close()

@app.route('/api/results', methods=['GET'])
def get_results():
    scan_id = request.args.get('scan_id')
    target = request.args.get('target')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if scan_id:
        cur.execute(
            "SELECT * FROM scan_results WHERE scan_id = %s ORDER BY discovered_at DESC",
            (scan_id,)
        )
    elif target:
        cur.execute(
            "SELECT * FROM scan_results WHERE target = %s ORDER BY discovered_at DESC",
            (target,)
        )
    else:
        cur.execute("SELECT * FROM scan_results ORDER BY discovered_at DESC LIMIT 100")
    
    columns = [desc[0] for desc in cur.description]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return jsonify(results)

@app.route('/api/scans', methods=['GET'])
def get_scans():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM scans ORDER BY created_at DESC LIMIT 100")
    
    columns = [desc[0] for desc in cur.description]
    scans = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return jsonify(scans)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)