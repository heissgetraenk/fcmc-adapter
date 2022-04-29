import socket
import sys

#tcp info
TCP_ADDRESS = 'localhost'
TCP_PORT = 1243
HEADER_LENGTH = 10

class FCMCClient:
    '''TCP client to connect with FCMC server'''

    def __init__(self) -> None:
        #tcp setup
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((TCP_ADDRESS, TCP_PORT))

        #blocking off: recv does not wait for the server 
        #but throws an exception when nothing can be recv'd 
        #this is used to sync the server with the client
        self.client_socket.setblocking(False)

        #variable to hold the position of the CAD model
        self.cur_pos1 = 0

        self.setup_complete = False

        while not self.setup_complete:
            # wait for the server connection and the CAD configuration info before 
            # finishing the setup
            
            try:
                message_header = self.client_socket.recv(HEADER_LENGTH)

                if not len(message_header):
                    #nothing was received. server can't be reached.
                    sys.exit()

                #figure out the length of the message
                message_length = int(message_header.decode("utf-8").strip())

                #receive the message body
                message = self.client_socket.recv(message_length).decode("utf-8")
                        
                if(message):
                    #the message contained something
                    axis_info = message.split(",")

                    #copy the current value of the FreeCAD constraint 
                    #from the axis info message
                    self.cur_pos1 = float(axis_info[2])
                    self.setup_complete = True
            
            except:
                print("Error receiving setup message")
            
    def sendValue(self, value):
        '''send a value to the FCMC server'''
        try:
            message = value

            if message:
            #if the message isn't empty:
                message = message.encode("utf-8")
                message_header = f"{len(message) :< {HEADER_LENGTH}}".encode("utf-8")
                
                #send message
                self.client_socket.send(message_header + message)

        except Exception as e:
            #server couldn't be reached
            print(str(e))
            sys.exit()
  

    def recvCurrentPos(self):
        '''receive the acknoledgement from FCMC server'''
        try:
            act_pos_header = self.client_socket.recv(HEADER_LENGTH)
        except:
            #the server isn't sending: it's still busy
            #exit the method by returning an invalid value 
            return "blocked"

        #figure out the message length
        act_pos_length = int(act_pos_header.decode("utf-8").strip())

        #receive the message
        act_pos = self.client_socket.recv(act_pos_length).decode("utf-8")

        if (act_pos):
            #acknowledgement received
            return act_pos

        
    def inital_pos(self):
        '''getter for the initial constraint value'''
        return self.cur_pos1

        





