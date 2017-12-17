import json
import sys

import gevent

if sys.version_info[0] < 3:
    from urlparse import urlparse, urlunparse
else:
    from urllib.parse import urlparse, urlunparse

from websocket import create_connection
from ._transport import Transport

import logging
logger = logging.getLogger(__name__)


class WebSocketsTransport(Transport):
    def __init__(self, session, connection):
        Transport.__init__(self, session, connection)
        self.ws = None
        self.__requests = {}

    def _get_name(self):
        return 'webSockets'

    @staticmethod
    def __get_ws_url_from(url):
        parsed = urlparse(url)
        scheme = 'wss' if parsed.scheme == 'https' else 'ws'
        url_data = (scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)

        return urlunparse(url_data)

    def beat(self):
        while True:
            try:
                self.ws.send("{}")
                logger.debug("ping")
                gevent.sleep(1)
            except Exception as e:
                logger.error(e)
                self._connection.close()
                break
        
    def start(self):
        ws_url = self.__get_ws_url_from(self._get_url('connect'))
        header = self.__get_headers()
        cookie = self.__get_cookie_str()
        
        logger.debug("Creating connection: %s\n\n\t%s\n\n\t%s" % (ws_url, "\n\t".join(header), "\n\t".join(cookie.split(';'))))
        self.ws = create_connection(ws_url,
                                    header=header,
                                    cookie=cookie,
                                    enable_multithread=True)

        self.__beat = gevent.spawn(self.beat)
        
        start_url = self._get_url('start')
        logger.debug("Getting %s" % start_url)

        response = self._session.get(start_url)
        logger.debug("Response %s" % response.text)

        def _receive():
            for notification in self.ws:
                self._handle_notification(notification)

        return _receive

    def send(self, data):
        self.ws.send(json.dumps(data))
        gevent.sleep()

    def close(self):
        gevent.kill(self.__beat)
        try:
            self.ws.close()
        except:
            pass

    def accept(self, negotiate_data):
        return bool(negotiate_data['TryWebSockets'])

    class HeadersLoader(object):
        def __init__(self, headers):
            self.headers = headers

    def __get_headers(self):
        headers = self._session.headers
        loader = WebSocketsTransport.HeadersLoader(headers)

        if self._session.auth:
            self._session.auth(loader)

        return ['%s: %s' % (name, headers[name]) for name in headers]

    def __get_cookie_str(self):
        return '; '.join([
                             '%s=%s' % (name, value)
                             for name, value in self._session.cookies.items()
                             ])
