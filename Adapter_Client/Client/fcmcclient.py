import socket
import sys
import pickle
from fcmcconfig import FCMCConfig as config

#tcp info
TCP_ADDRESS = 'localhost'
TCP_PORT = 1234
HEADER_LENGTH = 10

#CAD model configuration info
CAD_CONFIG_PATH = 'fc_setup.json'

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

        #Info of the FreeCAD model configuration
        config_handler = config(CAD_CONFIG_PATH)
        self.cad_config = config_handler.get_config()

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

                    #extract the objects
                    objects = message['objects']

                    #iterate through all objects
                    for obj in objects:
                        #get the geoAssigns of the current object
                        geo_assigns = objects[obj]["geoAssign"]
                        
                        #iterate through all geoAssigns of an object
                        for geo in geo_assigns:
                            #update cad_config with the received values
                            self.cad_config['objects'][obj]['geoAssign'][geo]['value'] = geo_assigns[geo]["value"]

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
        #create a new object holding the kinematic configuration
        scv_config_handler = config(CAD_CONFIG_PATH)
        scv_dict = scv_config_handler.get_config()
        
        #add a property for the request type to the dictionary
        scv_dict["type"] = "scv"

        #send the request to the fcmc server
        self._sendMessage(scv_dict)


    def _sendUmrRequest(self):
        '''request to server: Update Model Request (umr)'''
        #create a new object holding the kinematic configuration
        umr_config_handler = config(CAD_CONFIG_PATH)
        umr_dict = umr_config_handler.get_config()

        #get the current target values as stored in self.cad_config:
        #iterate through all configured objects
        for obj in self.cad_config['objects']:
            
            #iterate through all geoAssigns of the object
            for geo in self.cad_config['objects'][obj]['geoAssign']:
                #update umrDict with value from cad_config
                umr_dict['objects'][obj]['geoAssign'][geo]['value'] = self.cad_config['objects'][obj]['geoAssign'][geo]['value']

        #add a property for the request type to the dictionary
        umr_dict['type'] = 'umr'

        #send the request to the fcmc server
        self._sendMessage(umr_dict)


#-----------------------------------public methods-------------------------------------------


    def axis_pos(self, geo_assign):
        '''get a value of a FreeCAD object's geo_assign. 
        Use this method to get at a geo axis position'''
         #iterate through all configured objects
        for obj in self.cad_config['objects']:
            #does the objects possess the given geo axis?
            if geo_assign in self.cad_config['objects'][obj]['geoAssign']:
                #return with the value of the first occurence of the geo axis assign
                return self.cad_config["objects"][obj]["geoAssign"][geo_assign]["value"]


    def axis_list(self):
        '''get a dict of the configured geo axes and a corresponding object name'''
        #extract the configured objects
        obj_list = self.cad_config['objects']
        
        #initialise a list
        geo_list = []

        #iterate through all objects and their assigned geo_ax definition
        for obj in obj_list:
            #extract the geo axis assigns of the current object
            geos = obj_list[obj]['geoAssign']
            
            #iterate through all geo axis assigns
            for geo in geos:
                #get only the first occurence of a geo axis
                if not geo in geo_list:
                    #add new geo_ax definitions to the list
                    geo_list.append(geo)

        return geo_list


    def setGeoAxValue(self, geo, value):
        '''update the values of a given geo axis in the config dictionary'''
        #iterate through all configured objects
        for obj in self.cad_config['objects']:
            #does the objects possess the given geo axis?
            if geo in self.cad_config['objects'][obj]['geoAssign']:
                #update the value of the geo axis in that object
                self.cad_config['objects'][obj]['geoAssign'][geo]['value'] = value

    
    def sendValuesToCAD(self):
        '''method to send all values to the FreeCAD server'''
        #is the server available?
        if self.prev_msg == "blocked!":
            pass
        else:
            #FCMC server ready to receive: send Update Model Request
            self._sendUmrRequest()
        
        #check for acknowledgement from FCMC server
        self.prev_msg = self._recvMessage()
