"""Confined loopback adapters over the bootstrap's sole data descriptor."""
import asyncio
from contextlib import AsyncExitStack
import os
import signal
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mux import Channel, MAX_MIRROR_STREAMS, MAX_STREAMS, MIRROR_OPEN, ProtocolError, StreamClosed, bridge


class Relay:
    def __init__(self, channel):
        self.channel = channel
        self.active = 0
        self.mirror_active = 0

    async def handle(self, reader, writer):
        if self.active >= MAX_STREAMS or self.channel.closed:
            writer.close()
            return
        self.active += 1
        stream = None
        established = False
        try:
            request = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 10)
            if len(request) > 8192:
                raise ProtocolError()
            # The trusted proxy independently validates the exact authority.
            parts = request.split(b'\r\n', 1)[0].split(b' ')
            if len(parts) != 3 or parts[0] != b'CONNECT' or parts[2] not in (b'HTTP/1.0', b'HTTP/1.1'):
                raise ProtocolError()
            stream = await self.channel.open(parts[1])
            writer.write(b'HTTP/1.1 200 Connection established\r\n\r\n')
            await writer.drain()
            established = True
            await bridge(stream, reader, writer)
        except (ProtocolError, StreamClosed, OSError, asyncio.TimeoutError,
                asyncio.LimitOverrunError, asyncio.IncompleteReadError):
            if not established:
                writer.write(b'HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
                try:
                    await writer.drain()
                except OSError:
                    pass
        finally:
            writer.close()
            self.active -= 1
            if stream:
                await stream.close()


    async def handle_mirror(self, reader, writer):
        if self.active >= MAX_STREAMS or self.mirror_active >= MAX_MIRROR_STREAMS or self.channel.closed:
            writer.close()
            return
        self.active += 1
        self.mirror_active += 1
        stream = None
        try:
            header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 10)
            stream = await self.channel.open(header, kind=MIRROR_OPEN)
            while data := await stream.read():
                writer.write(data)
                await asyncio.wait_for(writer.drain(), 30)
        except (ProtocolError, StreamClosed, OSError, asyncio.TimeoutError,
                asyncio.LimitOverrunError, asyncio.IncompleteReadError):
            if stream is None:
                writer.write(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
                try:
                    await asyncio.wait_for(writer.drain(), 5)
                except (OSError, asyncio.TimeoutError):
                    pass
        finally:
            writer.close()
            self.active -= 1
            self.mirror_active -= 1
            if stream is not None:
                await stream.close()


async def run(channel_socket, ready, *, provider=True, dependency=False):
    reader, writer = await asyncio.open_connection(sock=channel_socket, limit=65536)
    channel = await Channel(reader, writer).start()
    relay = Relay(channel)
    try:
        async with AsyncExitStack() as listeners:
            if provider:
                await listeners.enter_async_context(await asyncio.start_server(
                    relay.handle, '127.0.0.1', 18080, limit=8192, backlog=64))
            if dependency:
                await listeners.enter_async_context(await asyncio.start_server(
                    relay.handle_mirror, '127.0.0.1', 18081, limit=8192, backlog=64))
            os.write(ready, b'1')
            os.close(ready)
            await channel.receiver
    finally:
        await channel.close()


if __name__ == '__main__':
    application = sys.argv[1:]
    mode = application.pop(0) if application and application[0] in ('--mirror-only', '--mirror-with-provider') else ''
    if not application or not application[0].startswith('/'):
        sys.exit('relay requires an absolute application path')
    channel_socket = socket.socket(fileno=3)
    channel_socket.setblocking(False)
    ready_read, ready_write = os.pipe2(os.O_CLOEXEC)
    pid = os.fork()
    if pid == 0:
        os.close(ready_read)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        try:
            asyncio.run(run(channel_socket, ready_write, provider=mode != '--mirror-only', dependency=bool(mode)))
        except (OSError, ProtocolError, StreamClosed, asyncio.TimeoutError, asyncio.IncompleteReadError):
            pass
        finally:
            os._exit(78)
    channel_socket.close()
    os.close(ready_write)
    # Bound pre-exec readiness and never execute the application if handshake/bind failed.
    import select
    available, _, _ = select.select([ready_read], [], [], 15)
    success = bool(available) and os.read(ready_read, 1) == b'1'
    os.close(ready_read)
    if not success:
        os.kill(pid, signal.SIGTERM)
        os.waitpid(pid, 0)
        sys.exit('relay preparation failed; restricted startup stopped')
    os.execv(application[0], application)
