#!/usr/bin/env python3
import re
import argparse
import urllib.parse
import os
import random
import string
import json
from http_utils import parse_url, create_socket_connection, receive_response, parse_headers_and_body

def get_wordpress_cookies(host, port, username, password, is_https):
    sock = create_socket_connection(host, port, is_https)
    
    login_path = "/wp-login.php"
    request = f"GET {login_path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    request += "Accept: text/html,application/xhtml+xml,application/xml\r\n"
    request += "Connection: close\r\n\r\n"
    
    sock.sendall(request.encode())
    response = receive_response(sock)
    sock.close()
    
    headers, body = parse_headers_and_body(response)
    
    initial_cookies = []
    for key, value in headers.items():
        if key.lower() == 'set-cookie':
            cookie_parts = value.split(';')[0]
            initial_cookies.append(cookie_parts)
    
    hidden_inputs = {}
    for match in re.finditer(b'<input[^>]*type=[\'"]hidden[\'"][^>]*>', body, re.IGNORECASE):
        input_tag = match.group(0).decode('utf-8', errors='ignore')
        name_match = re.search(r'name=[\'"]([^\'"]+)[\'"]', input_tag)
        value_match = re.search(r'value=[\'"]([^\'"]*)[\'"]', input_tag)
        
        if name_match and value_match:
            hidden_inputs[name_match.group(1)] = value_match.group(1)
    
    sock = create_socket_connection(host, port, is_https)
    
    login_data = {
        'log': username,
        'pwd': password,
        'wp-submit': 'Log In',
        'redirect_to': f"{'https' if is_https else 'http'}://{host}/wp-admin/",
        'testcookie': '1'
    }
    
    login_data.update(hidden_inputs)
    
    post_data = urllib.parse.urlencode(login_data)
    
    request = f"POST {login_path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    request += "Accept: text/html,application/xhtml+xml,application/xml\r\n"
    if initial_cookies:
        request += f"Cookie: {'; '.join(initial_cookies)}\r\n"
    request += "Content-Type: application/x-www-form-urlencoded\r\n"
    request += f"Content-Length: {len(post_data)}\r\n"
    request += "Connection: close\r\n\r\n"
    request += post_data
    
    sock.sendall(request.encode())
    response = receive_response(sock)
    sock.close()
    
    headers, _ = parse_headers_and_body(response)
    
    cookies = []
    for key, value in headers.items():
        if key.lower() == 'set-cookie':
            cookie_parts = value.split(';')[0]
            cookies.append(cookie_parts)
    
    return '; '.join(cookies)

def get_upload_nonce(host, port, cookies, is_https):
    sock = create_socket_connection(host, port, is_https)
    
    request = f"GET /wp-admin/media-new.php HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    request += f"Cookie: {cookies}\r\n"
    request += "Connection: close\r\n\r\n"
    
    sock.sendall(request.encode())
    response = receive_response(sock)
    sock.close()
    
    _, body = parse_headers_and_body(response)
    body_text = body.decode('utf-8', errors='ignore')
    
    nonce_match = re.search(r'_wpnonce":"([^"]+)"', body_text)
    if nonce_match:
        return nonce_match.group(1)
    return None

def main():
    parser = argparse.ArgumentParser(description='Upload a file to WordPress Media Library')
    parser.add_argument('--url', required=True, help='WordPress site URL')
    parser.add_argument('--user', required=True, help='Username')
    parser.add_argument('--password', required=True, help='Password')
    parser.add_argument('--local-file', required=True, help='Path to local file to upload')
    args = parser.parse_args()
    
    url = args.url
    username = args.user
    password = args.password
    local_file = args.local_file
    
    if not os.path.exists(local_file):
        print(f"Local file {local_file} does not exist")
        return
    
    protocol, host, port, _ = parse_url(url)
    is_https = protocol == 'https'
    
    cookies = get_wordpress_cookies(host, port, username, password, is_https)
    
    if not cookies or 'wordpress_logged_in' not in cookies:
        print("Upload failed. Login unsuccessful.")
        return
    
    nonce = get_upload_nonce(host, port, cookies, is_https)
    if not nonce:
        print("Upload failed. Could not get upload nonce.")
        return
    
    sock = create_socket_connection(host, port, is_https)
    
    filename = os.path.basename(local_file)
    
    with open(local_file, 'rb') as f:
        file_content = f.read()
    
    boundary = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))
    
    multipart_data = []
    
    multipart_data.append(f'--{boundary}'.encode())
    multipart_data.append(f'Content-Disposition: form-data; name="async-upload"; filename="{filename}"'.encode())
    
    content_type = "application/octet-stream"
    if filename.lower().endswith(('.jpg', '.jpeg')):
        content_type = "image/jpeg"
    elif filename.lower().endswith('.png'):
        content_type = "image/png"
    elif filename.lower().endswith('.gif'):
        content_type = "image/gif"
    
    multipart_data.append(f'Content-Type: {content_type}'.encode())
    multipart_data.append(b'')
    multipart_data.append(file_content)
    
    multipart_data.append(f'--{boundary}'.encode())
    multipart_data.append(b'Content-Disposition: form-data; name="_wpnonce"')
    multipart_data.append(b'')
    multipart_data.append(nonce.encode())
    
    multipart_data.append(f'--{boundary}'.encode())
    multipart_data.append(b'Content-Disposition: form-data; name="action"')
    multipart_data.append(b'')
    multipart_data.append(b'upload-attachment')
    
    multipart_data.append(f'--{boundary}--'.encode())
    
    body = b'\r\n'.join(multipart_data)
    
    request = f"POST /wp-admin/async-upload.php HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    request += f"Cookie: {cookies}\r\n"
    request += f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
    request += f"Content-Length: {len(body)}\r\n"
    request += "Connection: close\r\n\r\n"
    
    sock.sendall(request.encode() + body)
    
    response = receive_response(sock)
    sock.close()
    
    headers, body = parse_headers_and_body(response)
    
    try:
        body_str = body.decode('utf-8', errors='ignore')
        
        json_data = json.loads(body_str)
        if 'data' in json_data and 'url' in json_data['data']:
            file_url = json_data['data']['url']
            print(f"Upload success. File upload url: {file_url}")
        else:
            url_match = re.search(r'"url":"([^"]+)"', body_str)
            if url_match:
                file_url = url_match.group(1).replace('\\/', '/')
                print(f"Upload success. File upload url: {file_url}")
            else:
                print("Upload failed. Could not find file URL in response.")
    except Exception as e:
        print(f"Upload failed. Error parsing response: {e}")

if __name__ == "__main__":
    main()