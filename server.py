import asyncio
import websockets
import logging

connected = set()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


async def handler(websocket, path):
    connected.add(websocket)
    try:
        async for message in websocket:
            logging.info(f"Received message: {message} from {websocket.remote_address}")
            for conn in connected:
                if conn != websocket:
                    logging.info(f"Sending message: {message} to {conn.remote_address}")
                    await conn.send(message)
    except Exception:
        pass
    finally:
        connected.remove(websocket)


async def main():
    host, port = "localhost", 8010
    async with websockets.serve(handler, host, port):
        logging.info(f"WebSocket server started and listening on ws://{host}:{port}")
        await asyncio.Future()


asyncio.run(main())
