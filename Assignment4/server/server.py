import socket
import os
import datetime
import signal
import sys

# Constant for our buffer size

BUFFER_SIZE = 1024

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
        message = message+ value+' Not Modified\r\n'+date_string+'\r\n'
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
    print(header)
    sock.send(header.encode())

    # Open the file, read it, and send it

    with open(file_name, 'rb') as file_to_send:
        while True:
            chunk = file_to_send.read(BUFFER_SIZE)
            if chunk:
                sock.send(chunk)
            else:
                break

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

# Our main function.

def main():

    # Register our signal handler for shutting down.

    signal.signal(signal.SIGINT, signal_handler)

    # Create the socket.  We will ask this to work on any interface and to pick
    # a free port at random.  We'll print this out for clients to use.

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', 0))
    print('Will wait for client connections at port ' + str(server_socket.getsockname()[1]))
    server_socket.listen(1)
    
    # Keep the server running forever.
    
    while(1):
        print('Waiting for incoming client connection ...')
        conn, addr = server_socket.accept()
        print('Accepted connection from client address:', addr)
        print('Connection to client established, waiting to receive message...')

        # We obtain our request from the socket.  We look at the request and
        # figure out what to do based on the contents of things.

        request = get_line_from_socket(conn)
        print('Received request:  ' + request)
        info = get_line_from_socket(conn)

        host = info.split(' ')[1].split(':')[0]
        port = info.split(' ')[1].split(':')[1]

        request_list = request.split()
        
        # This server doesn't care about headers, so we just clean them up.

        header = get_line_from_socket(conn)
        check_if_newer = False        
        while header!= '':
            print(header)
            response_list = header.split(' ')
            print(response_list)
            if response_list[0]=='If-modified-since:':
                date=(response_list[3])
                month=datetime.datetime.strptime(response_list[4], '%b').month
                year=response_list[5]
                time = response_list[6].split(":")
                hour=time[0]
                minute = time[1]
                second = time[2]
                modified_time = datetime.datetime(int(year), int(month), int(date), int(hour), int(minute), int(second))
                check_if_newer = True
                print(modified_time)
                break
            print("+++")
            pass

        # If we did not get a GET command respond with a 501.

        if request_list[0] != 'GET':
            print('Invalid type of request received ... responding with error!')
            send_response_to_client(conn, '501', '501.html')

        # If we did not get the proper HTTP version respond with a 505.

        elif request_list[2] != 'HTTP/1.1':
            print('Invalid HTTP version received ... responding with error!')
            send_response_to_client(conn, '505', '505.html')

        # We have the right request and version, so check if file exists.
                  
        else:

            # If requested file begins with a / we strip it off.

            req_file = request_list[1]
            while (req_file[0] == '/'):
                req_file = req_file[1:]
            print(req_file)

            # Check if requested file exists and report a 404 if not.

            if (not os.path.exists(req_file)):
                print('Requested file does not exist ... responding with error!')
                send_response_to_client(conn, '404', '404.html')

            # file exists

            else:

                # if a conditional GET was made from cache, check which copy is newer
                # if one in cache is newer, send back 304 error 
                # if one in server is newer, send back the newer copy to cache

                if check_if_newer:

                    m_time = datetime.datetime.fromtimestamp(os.path.getmtime(req_file))
                    
                    if m_time<modified_time:
                        print("file in cache is newer...")
                        send_response_to_client(conn, '304', '304.html')
                    else:
                        print("file in server is newer...")

                        print('Requested file good to go!  Sending file ...')
                        send_response_to_client(conn, '200', req_file)
                else:
                    print('Requested file good to go!  Sending file ...')
                    send_response_to_client(conn, '200', req_file)

        # We are all done with this cache, so close the connection and
        # Go back to get another one!

        conn.close()
    

if __name__ == '__main__':
    main()

