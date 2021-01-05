import socket
import os
import datetime
import signal
import sys

EXPIRE_TIME = 120
BUFFER_SIZE = 1024

# Read a file from the socket and print it out.  (For errors primarily.)

def print_file_from_socket(sock, bytes_to_read):

    bytes_read = 0
    while (bytes_read < bytes_to_read):
        chunk = sock.recv(BUFFER_SIZE)
        bytes_read += len(chunk)
        print(chunk.decode())
        return chunk.decode()

# Signal handler for graceful exiting.

def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    sys.exit(0)

# Create an HTTP response

def prepare_response_message(value):
    date = datetime.datetime.now()
    date_string = 'Date: ' + date.strftime('%a, %d %b %Y %H:%M:%S EDT')
    message = 'HTTP/1.1 '
    if value == '200':
        message = message + value + ' OK\r\n' + date_string + '\r\n'
    elif value == '404':
        message = message + value + ' Not Found\r\n' + date_string + '\r\n'
    elif value == '501':
        message = message + value + ' Method Not Implemented\r\n' + date_string + '\r\n'
    elif value == '505':
        message = message + value + ' Version Not Supported\r\n' + date_string + '\r\n'
    elif value == '304':
        message = message + value + ' Not Modified\r\n'+date_string+'\r\n'
    return message

# Send the given response and file back to the client.

def send_response_to_client(sock, code, file_name):

    # Determine content type of file

    if ((file_name.endswith('.jpg')) or (file_name.endswith('.jpeg'))):
        type = 'image/jpeg'
    elif (file_name.endswith('.gif')):
        type = 'image/gif'
    elif (file_name.endswith('.png')):
        type = 'image/jpegpng'
    elif ((file_name.endswith('.html')) or (file_name.endswith('.htm'))):
        type = 'text/html'
    else:
        type = 'application/octet-stream'
    
    # Get size of file

    file_size = os.path.getsize(file_name)

    # Construct header and send it

    header = prepare_response_message(code) + 'Content-Type: ' + type + '\r\nContent-Length: ' + str(file_size) + '\r\n\r\n'
    sock.send(header.encode())

    # Open the file, read it, and send it

    with open(file_name, 'rb') as file_to_send:
        while True:
            chunk = file_to_send.read(BUFFER_SIZE)
            if chunk:
                sock.send(chunk)
            else:
                break

# A function for creating HTTP GET messages.

def prepare_get_message(host, port, file_name, time=''):
    if time!='':
        request = f'GET {file_name} HTTP/1.1\r\nHost: {host}:{port}\r\nIf-modified-since: {time}\r\n' 
        return request
    else:
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

# Get the file recieved from server, check if the file is sent or an error occured.
# If an error occured, add each line up to form an error http header and return the size of the error html message and the header
# If file received successully, simply return the size of file and empty string since the header doesn't matter in this case. 

def process_file_recieved(code, line, sock, header_done):
    bytes_to_read=0
    if code != '200':
        print('Error:  An error response was received from the server.  Details:\n')
        message = line+'\r\n'
        while (not header_done):
            
            header_line = get_line_from_socket(sock)
            message+=header_line+'\r\n'
            header_list = header_line.split(' ')
            if (header_line == ''):
                header_done = True
                message+='\r\n'
            elif (header_list[0] == 'Content-Length:'):
                bytes_to_read = int(header_list[1])
        return [bytes_to_read, message]
    else:
        print('Success:  Server is sending file.  Downloading it now.')
        while (not header_done):
            header_line = get_line_from_socket(sock)
            header_list = header_line.split(' ')
            if (header_line == ''):
                header_done = True
            elif (header_list[0] == 'Content-Length:'):
                bytes_to_read = int(header_list[1])
    print(bytes_to_read)
    return [bytes_to_read,'']

# Read a file from the socket and save it out.

def save_file_from_socket(sock, bytes_to_read, file_name):
    with open(file_name, 'wb') as file_to_write:
        bytes_read = 0
        while (bytes_read < bytes_to_read):
            chunk = sock.recv(BUFFER_SIZE)
            bytes_read += len(chunk)
            file_to_write.write(chunk)

# main function

