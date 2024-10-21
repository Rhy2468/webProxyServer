import socket
import threading 
import os 
import time 

port = 9090
host = socket.gethostbyname("localhost")
 
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen() 

    print("Server is listening on http://{}:{}".format(host, port))

    cont = True
    while cont: 
        clientConn, clientAddr = server.accept()
        clientThread = threading.Thread(target = handleClient, args = (clientConn, clientAddr))
        clientThread.start() 

def handleClient(connection, address): 
    print("Client Conn: {}, Client Address: {}\n".format(connection, address))

    try:
        request = connection.recv(1024).decode()

        if not request:
            error400 = "HTTP/1.0 400 Bad Request\r\n"
            connection.sendall(error400.encode())
            return
        

        print("Request received, request: {}".format(request))

        if (request): 
            requestForm= request.split("\r\n")[0]

            print("Request Exists and Formatted: {}\n".format(requestForm))
            
            method = requestForm.split()[0]
            if (method != 'GET'):
                error501 = "HTTP/1.1 501 Not Implemented\r\n"
                connection.sendall(error501.encode())
                return
            
            path = requestForm.split()[1] 

            if path == '/':
                path = '/test.html'
            file_path = "." + path 
            print("Method: {}\nPath: {}\n".format(method, file_path))

            if os.path.isfile(file_path):
                headers = request.split("\r\n")[1: ]
                modTime = None

                for header in headers: 
                    if header.startswith('If-Modified-Since:'):
                        modTime = header.split(': ', 1)[1]
                        break 
                
                format = '%a, %d %b %Y %H:%M GMT'
                fileTime = time.gmtime(os.path.getmtime(file_path))
                formattedFileModTime = time.strftime(format, fileTime)

                if modTime == formattedFileModTime: 
                    error304 = "HTTP/1.1 304 Not Modified\r\n"
                    connection.sendall(error304.encode())
                    return 
                else: 
                    file = open(file_path, 'r')
                    content = file.read() 
                    file.close() 
                    ok202 = "HTTP/1.1 200 OK\r\n"
                    ok202 += f"Last-Modified: {formattedFileModTime}\r\n"
                    ok202 += content
                    connection.sendall(ok202.encode())
                    return
            else: 
                error404 = "HTTP/1.1 404 Not Found\r\n"
                connection.sendall(error404.encode())
                return
        else: 
            print("Request is empty\n")
            return
    except Exception as e: 
        error400 = "HTTP/1.1 400 Bad Request\r\n"
        connection.sendall(error400.encode())
        return 
    finally:
        connection.close()

if __name__ == "__main__":
    main()

