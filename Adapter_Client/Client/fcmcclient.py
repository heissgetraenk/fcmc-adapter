import socket
import sys
import pickle

#tcp info
TCP_ADDRESS = 'localhost'
TCP_PORT = 1234
HEADER_LENGTH = 10

class FCMCClient:
    '''TCP client to connect with FCMC server'''

    def __init__(self, config) -> None:
        #tcp setup
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((TCP_ADDRESS, TCP_PORT))

        #blocking off: recv does not wait for the server
        #but throws an exception when nothing can be recv'd
        #this is used to sync the server with the client
        self.client_socket.setblocking(False)

        #receive configuration object as argument
        self.cad_config = config

        #setup loop variable
        self.setup_complete = False

        while not self.setup_complete:
            # wait for the server connection and the CAD configuration info before
            # finishing the setup

            #send info request
            self._sendSCVRequest()

            #receive info from server
            try:
                message = self._recvMessage()

                #does the server answer?
                if not message == "blocked!":
                    #update the cad_config dictionary with the actual machine axis values
                    self.cad_config['machAxes'] = message

                    #end of setup
                    self.setup_complete = True

                #remember the received message for the next client-server exchange
                self.prev_msg = message

            except:
                print("Error receiving setup message")


#-----------------------------------private methods-------------------------------------------
    def _sendMessage(self, msg):
        '''method to send a message to fcmc server'''
        #serialize the data to be sent
        myMsg = pickle.dumps(msg)

        #encode the message header
        msg_header = f"{len(myMsg) :< {HEADER_LENGTH}}".encode("utf-8")

        #concatenate the header and the message body
        full_msg = msg_header + myMsg

        #send the message)
        self.client_socket.send(full_msg)


    def _recvMessage(self):
        '''method to receive a message from fcmc server'''
        try:
            #receive the fixed length header
            message_header = self.client_socket.recv(HEADER_LENGTH)

            #figure out how long the message body will be
            message_length = int(message_header.decode("utf-8").strip())

            #unpickle and return the message
            return pickle.loads(self.client_socket.recv(message_length))

        except:
            #something went wrong while receiving
            return "blocked!"


    def _sendSCVRequest(self):
        '''request to server: Send Current Values (scv)'''
        #extract the machAxes section from the configuration object
        scv_dict = self.cad_config["machAxes"]

        #add a property for the request type to the configuration object
        scv_dict["type"] = "scv"

        #send the request to the fcmc server
        self._sendMessage(scv_dict)
        
        #delete the 'type' property from the configuration object again
        del scv_dict["type"]


    def _sendUmrRequest(self):
        '''request to server: Update Model Request (umr)'''
        #get the current target values as stored in self.cad_config:
        umr_dict = self.cad_config["machAxes"]

        #add a property for the request type to the configuration object
        umr_dict['type'] = 'umr'

        #send the request to the fcmc server
        self._sendMessage(umr_dict)

        #delete the 'type' property from the configuration object again
        del umr_dict['type']


#-----------------------------------public methods-------------------------------------------
    def sendValuesToCAD(self):
        '''method to send all values to the FreeCAD server'''
        #is the server available?
        if self.prev_msg == "blocked!":
            pass
        else:
            #FCMC server ready to receive: send Update Model Request 
            #with target values from the configuration object
            self._sendUmrRequest()

        #check for acknowledgement from FCMC server
        self.prev_msg = self._recvMessage()
