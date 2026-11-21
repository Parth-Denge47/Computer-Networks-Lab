"""
Experiment 07 - DNS and HTTP / HTTPS packet analysis

Name : Parth Denge
PRN  : 24070521018
Lab  : Computer Networks Laboratory

A small socket-level packet dissector that sends real DNS, HTTP and HTTPS
traffic and decodes the exact bytes on the wire, field by field, the way the
Wireshark packet-details pane does.

    python packet_dissector.py dns  sitnagpur.edu.in   [dns-server]
    python packet_dissector.py http example.com
    python packet_dissector.py tls  example.com
"""
import random
import socket
import ssl
import struct
import sys
import time

RR_TYPES = {1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR", 15: "MX", 28: "AAAA"}
RCODES = {0: "No error", 1: "Format error", 2: "Server failure", 3: "No such name"}
TLS_TYPES = {20: "Change Cipher Spec", 21: "Alert", 22: "Handshake", 23: "Application Data"}
TLS_VERSIONS = {0x0301: "TLS 1.0", 0x0302: "TLS 1.1", 0x0303: "TLS 1.2", 0x0304: "TLS 1.3"}
HS_TYPES = {1: "Client Hello", 2: "Server Hello", 4: "New Session Ticket", 11: "Certificate"}


def hexdump(data, limit=None, indent="    "):
    data = data[:limit] if limit else data
    for off in range(0, len(data), 16):
        row = data[off:off + 16]
        hexes = " ".join(f"{b:02x}" for b in row)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        print(f"{indent}{off:04x}  {hexes:<47}  {text}")


# --------------------------------------------------------------------------- DNS

def build_query(name, qtype=1):
    tid = random.randint(0, 0xFFFF)
    header = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0)  # RD = 1
    qname = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
    return tid, header + qname + struct.pack("!HH", qtype, 1)


def read_name(msg, off):
    labels, jumped, end = [], False, off
    while True:
        length = msg[off]
        if length & 0xC0 == 0xC0:                      # compression pointer
            if not jumped:
                end = off + 2
            off = ((length & 0x3F) << 8) | msg[off + 1]
            jumped = True
            continue
        if length == 0:
            if not jumped:
                end = off + 1
            return ".".join(labels), end
        labels.append(msg[off + 1:off + 1 + length].decode())
        off += 1 + length


def show_dns(msg, title):
    tid, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", msg[:12])
    qr = flags >> 15
    print(f"Domain Name System ({title})")
    print(f"    Transaction ID: 0x{tid:04x}")
    kind = "Standard query response" if qr else "Standard query"
    rc = flags & 0xF
    print(f"    Flags: 0x{flags:04x} {kind}" + (f", {RCODES.get(rc, rc)}" if qr else ""))
    print(f"        {qr}... .... .... .... = Response: Message is a {'response' if qr else 'query'}")
    op = f"{(flags >> 11) & 0xF:04b}"
    print(f"        .{op[:3]} {op[3]}... .... .... = Opcode: Standard query (0)")
    if qr:
        aa = (flags >> 10) & 1
        print(f"        .... .{aa}.. .... .... = Authoritative: "
              f"{'Server is an authority' if aa else 'Server is not an authority'} for domain")
    print(f"        .... ..{(flags >> 9) & 1}. .... .... = Truncated: Message is not truncated")
    print(f"        .... ...{(flags >> 8) & 1} .... .... = Recursion desired: Do query recursively")
    if qr:
        print(f"        .... .... {(flags >> 7) & 1}... .... = Recursion available: Server can do recursive queries")
        print(f"        .... .... .... {rc:04b} = Reply code: {RCODES.get(rc, rc)} ({rc})")
    print(f"    Questions: {qd}")
    print(f"    Answer RRs: {an}")
    print(f"    Authority RRs: {ns}")
    print(f"    Additional RRs: {ar}")
    off = 12
    print("    Queries")
    for _ in range(qd):
        name, off = read_name(msg, off)
        qtype, qclass = struct.unpack("!HH", msg[off:off + 4])
        off += 4
        print(f"        {name}: type {RR_TYPES.get(qtype, qtype)}, class IN")
    if an:
        print("    Answers")
    for _ in range(an):
        name, off = read_name(msg, off)
        rtype, rclass, ttl, rdlen = struct.unpack("!HHIH", msg[off:off + 10])
        off += 10
        rdata = msg[off:off + rdlen]
        if rtype == 1:
            value = "addr " + socket.inet_ntoa(rdata)
        elif rtype == 28:
            value = "addr " + socket.inet_ntop(socket.AF_INET6, rdata)
        elif rtype in (2, 5, 12):
            value = RR_TYPES[rtype].lower() + " " + read_name(msg, off)[0]
        else:
            value = f"{rdlen} bytes"
        off += rdlen
        print(f"        {name}: type {RR_TYPES.get(rtype, rtype)}, class IN, {value}")
        print(f"            Time to live: {ttl} ({ttl // 60} minutes, {ttl % 60} seconds)")
        print(f"            Data length: {rdlen}")


def dns(name, server="8.8.8.8"):
    tid, query = build_query(name)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    t0 = time.perf_counter()
    sock.sendto(query, (server, 53))
    resp, peer = sock.recvfrom(4096)
    rtt = (time.perf_counter() - t0) * 1000
    local = sock.getsockname()
    sock.close()

    print(f"User Datagram Protocol, Src Port: {local[1]}, Dst Port: 53   ({len(query)} bytes to {server})")
    show_dns(query, "query")
    print()
    print(f"User Datagram Protocol, Src Port: 53, Dst Port: {local[1]}   ({len(resp)} bytes from {peer[0]})")
    show_dns(resp, "response")
    print(f"    [Request matched: transaction ID 0x{tid:04x}]   [Time: {rtt:.1f} ms]")
    print()
    print("Response bytes:")
    hexdump(resp)


