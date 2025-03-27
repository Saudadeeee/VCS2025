#!/usr/bin/env python3
import argparse
from http_utils import parse_url, create_socket_connection, receive_response, extract_title

def main():
    parser = argparse.ArgumentParser(description='HTTP GET client to fetch a webpage and display its title')
    parser.add_argument('--url', required=True, help='URL to fetch')
    args = parser.parse_args()
    
    url = args.url
    protocol, host, port, path = parse_url(url)
    
    is_https = protocol == 'https'
    sock = create_socket_connection(host, port, is_https)
    
    request = f"GET {path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    request += "Accept: text/html,application/xhtml+xml,application/xml\r\n"
    request += "Connection: close\r\n\r\n"
    
    sock.sendall(request.encode())
    
    response = receive_response(sock)
    sock.close()
    
    header_end = response.find(b'\r\n\r\n')
    if header_end != -1:
        body = response[header_end + 4:]
        
        title = extract_title(body)
        if title:
            print(f"Title: {title}")
        else:
            print("No title found in the page")
    else:
        print("Invalid HTTP response")

if __name__ == "__main__":
    main()