from socket import *
import os
import time
from os import path
import threading
from email.utils import parsedate_to_datetime 
import re
from urllib.parse import unquote

serverName = 'localhost'
mtime ={}
serverPort = 12000
mtimeStr = ""

#Function to parse the incoming request and extract the filename
def parse_request(request):
    modRequest = request.splitlines()
    if not modRequest or len(modRequest) < 1:
        return None, None, None 

    requestLine = modRequest[0].split()
    if len(requestLine) < 2:
        return None, None, None 

    method = requestLine[0]
    #Extract the requested file and decode any URL encoding
    url = unquote(requestLine[1]) 

    if url.startswith("http://") or url.startswith("https://"):
        urlParts = url.split('/', 3)
        if len(urlParts) > 3:
            requestedFile = urlParts[-2]  
        else:
            requestedFile = ''  
    else:
        requestedFile = url.lstrip('/')  

    #Parse headers for If-Modified-Since
    headers = {line.split(": ")[0]: line.split(": ")[1] for line in modRequest[1:] if ": " in line}

    #Check for empty Host header
    if 'Host' not in headers or not headers['Host']:
        return None, None, None  

    return requestedFile, method, headers.get('If-Modified-Since')

#Function to generate an HTTP response based on the status code
def generate_response(statusCode):
    responses = {
        200: "HTTP/1.1 200 OK\r\n\r\n",
        304: "HTTP/1.1 304 Not Modified\r\n\r\n",
        400: "HTTP/1.1 400 Bad Request\r\n\r\n",
        404: "HTTP/1.1 404 Not Found\r\n\r\n",
        501: "HTTP/1.1 501 Not Implemented\r\n\r\n"
    }

    response = responses.get(statusCode)
    return response

#Function to check if file is valid 
def is_valid_filename(filename):
    #Regex to match invalid characters in the filename
    #This example disallows: ^ < > | ? * & and any non-printable characters
    if re.search(r'[<>|?*^&]', filename) or any(c.isspace() for c in filename):
        return False
    return True


# Function to handle incoming client connections
def handle_connection(clientSocket):
    global last_mtime, mtime_str
    try:
        #Receive request 
        request = clientSocket.recv(1024).decode()

        #If request does not exist, return error 400 Bad Request
        if not request.strip():
            response = generate_response(400)
            clientSocket.sendall(response.encode())
            send_file(clientSocket, '400.html')
            clientSocket.close()
            return
        
        #Obtain file data 
        filename, method, modSince = parse_request(request)
        print(f"Requested filename: {filename}")

        #If filename or method is None, return error 400 Bad Request
        if filename is None or method is None:
            response = generate_response(400)
            clientSocket.sendall(response.encode())
            send_file(clientSocket, '400.html')
            clientSocket.close()
            return

        #Check for invalid characters in the filename, return error 400 Bad Request
        if not is_valid_filename(filename):
            response = generate_response(400)
            clientSocket.sendall(response.encode())
            send_file(clientSocket, '400.html')
            clientSocket.close()
            return

        #If method is not GET, then return error 501 Not Implemented 
        #Note: we have not implemented other funcs such as POST
        if method != 'GET':
            response = generate_response(501) 
            clientSocket.sendall(response.encode())
            clientSocket.close()
            return
            
        #if Valid file 
        if path.exists(filename):
            #Get current time and format it 
            currentMTime = os.path.getmtime(filename) 
            mtimeStr = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(currentMTime))
            
            #if modification date exists 
            if modSince:
                #Format date and compare to current file time 
                #If modified time is >= than current time, return error 304 Not Modified
                modSinceFormat = parsedate_to_datetime(modSince).timestamp()
                if modSinceFormat >= currentMTime:
                    response = generate_response(304)
                    print(f"Response being sent: {response}")
                    clientSocket.close()
                    return

            #if file in array and current time is equal to the stored time, return error 304 Not Modified 
            if filename in mtime and currentMTime == mtime[filename]:
                if currentMTime == mtime[filename]:
                    response = generate_response(304)
                    print(f"Response being sent: {response}")
                    clientSocket.sendall(response.encode())
                    send_file(clientSocket, '304.html')
                    clientSocket.close()
                    return
            
            #Store current file modification time and generate a 200 OK response 
            #Add date to response 
            mtime[filename]= currentMTime
            response = generate_response(200)
            response += f"Last-Modified: {mtimeStr}\r\n\r\n"
            clientSocket.sendall(response.encode())
            send_file(clientSocket, filename)  

        #If not valid file, return error 404 Not Found 
        else:
            response = generate_response(404)
            clientSocket.sendall(response.encode())
            send_file(clientSocket, '404.html')
    
    #If attempt fails at any point, return error 400 Bad Request 
    except Exception as e:
        print(f"Error handling connection: {e}")
        response = generate_response(400)  
        clientSocket.sendall(response.encode())
        send_file(clientSocket, '400.html')

    #Close connection 
    finally:
        clientSocket.close()



#Function to send a file over the connection
def send_file(clientSocket, filename):
    #Open the file in binary mode, read the content and send file. 
    #If error return simple error message 
    try:
        with open(filename, 'rb') as file:
            content_data = file.read()

            if content_data == b"":
                print("File is empty.")
                return

            clientSocket.send(content_data)
    except Exception as e:
        print(f"Error sending file: {e}")


#Create TCP welcoming socket
serverSocket = socket(AF_INET,SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

#Bind the server port to the socket
serverSocket.bind((serverName,serverPort))

#Server begins listening for incoming TCP connections
serverSocket.listen(5)
print ('The server is ready to receive')

#loop to continuously respond to requests 
while True: 
    #Attempt connection and threading
    try:
        connectionSocket, addr = serverSocket.accept()
        print("Connection from:", addr)
        if connectionSocket:
            threading.Thread(target=handle_connection, args=(connectionSocket,)).start()
    except KeyboardInterrupt:
        print('Server shutting down...')
        break
    except Exception as e:
        print(f"Error: {e}")