def main():

     # Register our signal handler for shutting down.
    
    signal.signal(signal.SIGINT, signal_handler)

    # Create the socket.  We will ask this to work on any interface and to pick
    # a free port at random.  We'll print this out for clients to use.

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', 0))
    print('Will wait for client connections at port ' + str(server_socket.getsockname()[1]))
    server_socket.listen(1)

    # Keep the server running forever

    while(1):
        print('Waiting for incoming client connection ...')
        conn, addr = server_socket.accept()
        print('Accepted connection from client address:', addr)
        print('Connection to client established, waiting to receive message...')

        # We obtain our request from the socket.  We look at the request and
        # figure out what to do based on the contents of things.

        request = get_line_from_socket(conn)
        print('Received request:  ' + request)

        # We obtain the second line in message which contains the host and port info of the server

        info = get_line_from_socket(conn)
        host = info.split(' ')[1].split(':')[0]
        port = int(info.split(' ')[1].split(':')[1])
        
        # Now try to make connection to server

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            
        except ConnectionRefusedError:
            print('Error:  That host or port is not accepting connections.')
            sys.exit(1)

        request_list = request.split()

        

        # check if the message is a GET message
        if request_list[0]=='GET':

            # get the file path

            req_file = request_list[1]
            while (req_file[0] == '/'):

                # create a path with the host and port name

                file_path = host+'_'+str(port)+req_file

                # get only the file name

                req_file = req_file.split('/')[-1]

            # get the path without the file name

            list_dir = file_path.split('/')
            dir_path = ''
            counter =0
            while counter<len(list_dir)-1:
                dir_path = dir_path+list_dir[counter]  +'/'  
                counter+=1
            
            dir_path = dir_path.rstrip('/')
            
            # check if dir exists, if not, create it
            if not os.path.isdir(dir_path):
                os.makedirs(dir_path)

            

            # file does not exist, prepare message and send it to server

            if not os.path.exists(file_path):
                print("no file")
                
                message = prepare_get_message(host, port, req_file)
                client_socket.send(message.encode())
                
                # get response from server

                response_line = get_line_from_socket(client_socket)
                response_list = response_line.split(' ')
                headers_done = False

                # process received message

                list_of_message = process_file_recieved(response_list[1], response_line, client_socket, headers_done)

                # if file not received successfully, simple send error header and error html content

                if response_list[1]!='200':
                    print('Error:  An error response was received from the server.  Details:\n')
                    print(response_line)
                    
                    http_header = print_file_from_socket(client_socket, list_of_message[0])
                    print("ERROR MESSAGE!!!!!!!!!")
                    conn.send(list_of_message[1].encode())
                    conn.send(http_header.encode())
                    
                # file received successfully, save file locally and send response to client.

                else: 
                    print('Success:  Server is sending file.  Downloading it now.')

                    # Go through headers and find the size of the file, then save it.
            
                    save_file_from_socket(client_socket, list_of_message[0], file_path)
                    send_response_to_client(conn, '200',file_path)

            # file exists

            else:    

                # get current time and modification time of local file

                current_time = datetime.datetime.now()
                m_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                time_difference=current_time-m_time
                print('file exists')
                
                # check if the file is expired or not, if not, call a conditional GET

                if time_difference.total_seconds()<EXPIRE_TIME:
                    
                    mtime_string = 'Date: ' + m_time.strftime('%a, %d %b %Y %H:%M:%S EDT')
                    message = prepare_get_message(host, port, req_file, mtime_string)
                    client_socket.send(message.encode())
                    response_line = get_line_from_socket(client_socket)
                    response_list = response_line.split(' ')

                    # file in server is older, file in cache is newer and sent to client

                    if response_list[1] == '304':
                        list_of_message = process_file_recieved(response_list[1], response_line, client_socket, headers_done)
                        print(list_of_message[1])
                        http_header = print_file_from_socket(client_socket, list_of_message[0])
                        print("ERROR MESSAGE!!!!!!!!!")
                        send_response_to_client(conn, '200', file_path)

                    # file in server is newer, remove local file and retrieve a new copy from server

                    else:
                        os.remove(file_path)
                        print("newer file founded...")
                        
                        
                        print("new file downloading...")
                        
                        print("+++")
                        
                        headers_done = False

                        list_of_message = process_file_recieved(response_list[1], response_line, client_socket, headers_done)

                        # if file in server is deleted

                        if response_list[1]!='200':

                            http_header = print_file_from_socket(client_socket, list_of_message[0])
                            print("ERROR MESSAGE!!!!!!!!!")
                            conn.send(list_of_message[1].encode())
                            conn.send(http_header.encode())
                        
                        # file retrieved successfully, save locally and send back to client

                        else:
                            print('Success:  Server is sending file.  Downloading it now.')
                            save_file_from_socket(client_socket, list_of_message[0], file_path)
                            send_response_to_client(conn, '200', file_path)


                        
                    
                    

                # file expired, remove stored file and retrieve new one from server

                else:
                    os.remove(file_path)
                    print("expired file deleted...")
                    message = prepare_get_message(host, port, req_file)

                    
                    client_socket.send(message.encode())
                    print("new file downloading...")
                    response_line = get_line_from_socket(client_socket)
                    print("+++")
                    response_list = response_line.split(' ')
                    headers_done = False
                    
                    list_of_message = process_file_recieved(response_list[1], response_line, client_socket, headers_done)

                    # file in server is deleted

                    if response_list[1]!='200':

                        http_header = print_file_from_socket(client_socket, list_of_message[0])
                        print("ERROR MESSAGE!!!!!!!!!")
                        conn.send(list_of_message[1].encode())
                        conn.send(http_header.encode())
                    
                    # file retrieved successfully

                    else:
                        save_file_from_socket(client_socket, list_of_message[0], file_path)
                        send_response_to_client(conn, '200', file_path)

                    

                    
            
                   
                    
        
if __name__ == '__main__':
    main()
        



