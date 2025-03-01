import psycopg2
import json
import os
from datetime import datetime

class DatabaseManager:
    """
    Handles database connections and operations for the ASM system
    """
    
    def __init__(self, host=None, port=None, dbname=None, user=None, password=None):
        """Initialize with connection parameters or use environment variables."""
        self.host = host or os.environ.get('DB_HOST', 'timescaledb')
        self.port = port or os.environ.get('DB_PORT', '5432')
        self.dbname = dbname or os.environ.get('DB_NAME', 'dalang_watcher')
        self.user = user or os.environ.get('DB_USER', 'postgres')
        self.password = password or os.environ.get('DB_PASSWORD', 'asmadmin')
    
    def get_connection(self):
        """Get a connection to the database."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password
        )
    
    def init_db(self):
        """Initialize the database schema."""
        conn = self.get_connection()
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
    
    def create_scan(self, scan_type, target, parameters):
        """Create a new scan record and return its ID."""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO scans (scan_type, target, parameters) VALUES (%s, %s, %s) RETURNING scan_id",
            (scan_type, target, json.dumps(parameters))
        )
        
        scan_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return scan_id
    
    def store_port_results(self, scan_id, target_ip, results, scan_type):
        """Store port scanning results in the database."""
        conn = self.get_connection()
        cur = conn.cursor()
        
        protocol = "TCP" if scan_type != 'udp' else "UDP"
        
        for port, status in results.items():
            if status == "Open" or status == "Open|Filtered":
                cur.execute(
                    "INSERT INTO scan_results (scan_id, target, port, protocol, status) VALUES (%s, %s, %s, %s, %s)",
                    (scan_id, target_ip, port, protocol, status)
                )
        
        conn.commit()
        cur.close()
        conn.close()
    
    def store_host_results(self, scan_id, hosts):
        """Store host discovery results in the database."""
        conn = self.get_connection()
        cur = conn.cursor()
        
        for host in hosts:
            cur.execute(
                "INSERT INTO scan_results (scan_id, target, status, additional_data) VALUES (%s, %s, %s, %s)",
                (scan_id, host["ip"], "Active", json.dumps({"mac": host["mac"]}))
            )
        
        conn.commit()
        cur.close()
        conn.close()
    
    def get_results(self, scan_id=None, target=None):
        """Get scan results from the database."""
        conn = self.get_connection()
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
        
        return results
    
    def get_scans(self, limit=100):
        """Get scan metadata from the database."""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute(f"SELECT * FROM scans ORDER BY created_at DESC LIMIT {limit}")
        
        columns = [desc[0] for desc in cur.description]
        scans = [dict(zip(columns, row)) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return scans