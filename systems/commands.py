from systems.event_source import AsyncEventSource, BaseEventArgs
import trio
import json

class CommandSystem(AsyncEventSource):
    COMMAND_EVENT = "COMMAND_EVENT"
    MODE_COMMAND = "SELECT_MODE"
    DIRECTION_COMMAND = "SET_DIRECTION"
    SESSION_COMMAND = "NEW_SESSION"

    DIRECTION_FORWARDS = "FORWARDS"
    DIRECTION_LEFT = "LEFT"
    DIRECTION_RIGHT = "RIGHT"
    DIRECTION_BACKWARDS = "BACKWARDS"
    DIRECTION_STOP = "STOP"

    def __init__(self, port, nursery, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        self._COMMAND_PORT = port
        self._socket = trio.socket.socket(trio.socket.AF_INET, trio.socket.SOCK_DGRAM)

    async def run(self):
        await self._socket.bind(('localhost', self._COMMAND_PORT))
        while True:
            try:
                data, addr = await self._socket.recvfrom(1024)
                decoded_data = json.loads(data.decode('UTF-8'))
                await self.raise_event(CommandEventArgs(self.COMMAND_EVENT, decoded_data))
            except Exception as e:
                print(f"!!!! Unknown command exception: {e}")


class CommandEventArgs(BaseEventArgs):
    def __init__(self, event_type: str, data: dict):
        super().__init__(event_type)
        self.data = data  # type: dict