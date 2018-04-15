import socket
import ssl
import base64
import select
import re

def send_recv(command, socket):
    command += b'\n'
    socket.send(command)
    res = b''
    while True:
        try:
            data = socket.recv(1024)
            res += data
        except Exception:
            break
    return res.decode(encoding='utf-8')

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(1)
    s = ssl.wrap_socket(s)
    s.connect(('pop.yandex.ru', 995))
    print(s.recv(1024))
    print(send_recv(b'USER ivanugriumov@yandex.ru', s))
    print(send_recv(b'PASS alinor99', s))
    print(send_recv(b'STAT', s))
    print(send_recv(b'LIST', s))
#    print(send_recv(b'TOP 1 10', s))
    message = (send_recv(b'RETR 1', s))
    regex = re.compile('(Subject: |\t)=\?utf-8\?B\?(.*?)\?=')
    result = regex.findall(message)
    print(result)
    print(send_recv(b'QUIT', s))
