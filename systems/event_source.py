import trio


class AsyncEventSource:
    def __init__(self, nursery, notification_callbacks=None, error_callbacks=None):
        """
        Base class for event sources that ONLY implement asynchronous callbacks

        :param nursery nursery: Trio nursery. Needed in order to raise asynchronous events without waiting for them
        :param List[async function] notification_callbacks: list of async functions to be notified of the event
        :param List[async function] error_callbacks: list of async functions to be called when an error happens
        """
        if nursery is None:
            raise ValueError("nursery is required for an AsyncEventSource object")
        self._a_notification_cb = notification_callbacks if notification_callbacks is not None else []
        self._a_error_cb = error_callbacks if error_callbacks is not None else []
        self.nursery = nursery

    def subscribe(self, notification_callbacks=None, error_callbacks=None):
        """
        Adds the provided notification and error callbacks to the stored lists.
        Does nothing if the lists are empty (or None), or if some of their elements are already subscribed

        :param List[async function] notification_callbacks: new notification callbacks
        :param List[async function] error_callbacks: new error callbacks
        """
        if notification_callbacks is not None:
            new_notification_cb = list(set(notification_callbacks) - set(self._a_notification_cb))
            self._a_notification_cb = self._a_notification_cb + new_notification_cb

        if error_callbacks is not None:
            new_error_cb = list(set(error_callbacks) - set(self._a_error_cb))
            self._a_error_cb = self._a_error_cb + new_error_cb

    def unsubscribe(self, notification_callbacks=None, error_callbacks=None):
        """
        Removes the provided notification and error callbacks from the stored lists.
        Does nothing if the lists are empty (or None), or if some of their elements were not subscribed

        :param List[async function] notification_callbacks: removed notification callbacks
        :param List[async function] error_callbacks: removed error callbacks
        """
        if notification_callbacks is not None:
            self._a_notification_cb = list(set(self._a_notification_cb) - set(notification_callbacks))
        if error_callbacks is not None:
            self._a_error_cb = list(set(self._a_error_cb) - set(error_callbacks))

    async def raise_event(self, param):
        """
        Calls all subscribed functions (event handles).

        :param param: SECOND parameter passed to all subscribed functions (first one being SELF)
        """
        for event_handle in self._a_notification_cb:
            self.nursery.start_soon(event_handle, self, param)

    async def raise_error(self, param):
        """
        Calls all subscribed error functions (error event handles). If a nursery is defined, it is used.
        Otherwise, a new one is created and this acts as the parent of all callbacks (thus blocking
        until they all finish).

        :param param: SECOND parameter passed to all subscribed error functions (first one being SELF)
        """
        for event_handle in self._a_error_cb:
            self.nursery.start_soon(event_handle, self, param)


class BaseEventArgs:
    """
    Class to be inherited by specialized events. To be passed as the "param" attribute in raise_event
    """
    def __init__(self, event_type: str):
        self.event_type = event_type  # type: str


if __name__ == "__main__":
    """
    Sample code. The classes here are intended to be inherited, since they do not raise any event by themselves.
    """
    class SampleProducer(AsyncEventSource):
        def __init__(self, nursery, *args, **kwargs):
            # Nothing to do here (simple example, __init__ method could be deleted)
            super().__init__(nursery, *args, **kwargs)

        async def main_loop(self):
            divisor = 5
            dividend = 10
            try:
                while True:
                    await self.raise_event(dividend/divisor)
                    divisor -= 1
                    await trio.sleep(1)
            except ZeroDivisionError as e:
                await self.raise_error(f"!! ERROR: {e}")
                print("PRODUCER - Zero reached, finalizing producer")

    async def async_timer():
        counter = 0
        while True:
            print(f"### {counter}s ###")
            counter += 1
            await trio.sleep(1)

    async def consumer_1(source, param):
        # print("CONSUMER 1 - Starting asynchronous consumer 1")
        await trio.sleep(3)
        print(f"CONSUMER 1 - Received value: {param}. Caller type: {type(source)}")

    async def consumer_2(source, param):
        # print("CONSUMER 2 - Starting asynchronous consumer 2")
        await trio.sleep(3)
        print(f"CONSUMER 2 - Received value: {param}. Caller type: {type(source)}")

    async def parent():
        async with trio.open_nursery() as nursery:
            producer = SampleProducer(nursery)
            # Only consumer 1 is subscribed for regular events, but both are subscribed for the error events
            # Normally, a different method is used for regular events and error handling
            producer.subscribe(notification_callbacks=[consumer_1], error_callbacks=[consumer_1, consumer_2])
            # Now, the consumer_1 method is unsubscribed as error handle (just as an example)
            producer.unsubscribe(error_callbacks=[consumer_1])
            nursery.start_soon(async_timer)
            nursery.start_soon(producer.main_loop)

    trio.run(parent)



