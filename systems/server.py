import trio
import httpx
import random
import string
import socket
from typing import List, Union
from systems.event_source import AsyncEventSource, BaseEventArgs


SESSION_ID_LENGTH = 30


class Server(AsyncEventSource):
    SESSION_REGISTER_ERROR = "SESSION_REGISTER_ERROR"
    SESSION_UPDATE_ERROR = "SESSION_UPDATE_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"

    def __init__(self, ip_address, port, sensor_data, rover_id,
                 nursery, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks=notification_callbacks, error_callbacks=error_callbacks)
        self._IP_ADDRESS = ip_address
        self._PORT = port
        self._FULL_ADDRESS = f"http://{ip_address}:{port}/"
        self._ROVER_ID = rover_id
        self._ROVER_ADDRESS = find_ip_address()
        self._data = sensor_data
        self._continue_running = False
        # Event to prevent multiple simultaneous update loops:
        #   "a_run_update_loop" called before the existing one wakes up after "stop_update_loop"
        self._exited_update_loop = trio.Event()
        self._exited_update_loop.set()  # Event is initially set (no update loop is running)

    async def initialize_session(self, start_update_loop=False):
        self.stop_update_loop()
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                await self._register_rover(client)
                for _ in range(3):  # Maximum 3 tries to generate a random session ID
                    self._define_new_session()
                    result = await self._register_session(client)
                    if result == 200:
                        break
                if result != 200:
                    await self.raise_error(ServerErrorArgs(self.SESSION_REGISTER_ERROR, self._continue_running))
                    return
                await self._update_rover(client)
        except httpx.TimeoutException:
            await self.raise_error(ServerErrorArgs(self.CONNECTION_ERROR, self._continue_running))
            return
        if start_update_loop:
            await self.a_run_update_loop()

    async def a_run_update_loop(self):
        if self._continue_running:
            return
        self._continue_running = True
        # If the existing update loop did not have time to wake up, just let it continue and abort the new one
        if not self._exited_update_loop.is_set():
            return
        async with httpx.AsyncClient(timeout=3) as client:
            try:
                while self._continue_running:
                    code = await self._update_session(client)
                    if code != 200:
                        await self.raise_error(ServerErrorArgs(self.SESSION_UPDATE_ERROR, self._continue_running))
                    await trio.sleep(1)
            except httpx.TimeoutException:
                await self.raise_error(ServerErrorArgs(self.CONNECTION_ERROR, self._continue_running))
        self._continue_running = False
        self._exited_update_loop.set()  # Free the way for another future update loop

    def stop_update_loop(self):
        self._continue_running = False

    async def _register_rover(self, client):
        msg = {'rover_id': self._ROVER_ID, 'address': self._ROVER_ADDRESS}
        ans = await client.post(self._FULL_ADDRESS + "api/rover/", json=msg)
        print(f"Sent rover registration. Status code: {ans.status_code}")
        return ans.status_code

    async def _register_session(self, client):
        msg = {'session_id': self._session_id, 'rover_id': self._ROVER_ID}
        ans = await client.post(self._FULL_ADDRESS + "api/session/", json=msg)
        print(f"Sent session registration. Status code: {ans.status_code}")
        return ans.status_code

    async def _update_rover(self, client):
        msg = {'rover_id': self._ROVER_ID, 'last_session': self._session_id, 'address': self._ROVER_ADDRESS}
        ans = await client.put(self._FULL_ADDRESS + "api/rover/" + self._ROVER_ID + "/", json=msg)
        print(f"Sent rover update. Status code: {ans.status_code}")
        return ans.status_code

    async def _update_session(self, client):
        ans = await client.put(self._FULL_ADDRESS + "api/session/" + self._session_id + "/", json=self._data)
        print(f"---> Sent session update. Status code: {ans.status_code}\n{self._data}")
        return ans.status_code

    def _define_new_session(self):
        self._session_id = generate_session_id()
        self._data['session_id'] = self._session_id
        self._data['rover_id'] = self._ROVER_ID


class DummyServer(AsyncEventSource):
    def __init__(self, ip_address, port, sensor_data, rover_id,
                 nursery, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks=notification_callbacks, error_callbacks=error_callbacks)

    async def initialize_session(self, start_update_loop=False):
        pass

    async def a_run_update_loop(self):
        pass

    async def stop_notification_loop(self):
        pass


class ServerErrorArgs(BaseEventArgs):
    def __init__(self, event_type: str, is_server_running: bool):
        super().__init__(event_type)
        self.is_server_running = is_server_running  # type: bool


def find_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    address = s.getsockname()[0]
    s.close()
    return address


def generate_session_id():
    return ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=SESSION_ID_LENGTH))