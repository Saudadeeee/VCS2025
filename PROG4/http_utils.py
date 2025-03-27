import socket
import re
import ssl
from urllib.parse import urlparse

def parse_url(url):
    parsed = urlparse(url)
    protocol = parsed.scheme
    host = parsed.netloc
    path = parsed.path if parsed.path else '/'
    port = 443 if protocol == 'https' else 80
    
    if ':' in host:
        host, port_str = host.split(':')
        port = int(port_str)
        
    return protocol, host, port, path

def create_socket_connection(host, port, is_https=False):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    if is_https:
        context = ssl.create_default_context()
        sock = context.wrap_socket(sock, server_hostname=host)
    
    sock.connect((host, port))
    return sock

def receive_response(sock):
    response = b''
    while True:
        data = sock.recv(4096)
        if not data:
            break
        response += data
        
        if b'\r\n0\r\n\r\n' in response or not b'Transfer-Encoding: chunked' in response:
            if b'\r\n\r\n' in response:
                header_end = response.find(b'\r\n\r\n') + 4
                headers = response[:header_end].decode('utf-8', errors='ignore')
                
                content_length_match = re.search(r'Content-Length: (\d+)', headers)
                if content_length_match:
                    content_length = int(content_length_match.group(1))
                    if len(response) - header_end >= content_length:
                        break
                else:
                    break
    
    return response

def parse_headers_and_body(response):
    header_end = response.find(b'\r\n\r\n')
    if (header_end == -1):
        return {}, b''
    
    headers_raw = response[:header_end].decode('utf-8', errors='ignore')
    body = response[header_end + 4:]
    
    if b'Transfer-Encoding: chunked' in response[:header_end]:
        decoded_body = b''
        while body:
            chunk_size_end = body.find(b'\r\n')
            if chunk_size_end == -1:
                break
            
            chunk_size_hex = body[:chunk_size_end].decode('ascii', errors='ignore').strip()
            try:
                chunk_size = int(chunk_size_hex, 16)
            except ValueError:
                break
                
            if chunk_size == 0:
                break
                
            chunk_data_start = chunk_size_end + 2
            chunk_data_end = chunk_data_start + chunk_size
            decoded_body += body[chunk_data_start:chunk_data_end]
            
            body = body[chunk_data_end + 2:]
            
        body = decoded_body
    
    headers = {}
    for line in headers_raw.split('\r\n')[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key] = value
    
    return headers, body

def extract_title(html):
    match = re.search(b'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).decode('utf-8', errors='ignore').strip()
    return None