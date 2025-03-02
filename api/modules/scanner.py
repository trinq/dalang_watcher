from scapy.all import IP, TCP, UDP, ICMP, sr1, srp, Ether, ARP
import ipaddress
import threading
import time
import concurrent.futures
from queue import Queue

class NetworkScanner:
    """
    Class that handles various network scanning techniques using Scapy
    """
    
    # Class variables for rate limiting
    MAX_WORKERS = 10  # Maximum number of concurrent worker threads
    RATE_LIMIT = 0.02  # 20ms between packets (50 packets per second)
    
    @staticmethod
    def _scan_port_stealth(target_ip, port, timeout=1):
        """
        Scan a single port using stealth SYN scan.
        """
        response = sr1(IP(dst=target_ip)/TCP(dport=port, flags="S"), timeout=timeout, verbose=0)
        if response and response.haslayer(TCP):
            if response[TCP].flags == 0x12:  # SYN-ACK
                # Send RST to close connection
                sr1(IP(dst=target_ip)/TCP(dport=port, flags="R"), timeout=timeout, verbose=0)
                return port, "Open"
            elif response[TCP].flags == 0x14:  # RST-ACK
                return port, "Closed"
        else:
            return port, "Filtered"
    
    @staticmethod
    def _scan_port_connect(target_ip, port, timeout=1):
        """
        Scan a single port using full TCP connect scan.
        """
        response = sr1(IP(dst=target_ip)/TCP(dport=port, flags="S"), timeout=timeout, verbose=0)
        if response and response.haslayer(TCP):
            if response[TCP].flags == 0x12:
                # Send ACK to complete handshake
                sr1(IP(dst=target_ip)/TCP(dport=port, flags="A"), timeout=timeout, verbose=0)
                # Send RST to close connection
                sr1(IP(dst=target_ip)/TCP(dport=port, flags="R"), timeout=timeout, verbose=0)
                return port, "Open"
            else:
                return port, "Closed"
        else:
            return port, "Filtered"
    
    @staticmethod
    def _scan_port_udp(target_ip, port, timeout=1):
        """
        Scan a single port using UDP scan.
        """
        response = sr1(IP(dst=target_ip)/UDP(dport=port), timeout=timeout, verbose=0)
        if response is None:
            return port, "Open|Filtered"  # No response could mean open or filtered
        elif response.haslayer(ICMP):
            if response[ICMP].type == 3 and response[ICMP].code == 3:
                return port, "Closed"  # Port unreachable
            else:
                return port, "Filtered"
        else:
            return port, "Open"
    
    @staticmethod
    def stealth_port_scan(target_ip, ports, timeout=1):
        """
        Perform a stealth SYN port scan using multiple threads.
        Returns a dict with port numbers as keys and status as values.
        """
        return NetworkScanner._threaded_port_scan(
            NetworkScanner._scan_port_stealth, target_ip, ports, timeout
        )
    
    @staticmethod
    def connect_scan(target_ip, ports, timeout=1):
        """
        Perform a full TCP connect scan using multiple threads.
        """
        return NetworkScanner._threaded_port_scan(
            NetworkScanner._scan_port_connect, target_ip, ports, timeout
        )
    
    @staticmethod
    def udp_scan(target_ip, ports, timeout=1):
        """
        Perform a UDP scan using multiple threads.
        """
        return NetworkScanner._threaded_port_scan(
            NetworkScanner._scan_port_udp, target_ip, ports, timeout
        )
    
    @staticmethod
    def _threaded_port_scan(scan_func, target_ip, ports, timeout=1):
        """
        Generic threaded port scanning function.
        Uses ThreadPoolExecutor to manage worker threads and applies rate limiting.
        """
        results = {}
        
        # Use semaphore to control rate limiting across threads
        port_queue = Queue()
        
        # Add all ports to the queue
        for port in ports:
            port_queue.put(port)
        
        def worker():
            while not port_queue.empty():
                try:
                    port = port_queue.get(block=False)
                    port, status = scan_func(target_ip, port, timeout)
                    results[port] = status
                    # Apply rate limiting
                    time.sleep(NetworkScanner.RATE_LIMIT)
                except Exception as e:
                    print(f"Error scanning port: {e}")
                finally:
                    port_queue.task_done()
        
        # Determine number of worker threads based on port count
        # Use fewer workers for smaller port ranges
        port_count = len(ports)
        worker_count = min(NetworkScanner.MAX_WORKERS, max(1, port_count // 100 + 1))
        
        # Create and start worker threads
        threads = []
        for _ in range(worker_count):
            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Wait for all ports to be processed
        port_queue.join()
        
        return results
    
    @staticmethod
    def discover_hosts(network):
        """
        Discover active hosts on a network using ARP.
        """
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
        
        return active_hosts
    
    @staticmethod
    def scan_ports_async(scan_type, target_ip, ports, timeout=1):
        """
        Perform the appropriate scan based on scan_type.
        """
        if scan_type == 'stealth':
            return NetworkScanner.stealth_port_scan(target_ip, ports, timeout)
        elif scan_type == 'connect':
            return NetworkScanner.connect_scan(target_ip, ports, timeout)
        elif scan_type == 'udp':
            return NetworkScanner.udp_scan(target_ip, ports, timeout)
        else:
            raise ValueError(f"Unsupported scan type: {scan_type}")