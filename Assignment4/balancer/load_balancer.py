import socket
import sys
import datetime
import signal
from random import randint

BUFFER_SIZE = 1024
TIME_OUT = 300

# Signal handler for graceful exiting.

def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    sys.exit(0)

# A function for creating HTTP GET messages.

def prepare_get_message(host, port, file_name):
    request = f'GET {file_name} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n' 
    return request

# Create an HTTP response

def prepare_response_message():
    message = 'HTTP/1.1 ' + str(301) + ' Moved Permanently'+'\r\n'

    return message

# Send the given response and file back to the client.

def send_response_to_client(sock, server_info, file_name):

    # Construct header and send it

    header = prepare_response_message() + 'Location: http://' + server_info + '/'+ file_name +'\r\n\r\n'
    sock.send(header.encode())

    # Open the file, read it, and send it
    with open('301.html', 'rb') as file_to_send:
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

# Read a file from the socket and print it out.  (For 301 html)

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

# function used to test if a given server is available
# return the response time if yes, return false otherwise

def test_server(host, port):

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host,port))
    except ConnectionRefusedError:
        print('Error:  That host or port of server is not accepting connections.')
        return False    

    # connect success, keep record of time
    # testing transfer with test.jpg

    print('Connection to server established. Sending message...\n')
    message = prepare_get_message(host, port, 'test.jpg')
    start_time = datetime.datetime.now()
    client_socket.send(message.encode())

    response_line = get_line_from_socket(client_socket)
    response_list = response_line.split(' ')
    headers_done = False

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
        return False
    
    # test file being transfered successfully
    else:

        print('Success:  Server is sending test file.  Downloading it now.')
        
        # Go through headers and find the size of the file, then save it.
   
        bytes_to_read = 0
        while (not headers_done):
            header_line = get_line_from_socket(client_socket)
            header_list = header_line.split(' ')
            if (header_line == ''):
                headers_done = True
            elif (header_list[0] == 'Content-Length:'):
                bytes_to_read = int(header_list[1])
        save_file_from_socket(client_socket, bytes_to_read, 'test.jpg')

    # subtract starting time from ending time to get response time
    #     
    end_time = datetime.datetime.now()
    response_time = end_time-start_time
    response_time = response_time.total_seconds()
    print(response_time)
    return response_time

# return the sum of 1+2+..+n

def sum_from_1_to_n(n):
    return sum(range(n+1))

# map the servers with different ratios based on their performance

def map_server_performance_ratio(total, num_server, sorted_list):
    random_range={}
    counter = total
    l_num = []
    difference = total - num_server
    num = num_server
    index = 0

    # iterate the loop from the sum of 1 to the number of total servers to 1
    # for example, if there are 3 servers avaible, total will be 6, and the loop will iterate 6 times
    # and each server will be matched with different amount of numbers from 1 to 6 based on their performance

    while counter>0:
        if counter>difference:
            l_num.append(counter)
            counter-=1
        elif counter == difference:
            list_copy=l_num.copy()
            random_range[sorted_list[index]] = list_copy
            index+=1
            l_num.clear()
            num-=1
            difference = difference-num
             
            if counter ==1:
                random_range[sorted_list[-1]] = [1]
                break
            l_num.append(counter)
            counter-=1
  
    return random_range

# Our main function

def main():

    # keep running the web balancer as a server forever

    while True:

        # read from the configuration file and store all servers details in list
        list_servers = []

        with open("configuration.txt", "r") as f:
            line = f.readline()
            line = line.strip("\n")
            list_servers.append(line)
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip("\n")
                list_servers.append(line)

        print(list_servers)
        number_of_server = len(list_servers)
        list_rtime = {}
        list_error=[]

        # for each server, do a test and build a dictionary with the server detail and its response time

        for el in list_servers:
            host = el.split(":")[0]
            port = int(el.split(":")[1])
            rtime=test_server(host, port)
            if not rtime:
                list_error.append(el)
                number_of_server-=1
            else:
                list_rtime[el]=rtime
        
        # keep track of servers which are unavailable
        # print out the them

        if_error = ""
        for el in list_error:
            if_error = if_error+el+' '

        if if_error != "":
            print("The following servers are unavailable right now...\n"+if_error)

        # sort the dictionary based on the response time, from fastest to slowest

        list_rtime = {key: value for key, value in sorted(list_rtime.items(), key=lambda item: item[1])}

        # keep track of sorted server details separately from the time

        sorted_list = []
        for key in list_rtime:
            sorted_list.append(key)


        # get range of numbers can be selected from

        total_random_num = sum_from_1_to_n(number_of_server)

        # map each server to a specific range of number
        # details explained in comments of map_server_performance_ratio function

        performance_ratio = map_server_performance_ratio(total_random_num, number_of_server, sorted_list)



        # Register our signal handler for shutting down.

        signal.signal(signal.SIGINT, signal_handler)

        # Create the socket.  We will ask this to work on any interface and to pick
        # a free port at random.  We'll print this out for clients to use.

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('', 0))
        print('Will wait for client connections at port ' + str(server_socket.getsockname()[1]))
        server_socket.listen(1)
        server_socket.settimeout(TIME_OUT)

        # Keep the server running forever.
        
        while(1):
            print('Waiting for incoming client connection ...')
            
            # check if the connect is timed out or not
            # if timed out, the program will run the server tests again
            # then start a new connection as a server

            try:
                conn, addr = server_socket.accept()
                print('Accepted connection from client address:', addr)
                print('Connection to client established, waiting to receive message...')
            except:
                break

            # We obtain our request from the socket.  We look at the request and
            # figure out what to do based on the contents of things.
            # pick a random number from the range mentioned above and get its corresponding server

            url=''
            request = get_line_from_socket(conn)
            print('Received request:  ' + request)
            ran_num = randint(1, total_random_num)
            for key in performance_ratio:
                if ran_num in performance_ratio[key]:
                    url = key
            
            request_list = request.split()

            # This server doesn't care about headers, so we just clean them up.

            while (get_line_from_socket(conn) != ''):
                pass

            # If requested file begins with a / we strip it off.

            req_file = request_list[1]
            while (req_file[0] == '/'):
                req_file = req_file[1:]

            
            print('Server found, sending redirecting details...')
            send_response_to_client(conn, url, req_file)
                
            # We are all done with this client, so close the connection and
            # Go back to get another one!

            conn.close();
            



if __name__ == '__main__':
    main()