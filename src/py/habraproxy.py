# coding=utf-8

#  habraproxy.py — это простейший http-прокси-сервер, запускаемый локально (порт на ваше
#  усмотрение), который показывает содержимое страниц Хабра. С одним исключением: после
#  каждого слова из шести букв должен стоять значок «™». Примерно так:
#
#  http://habrahabr.ru/company/yandex/blog/258673/
#  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#  Сейчас на фоне уязвимости Logjam все в индустрии в очередной раз обсуждают проблемы и
#  особенности TLS. Я хочу воспользоваться этой возможностью, чтобы поговорить об одной из
#  них, а именно — о настройке ciphersiutes.
#
#  http://127.0.0.1:8232/company/yandex/blog/258673/
#  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#  Сейчас™ на фоне уязвимости Logjam™ все в индустрии в очередной раз обсуждают проблемы и
#  особенности TLS. Я хочу воспользоваться этой возможностью, чтобы поговорить об одной из
#  них, а именно™ — о настройке ciphersiutes.
#
#  Условия:
#    * Python 2.x
#    * можно использовать любые общедоступные библиотеки, которые сочтёте нужным
#    * чем меньше кода, тем лучше. PEP8 — обязательно
#    * в случае, если не хватает каких-то данных, следует опираться на здравый смысл
#
#  Если задача кажется слишом простой, можно добавить следующее:
#    * параметры командной строки (порт, хост, сайт, отличный от хабра и т.п.)
#    * после старта локального сервера автоматически запускается браузер с открытой
#      обработанной™ главной страницей

import re
import webbrowser
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urllib2 import urlopen
from threading import Thread
from argparse import ArgumentParser


class ResponseData:
    def __init__(self, response_fileobject):
        self.status = response_fileobject.getcode()
        self.headers = response_fileobject.info().dict
        self.content = response_fileobject.read()


class ProxyHandler(BaseHTTPRequestHandler):
    SOURCE = 'http://habrahabr.ru'

    def _query_response_from_source(self):
        response_fileobject = urlopen(ProxyHandler.SOURCE + self.path)

        try:
            response_object = ResponseData(response_fileobject)
        finally:
            response_fileobject.close()

        return response_object

    @staticmethod
    def _process_response(response_object):
        trademark = u'&#8482;'
        add_trademark_pattern = r'(<script.+?>.+<\/script>)|' \
                                '(<style.+?>.+?<\/style>)|' \
                                '(<.+?\/?>)|' \
                                '(?<!<)(?<!<\/)(?<!\w)(?P<word>[\w]{6})(?!\w)(?!\/?>)'
        regex_flags = re.UNICODE | re.MULTILINE

        str_content = response_object.content.decode('utf-8')

        def replace(match):
            if match.group('word'):
                return match.group('word') + trademark
            else:
                return match.group(0)

        str_content = re.sub(add_trademark_pattern, replace, str_content, flags=regex_flags)

        response_object.content = str_content.encode('utf-8')
        response_object.headers['content-length'] = len(response_object.content)

    @staticmethod
    def _is_html_response(response_object):
        return 'content-type' in response_object.headers \
               and 'text/html' in response_object.headers['content-type']

    def _write_response_to_client(self, response_object):
        self.send_response(response_object.status)

        for (k, v) in response_object.headers.items():
            self.send_header(k, v)
        self.end_headers()

        self.wfile.write(response_object.content)

    def do_GET(self):
        response = self._query_response_from_source()

        if response.status == 200 and ProxyHandler._is_html_response(response):
            ProxyHandler._process_response(response)

        self._write_response_to_client(response)


def main():
    parse = ArgumentParser('just for fun proxy')

    parse.add_argument('host', default='localhost', help='host')
    parse.add_argument('port', default='9090', type=int, help='port')
    parse.add_argument('-s', default='http://habrahabr.ru', dest='source', help='source like http://habrahabr.ru')

    args = parse.parse_args()

    server = None
    try:
        ProxyHandler.SOURCE = args.source

        server = HTTPServer((args.host, args.port), ProxyHandler)

        thread = Thread(target=lambda: server.serve_forever())
        thread.start()

        running_at = "%s:%s" % (args.host, args.port)

        print "running at %s, source %s" % (running_at, args.source)
        print "type ctrl+c for interrupt"

        webbrowser.open('http://' + running_at)

        while True:  # hack, because thread.join ignoring CTRL+C
            thread.join(100)

    finally:
        if server:
            server.server_close()


if __name__ == '__main__':
    main()
