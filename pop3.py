import socket
import ssl
import base64
import select
import re
from collections import defaultdict
from hashlib import md5


def recv_all(socket):
    res = b''
    while True:
        try:
            data = socket.recv(1024)
            res += data
        except:
            break
    return res.decode()[:-1]


def send_recv(command, socket):
    socket.send(command.encode() + b'\n')
    return recv_all(socket)


def transform_utf8(value):
    last_index = 0
    result = []
    for match in re.finditer(r'=\?utf-8\?b\?(.+?)\?=', value, re.IGNORECASE):
        result.append(value[last_index: match.start()])
        last_index = match.end()
        result.append(base64.b64decode(match.group(1)).decode())
    result.append(value[last_index:])
    return ''.join(result)


def parse_mail(mail):
    if '\n\n' not in mail:
        return {}, mail
    headers = defaultdict(list)
    head, body = mail.split('\n\n', 1)
    last = ''
    for line in head.split('\n'):
        if ':' not in line or not line[0].strip():
            headers[last].append(line.lstrip())
            continue
        name, value = line.split(': ', 1)
        last = name
        headers[name].append(value)
    headers = {k.lower():transform_utf8(''.join(v)) for k, v in headers.items()}
    return headers, body


def parse_ct(content_type):
    param_regex = r'(?:;\s*(.+?)=([^;]+))?'
    match = re.match(r'(.+?)/([^;]+)' + param_regex * 10, content_type, re.DOTALL)
    if not match:
        return
    type, subtype, *params = match.groups()
    params = list(filter(bool, params))
    return type, subtype, dict(zip(params[::2], params[1::2]))


def parse_body(ct, body):
    type, _, params = ct
    if type == 'multipart':
        parts = []
        boundary = params['boundary'][1:-1]
        if boundary.startswith('----=='):
            boundary = re.escape(boundary[6:])
        else:
            boundary = '--' + re.escape(boundary)
        for part in re.split(boundary + r'(?:--)?', body):
            parts.append(parse_mail_full(part))
        return parts
    else:
        return body


def parse_mail_full(mail):
    headers, body = parse_mail(mail)
    ct = parse_ct(headers.get('content-type', 'text/plain'))
    parsed_body = parse_body(ct, body)
    return {
        'headers': headers,
        'content-type': ct,
        'body': parsed_body,
        'from': headers.get('from', '<unknown>'),
        'subject': headers.get('subject', '<unknown>'),
    }


def save_file(contents, extension, depth=0, padding='\t'):
    m = md5()
    m.update(contents)
    hashname = f'{m.hexdigest()}.{extension}'
    with open(hashname, 'wb') as file:
        file.write(contents)
    print(f'{padding*depth}>> Saved as:', hashname)


def traverse_mail_body(mail, depth=0, padding='\t'):
    ct = mail['content-type']
    type, extension, params = ct
    print(f'{padding*depth}>> Content type:', type, extension)
    if type == 'multipart':
        for part in (x for x in mail['body'] if x['body']):
            traverse_mail_body(part, depth + 1)
    elif type == 'text':
        text = mail['body']
        if mail.get('content-transfer-encoding', 'plain') == 'base64':
            text = base64.b64decode(text).decode()
        text = repr(text)
        if len(text) > 50:
            text = text[:50] + "' ..."
        print(f'{padding*depth}>> Text:', text)
        save_file(mail['body'].encode(), extension, depth, padding)
    elif type == 'image':
        filename = params.get('name', f'noname.{extension}')
        print(f'{padding*depth}>> Image:', filename)
        save_file(base64.b64decode(mail['body'].replace('\n', '')), extension, depth, padding)


def download_mail(s, n):
    mail = send_recv(f'TOP {n}', s)
    mail = '\n'.join(mail.replace('\r', '').split('\n')[1:-1])
    mail = parse_mail_full(mail)
    print('>> From:', repr(mail['from']))
    print('>> Subject:', repr(mail['subject']))
    traverse_mail_body(mail)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        s = ssl.wrap_socket(s)
        s.connect(('pop.yandex.ru', 995))
        s.recv(1024)
        print(send_recv('USER ivanugriumov@yandex.ru', s))
        print(send_recv('PASS alinor99', s))
        while 1:
            whole_command = input('pop3> ')
            command, *args = whole_command.split()
            if command == 'exit':
                s.send(b'QUIT\n')
                return
            elif command == 'download':
                download_mail(s, *map(int, args))
            else:
                print(send_recv(whole_command, s))

main()
