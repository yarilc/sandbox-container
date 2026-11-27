"""Disposable TLS fixture entrypoint using the selected production proxy code."""
import asyncio
import json
from pathlib import Path
import socket
import ssl
import sys

sys.path.insert(0, '/opt/sandbox-egress')
import proxy

original_resolver = socket.getaddrinfo


def resolve(host, port, *args, **kwargs):
    # Exact fixture-only DNS mapping. Production resolution/address validation
    # still executes against the separate protected fixture policy.
    return original_resolver('127.0.0.1' if host == 'qualification.invalid' else host, port, *args, **kwargs)


socket.getaddrinfo = resolve


def mirror_fixture_resolver(host, port, allowed):
    if (host, port, allowed) == ('qualification.invalid', 8443, None):
        allowed = ['127.0.0.1']
    return proxy.resolved_addresses(host, port, allowed)


async def main():
    trust = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    trust.load_cert_chain('/qualification/cert.pem', '/qualification/key.pem')
    counts = []
    requests = []

    # TLS handshake buffering must be counted before SSL consumes ClientHello.
    # A blocking listener in an independent thread provides MSG_PEEK counters.
    import threading
    listener = socket.socket()
    listener.bind(('127.0.0.1', 8443)); listener.listen(8)

    def serve():
        while True:
            raw, _ = listener.accept()
            raw.settimeout(5)
            try:
                count = len(raw.recv(16384, socket.MSG_PEEK))
                if count:
                    with trust.wrap_socket(raw, server_side=True) as secure:
                        header = bytearray()
                        while not header.endswith(b'\r\n\r\n') and len(header) < 8192:
                            chunk = secure.recv(1024)
                            if not chunk:
                                break
                            header.extend(chunk)
                        first, *fields = header.decode('ascii').split('\r\n')
                        method, target, _ = first.split(' ')
                        if target == '/':
                            counts.append(count)
                            Path('/logs/qualification-counts.json').write_text(json.dumps(counts))
                            body = b'qualification-tls-positive'
                        else:
                            headers = {line.partition(':')[0].lower() for line in fields}
                            credentials = bool(headers & {'authorization', 'cookie', 'proxy-authorization', 'x-api-key'})
                            requests.append([method, target, credentials])
                            Path('/logs/qualification-mirror.json').write_text(json.dumps(requests))
                            body = b'qualification-mirror-positive'
                        secure.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: '
                                       + str(len(body)).encode() + b'\r\n\r\n' + body)
                else:
                    counts.append(count)
                    Path('/logs/qualification-counts.json').write_text(json.dumps(counts))
            finally:
                raw.close()

    threading.Thread(target=serve, daemon=True).start()
    await proxy.main(mirror_resolver=mirror_fixture_resolver)


if __name__ == '__main__':
    asyncio.run(main())
