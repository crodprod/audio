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
        # print('ok')
        connected.remove(websocket)


async def main():
    async with websockets.serve(handler, "localhost", 8010):
        logging.info("WebSocket server started and listening on ws://localhost:8010")
        await asyncio.Future()


asyncio.run(main())
