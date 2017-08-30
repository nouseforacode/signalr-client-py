from signalr.events import EventHook


class Hub:
    def __init__(self, name, connection):
        self.name = name
        self.server = HubServer(name, connection, self)
        self.client = HubClient(name, connection)
        self.error = EventHook()


class HubServer:
    def __init__(self, name, connection, hub):
        self.name = name
        self.__connection = connection
        self.__hub = hub
        self.__rspHandlers = rspHandlers = {}

        def handle(**kwargs):
            if 'R' in kwargs:
                assert 'I' in kwargs
                callId = int(kwargs['I'])
                if callId in self.__rspHandlers:
                    rspArgs = kwargs['R'] if 'R' in kwargs else {}
                    rspHandlers[callId](**rspArgs)
                    del rspHandlers[callId]

        connection.received += handle

    def invoke(self, method, *data, **kwargs):
        callback = kwargs["response"] if "response" in kwargs else None
        callId = self.__connection.increment_send_counter()
        self.__connection.send({
            'H': self.name,
            'M': method,
            'A': data,
            'I': callId
        })
        if callback is not None:
            self.__rspHandlers[ callId ] = callback


class HubClient(object):
    def __init__(self, name, connection):
        self.name = name
        self.__handlers = {}

        def handle(**kwargs):
            if 'M' in kwargs:
                for inner_data in kwargs['M']:
                    hub = inner_data['H'] if 'H' in inner_data else ''
                    if hub.lower() == self.name.lower():
                        method = inner_data['M']
                        if method in self.__handlers:
                            arguments = inner_data['A']
                            self.__handlers[method].fire(*arguments)

        connection.received += handle

    def on(self, method, handler):
        if method not in self.__handlers:
            self.__handlers[method] = EventHook()
        self.__handlers[method] += handler

    def off(self, method, handler):
        if method in self.__handlers:
            self.__handlers[method] -= handler


class DictToObj:
    def __init__(self, d):
        self.__dict__ = d
