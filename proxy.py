import socket

#Host and port for the proxy server
PROXY_HOST = "localhost"
PROXY_PORT = 8080

#Web server host and port
WEB_SERVER_HOST = 'localhost'
WEB_SERVER_PORT = 12000

# Create proxy server socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((PROXY_HOST, PROXY_PORT))
server.listen(1)
print('Proxy server listening on port %s ...' % PROXY_PORT)

# Function to forward the request to the destination web server
def forward_request(request, client_connection):
    print("Forwarding request to web server for processing")
    print(f"Request sent to web server: {request}")

    # Create a socket to communicate with the destination web server
    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    #format request and get method, pth, and host 
    requestForm= request.split("\r\n")[0]
    print("Request Exists and Formatted: {}\n".format(requestForm))
    method = requestForm.split()[0]
    path = requestForm.split()[1]
    host = path.split("/")[2]

    #If method is not get, return 501 Not Implemented     
    if (method != 'GET'):
        error501 = "HTTP/1.1 501 Not Implemented\r\n"
        client_connection.sendall(error501.encode())
        return
    
    #If test.html file detected, internal request 
    if host.strip() == 'test.html'  :
        print("Detected internal request")
        
        #Connect to socket 
        webSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Connect to the web server
            webSocket.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))
            webSocket.sendall(request.encode('utf-8'))

            # Receive the response from the web server
            response = b""
            while True:
                part = webSocket.recv(1024)
                if not part: 
                    break
                response += part

        #close websocket and return the response 
        finally:
            webSocket.close()
        return response

    #Else if external server request 
    else:
        #Remove initial / as it messes with path 
        if path.startswith('/http'):
            path = path[1:]\
            
        #Attempt to make connection and return page 
        try:
            #Obtain target IP and attempt connection 
            targetIp = socket.gethostbyname(host)
            proxy.connect((targetIp, 80))
            print("Target IP resolved: {}".format(targetIp))
            print("Connected to target server at {} ({})".format(host, targetIp))

            #Reconstruct Request and send it 
            parsedPath = '/' + '/'.join(path.split("/")[3:])
            newRequest = "GET {} HTTP/1.0\r\n".format(parsedPath)
            hostHeader = "Host: {}\r\n".format(host)
            modRequest = newRequest + hostHeader + "\r\n"
            proxy.sendall(modRequest.encode())

            #Obtain response fully
            responseParts = []
            while True:
                data = proxy.recv(2048)
                if not data:
                    break
                responseParts.append(data)
            proxyResponse = b''.join(responseParts)

            #Send response to client connection
            print("Sending response back to client ({} bytes)".format(len(proxyResponse)))
            client_connection.sendall(proxyResponse)

        #Close connection 
        finally:
            proxy.close()

#loop to continuously respond to requests 
while True:
    #Obtain client info and request. Send request 
    connection, address = server.accept()
    request = connection.recv(1024).decode('utf-8')
    response = forward_request(request, connection)
    connection.sendall(response)

    #close client  
    connection.close()