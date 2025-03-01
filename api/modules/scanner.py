from scapy.all import IP, TCP, UDP, ICMP, sr1, srp, Ether, ARP
import ipaddress
import threading






class NetworkScanner:
    """
    Class that handles various network scanning techniques using Scapy
    """
    
    @staticmethod
    def stealth_port_scan(target_ip, ports, timeout=1):
        """
        Perform a stealth SYN port scan.
        Returns a dict with port numbers as keys and status as values.
        """
        results = {}
        for port in ports:
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
        return results
    
    @staticmethod
    def connect_scan(target_ip, ports, timeout=1):
        """
        Perform a full TCP connect scan.
        """
        results = {}
        for port in ports:
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
        return results
    
    @staticmethod
    def udp_scan(target_ip, ports, timeout=1):
        """
        Perform a UDP scan.
        """
        results = {}
        for port in ports:
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