# -------------------------------------------------------------------------- HTTP

def http(host):
    request = (f"GET / HTTP/1.1\r\nHost: {host}\r\nUser-Agent: cn-lab-dissector\r\n"
               "Accept: text/html\r\nConnection: close\r\n\r\n").encode()
    sock = socket.create_connection((host, 80), timeout=10)
    peer = sock.getpeername()
    sock.sendall(request)
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    sock.close()

    print(f"Transmission Control Protocol, Dst: {peer[0]}, Dst Port: 80 (http)")
    print(f"Hypertext Transfer Protocol   ({len(request)} bytes, sent in plaintext)")
    for line in request.decode().split("\r\n")[:-2]:
        print(f"    {line}\\r\\n")
    print("    \\r\\n")
    print()
    print("Request bytes on the wire (anyone on the path can read them):")
    hexdump(request, 80)
    print()
    head, _, body = data.partition(b"\r\n\r\n")
    print(f"Hypertext Transfer Protocol   (response, {len(data)} bytes in plaintext)")
    for line in head.decode(errors="replace").split("\r\n")[:9]:
        print(f"    {line}\\r\\n")
    print("    \\r\\n")
    title = body.split(b"<title>")[1].split(b"</title>")[0].decode() if b"<title>" in body else ""
    print(f"    Line-based text data: text/html   <title>{title}</title>")


# --------------------------------------------------------------------------- TLS

def tls_records(stream):
    off = 0
    while off + 5 <= len(stream):
        ctype, ver, length = struct.unpack("!BHH", stream[off:off + 5])
        yield ctype, ver, stream[off + 5:off + 5 + length]
        off += 5 + length


def client_hello_sni(body):
    p = 4 + 2 + 32                       # handshake header, version, random
    p += 1 + body[p]                     # session id
    p += 2 + struct.unpack("!H", body[p:p + 2])[0]   # cipher suites
    p += 1 + body[p]                     # compression methods
    end = p + 2 + struct.unpack("!H", body[p:p + 2])[0]
    p += 2
    while p < end:
        etype, elen = struct.unpack("!HH", body[p:p + 4])
        if etype == 0:
            n = struct.unpack("!H", body[p + 7:p + 9])[0]
            return body[p + 9:p + 9 + n].decode()
        p += 4 + elen
    return "-"


def tls(host):
    try:                                  # Mozilla CA bundle if available
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    tls_obj = ctx.wrap_bio(incoming, outgoing, server_hostname=host)
    sock = socket.create_connection((host, 443), timeout=10)
    peer = sock.getpeername()[0]
    pending = {"client -> server": b"", "server -> client": b""}
    records = []                          # (direction, type, version, body) in time order

    def log(direction, data):
        pending[direction] += data
        buf = pending[direction]
        while len(buf) >= 5:
            length = struct.unpack("!H", buf[3:5])[0]
            if len(buf) < 5 + length:
                break
            records.append((direction, buf[0], struct.unpack("!H", buf[1:3])[0], buf[5:5 + length]))
            buf = buf[5 + length:]
        pending[direction] = buf

    def flush():
        data = outgoing.read()
        if data:
            sock.sendall(data)
            log("client -> server", data)
        return data

    def pull():
        data = sock.recv(65536)
        log("server -> client", data)
        incoming.write(data) if data else incoming.write_eof()
        return data

    while True:
        try:
            tls_obj.do_handshake()
            break
        except ssl.SSLWantReadError:
            flush()
            pull()
    flush()

    request = f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode()
    tls_obj.write(request)
    request_no = len(records) + 1
    app_record = flush()
    plain = b""
    while b"\r\n\r\n" not in plain:
        try:
            plain += tls_obj.read(65536)
        except ssl.SSLWantReadError:
            if not pull():
                break
    sock.close()

    print(f"Transmission Control Protocol, Dst: {peer}, Dst Port: 443 (https)")
    print(f"Negotiated: {tls_obj.version()}, cipher {tls_obj.cipher()[0]}")
    print()
    print(f"{'No.':<4} {'Direction':<17} {'Record type':<19} {'Version':<8} {'Length':>6}  Info")
    for n, (direction, ctype, ver, body) in enumerate(records, start=1):
        info = ""
        if ctype == 22:
            info = HS_TYPES.get(body[0], f"handshake type {body[0]}")
            if body[0] == 1:
                info += f"  (SNI {client_hello_sni(body)} in clear)"
        elif ctype == 23:
            info = "<- our HTTP GET, encrypted" if n == request_no else "encrypted"
        print(f"{n:<4} {direction:<17} {TLS_TYPES.get(ctype, ctype):<19} "
              f"{TLS_VERSIONS.get(ver, hex(ver)):<8} {len(body):>6}  {info}")
    print()
    print(f"The {len(request)}-byte HTTP request, as it actually crossed the network:")
    hexdump(app_record, 80)
    print()
    print("Only the endpoint holding the session keys can decrypt it:")
    print("    " + plain.split(b"\r\n")[0].decode())


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("dns", "http", "tls"):
        print(__doc__)
        sys.exit(1)
    mode, target = sys.argv[1], sys.argv[2]
    if mode == "dns":
        dns(target, *(sys.argv[3:4]))
    elif mode == "http":
        http(target)
    else:
        tls(target)
