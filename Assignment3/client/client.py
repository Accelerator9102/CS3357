import socket
import os
import sys
import argparse
from urllib.parse import urlparse

# Define a constant for our buffer size

BUFFER_SIZE = 1024

# A function for creating HTTP GET messages.

def prepare_get_message(host, port, file_name):
    request = f'GET {file_name} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n' 
    return request


# Read a single line (ending with \n) from a socket and return it.
# We will strip out the \r and the \n in the process.

def get_line_from_socket(sock):

    done = False
    line = ''
    while (not done):
        char = sock.recv(1).decode()
        if (char == '\r'):
            pass
        elif (char == '\n'):
            done = True
        else:
            line = line + char
    return line

# Read a file from the socket and print it out.  (For errors primarily.)

def print_file_from_socket(sock, bytes_to_read):

    bytes_read = 0
    while (bytes_read < bytes_to_read):
        chunk = sock.recv(BUFFER_SIZE)
        bytes_read += len(chunk)
        print(chunk.decode())

# Read a file from the socket and save it out.

def save_file_from_socket(sock, bytes_to_read, file_name):

    with open(file_name, 'wb') as file_to_write:
        bytes_read = 0
        while (bytes_read < bytes_to_read):
            chunk = sock.recv(BUFFER_SIZE)
            bytes_read += len(chunk)
            file_to_write.write(chunk)


# Our main function.

def main():

    # Check command line arguments to retrieve a URL.

    parser = argparse.ArgumentParser()
    print(parser)
    parser.add_argument("url", help="URL to fetch with an HTTP GET request")

    # Add the optional argument called -proxy

    parser.add_argument("-proxy", help="Proxy to fetch with a cache")
    print(parser)
    args = parser.parse_args()
    print(args)

    # Check the URL passed in and make sure it's valid. And then check if the optional argument -proxy is used or not. 
    # If used, parse the argument and save cache host and port for later
    # If not used, keep track of server host and port for later.
    
    try:

        proxy_flag=False
        parsed_url = urlparse(args.url)
        print(args.proxy)

        if ((parsed_url.scheme != 'http') or (parsed_url.port == None) or (parsed_url.path == '') or (parsed_url.path == '/') or (parsed_url.hostname == None)):
            raise ValueError
        host = parsed_url.hostname
        port = parsed_url.port
        file_name = parsed_url.path

        if args.proxy is not None:
            parsed_proxy = args.proxy.split(':')
            if len(parsed_proxy)!=2:
                print('Error: Invalid Cache Info. Enter a cache of the form: host:port\nWill be connecting to server directly...')
            else:
                proxy_host = parsed_proxy[0]
                print(proxy_host)
                proxy_port = int(parsed_proxy[1])
                print(proxy_port)
                proxy_flag = True

    except ValueError:
        print('Error:  Invalid URL.  Enter a URL of the form:  http://host:port/file')
        sys.exit(1)

    # Optional argument is prompted. Now we try to make a connection to the cache.

    if proxy_flag:
        print('Connecting to Cache ...')
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((proxy_host,proxy_port))
        except ConnectionRefusedError:
            print('Error:  That host or port of cache is not accepting connections.')
            sys.exit(1)
     

    # Optional argument is not prompted. Now we try to make a connection to the server.

    else:
        print('Connecting to server ...')
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
        except ConnectionRefusedError:
            print('Error:  That host or port is not accepting connections.')
            sys.exit(1)

        # Either of the connections was successful, so we can prep and send our message.
    
    print('Connection to server/cache established. Sending message...\n')
    message = prepare_get_message(host, port, file_name)
    
    client_socket.send(message.encode())
    
    # Receive the response from the server and start taking a look at it

    response_line = get_line_from_socket(client_socket)
    response_list = response_line.split(' ')
    headers_done = False
        
    # If an error is returned from the server, we dump everything sent and
    # exit right away.  
    
    if response_list[1] != '200':
        print('Error:  An error response was received from the server.  Details:\n')
        print(response_line)
        bytes_to_read = 0
        while (not headers_done):
            header_line = get_line_from_socket(client_socket)
            print(header_line)
            header_list = header_line.split(' ')
            if (header_line == ''):
                headers_done = True
            elif (header_list[0] == 'Content-Length:'):
                bytes_to_read = int(header_list[1])
        print_file_from_socket(client_socket, bytes_to_read)
        sys.exit(1)
           
    
    # If it's OK, we retrieve and write the file out.

    else:

        print('Success:  Server is sending file.  Downloading it now.')

        # If multiple directories are in the file name, we split it by / and get the last element, which is the file name. 

        while (file_name[0] == '/'):
            file_name = file_name.split('/')[-1]
        
        # Go through headers and find the size of the file, then save it.
   
        bytes_to_read = 0
        while (not headers_done):
            header_line = get_line_from_socket(client_socket)
            header_list = header_line.split(' ')
            if (header_line == ''):
                headers_done = True
            elif (header_list[0] == 'Content-Length:'):
                bytes_to_read = int(header_list[1])
        save_file_from_socket(client_socket, bytes_to_read, file_name)

if __name__ == '__main__':
    main()
