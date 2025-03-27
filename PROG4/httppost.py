#!/usr/bin/env python3
import re
import argparse
import urllib.parse
from http_utils import parse_url, create_socket_connection, receive_response, parse_headers_and_body

def main():
    parser = argparse.ArgumentParser(description='HTTP POST client to login to WordPress')
    parser.add_argument('--url', required=True, help='WordPress site URL')
    parser.add_argument('--user', required=True, help='Username')
    parser.add_argument('--password', required=True, help='Password')
    args = parser.parse_args()
    
    url = args.url
    username = args.user
    password = args.password
    
    protocol, host, port, path = parse_url(url)
    
    is_https = protocol == 'https'
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
    
    body = response.split(b'\r\n\r\n', 1)[1] if b'\r\n\r\n' in response else b''
    
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
        'redirect_to': f"{protocol}://{host}/wp-admin/",
        'testcookie': '1'
    }
    
    login_data.update(hidden_inputs)
    
    post_data = urllib.parse.urlencode(login_data)
    
    request = f"POST {login_path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    request += "Accept: text/html,application/xhtml+xml,application/xml\r\n"
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
            cookies.append(value)
    
    login_success = any('wordpress_logged_in' in cookie for cookie in cookies)
    
    if login_success:
        print(f"User {username} đăng nhập thành công")
    else:
        print(f"User {username} đăng nhập thất bại")

if __name__ == "__main__":
    main()