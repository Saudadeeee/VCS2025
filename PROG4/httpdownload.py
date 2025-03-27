#!/usr/bin/env python3
import argparse
from http_utils import parse_url, create_socket_connection, receive_response, parse_headers_and_body

def main():
    parser = argparse.ArgumentParser(description='Download a file from a WordPress site')
    parser.add_argument('--url', required=True, help='WordPress site URL')
    parser.add_argument('--remote-file', required=True, help='Path to remote file to download')
    args = parser.parse_args()
    
    url = args.url
    remote_file = args.remote_file
    
    protocol, host, port, _ = parse_url(url)
    is_https = protocol == 'https'
    
    if not remote_file.startswith('/'):
        remote_file = '/' + remote_file
    
    sock = create_socket_connection(host, port, is_https)
    
    request = f"GET {remote_file} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    request += "Accept: */*\r\n"
    request += "Connection: close\r\n\r\n"
    
    sock.sendall(request.encode())
    
    response = receive_response(sock)
    sock.close()
    
    status_line = response.split(b'\r\n', 1)[0].decode('utf-8', errors='ignore')
    status_code = int(status_line.split(' ')[1]) if len(status_line.split(' ')) > 1 else 0
    
    if status_code == 404:
        print("Không tồn tại file ảnh")
        return
    
    headers, body = parse_headers_and_body(response)
    
    if body:
        print(f"Kích thước file ảnh: {len(body)} bytes")
    else:
        print("Không tồn tại file ảnh")

if __name__ == "__main__":
    main()