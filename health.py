import asyncio


async def handle_connection(reader: asyncio.StreamReader, writer) -> None:
    try:
        request = await reader.read(2048)
        path = request.split(b" ", 2)[1] if b" " in request else b"/"
        if path == b"/health":
            status = b"200 OK"
            body = b'{"ok":true}'
        else:
            status = b"404 Not Found"
            body = b'{"ok":false}'
        writer.write(
            b"HTTP/1.1 " + status + b"\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + body
        )
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def start(port: int):
    return await asyncio.start_server(handle_connection, "0.0.0.0", port)
