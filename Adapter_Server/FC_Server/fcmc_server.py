import FreeCAD as App
import FreeCADGui
from PySide import QtGui
import select
import socket
import sys
import pickle

#tcp info
TCP_ADDRESS = 'localhost'
TCP_PORT = 1234
HEADER_LENGTH = 10

class FcmcServer:
    '''FreeCAD Motion Control Server: TCP server that connects a custom tcp client with a FreeCAD Document. #
    The server receives a position value, writes that value onto a constraint of a FreeCAD Master Sketch and
    recomputes the model to display the changed position'''

    def __init__(self, listen_address, listen_port):
        self.is_running = False
        self.is_waiting = False
        self.remote_address = ""
        self.listen_address = listen_address
        self.listen_port = listen_port
        self.message_box = False
        self.doc_name = ""

    def _terminate(self):
        '''terminate the server'''
        self.is_running = False

    def _showDialog(self):
        '''present a message box to show status of server. Close-button is used to terminate the server'''
        mb = QtGui.QMessageBox()
        mb.setIcon(mb.Icon.Warning)
        mb.setText("Wait for connection...")
        mb.setWindowTitle("Connection")
        mb.setModal(False)
        mb.setStandardButtons(mb.StandardButton.Close)
        mb.buttonClicked.connect(lambda btn : self._terminate())
        mb.show()
        self.message_box = mb


    def _sendMessage(self, msg):
        '''method to send a message'''
        #serialize the data to be sent
        myMsg = pickle.dumps(msg)

        #encode the message header
        msg_header = f"{len(myMsg) :< {HEADER_LENGTH}}".encode("utf-8")

        #concatenate the header and the message body
        full_msg = msg_header + myMsg

        #send the message
        self.client_socket.send(full_msg)


    def _recvMessage(self):
        '''method to receive messages'''
        try:
            #receive the fixed length header
            message_header = self.client_socket.recv(HEADER_LENGTH)

            #figure out how long the message body will be
            message_length = int(message_header.decode("utf-8").strip())

            #return the message   
            return pickle.loads(self.client_socket.recv(message_length))   

        except:
            #something went wrong while receiving
            return "blocked!"


    def _handleRequest(self, request):
        '''method to formulate a response to requests from the client'''
        #determine type of request
        req_type = request['type']

        if req_type == 'scv':            
        #handle scv request
            answ_dict = request

            #get the name of the FreeCAD document
            self.doc_name = request['fcDocName']

            #iterate through all configured objects
            for obj in answ_dict['objects']:
                #append actual values to the recv'd dict
                answ_dict['objects'][obj]['geoAssign'] = self._getActValues(self.doc_name, obj,
                                                                 answ_dict)

            #return updated dict
            return answ_dict

        elif req_type == 'umr':
        #handle umr request
            self._updateCAD(self.doc_name, request)

        
        
    def _getActValues(self, doc, obj, config_dict):
        '''get actual values from FreeCAD Document for a given object''' 
        #extract the geo axis assigns from the configuration dictionary
        updated_geo = geo_assigns = config_dict['objects'][obj]['geoAssign']

        #iterate through all geoAssigns of the given object
        for geo in geo_assigns:

            if geo_assigns[geo]["type"] == "rotary":
                #rotary type geo: get the sketch constraint value by ConstraintNo (move_prop_id)
                move_prop_id = geo_assigns[geo]["movePropID"]
                sketch_name = geo_assigns[geo]["sketch"]
                #actual value from FreeCAD Document:
                updated_geo[geo]["value"] = App.getDocument(doc).getObjectsByLabel(sketch_name)[0].getDatum(int(move_prop_id)).Value

            elif geo_assigns[geo]["type"] == "linear":
                #linear type geo: get x, y or z component of Placement Vector from FreeCAD Document
                if geo == "X":
                    #actual position of object in X:
                    updated_geo[geo]["value"] = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Base.x

                elif geo == "Y":
                    #actual position of object in Y:
                    updated_geo[geo]["value"] = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Base.y

                elif geo == "Z": 
                    #actual position of object in Z:
                    updated_geo[geo]["value"] = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Base.z    

        return updated_geo      


    def _updateCAD(self, doc, upd_dict):
        '''method to interact with FreeCAD model'''
        #extract objects from configuration
        objects = upd_dict['objects']
        
        #iterate through all configured objects
        for obj in objects:
            #extract geo axis assignments for the given object
            geo_assigns = objects[obj]['geoAssign']
            
            #iterate through all geoAssigns of the object
            for geo in geo_assigns:
                #value to update to
                value = geo_assigns[geo]['value']
                
                #is the current geo axis assign of type "rotary"?
                if geo_assigns[geo]["type"] == "rotary":
                    #get the Constraint number (move_prop_id) responsible for the rotary movement
                    move_prop_id = int(geo_assigns[geo]["movePropID"])

                    #get the name of the sketch the constraint belongs to
                    sketch_name = geo_assigns[geo]["sketch"]

                    #update the sketch constraint value
                    App.getDocument(doc).getObjectsByLabel(sketch_name)[0].setDatum(move_prop_id, App.Units.Quantity(value))

                #is the current geo axis assign of type "linear"?
                elif geo_assigns[geo]["type"] == "linear":
                    #linear type geo: update x, y or z component of Placement Vector of FreeCAD Document, maintain rotation vector:
                    
                    #get the current rotation of the object
                    angle = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Rotation.Angle
                    rot_x = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Rotation.Axis.x
                    rot_y = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Rotation.Axis.y
                    rot_z = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Rotation.Axis.z

                    #get the current placement of the object
                    x = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Base.x
                    y = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Base.y
                    z = App.getDocument(doc).getObjectsByLabel(obj)[0].Placement.Base.z

                    #update the vector component corresponding to the current geo axis assign
                    if geo == "X":
                        #update x position
                        App.getDocument(doc).getObjectsByLabel(obj)[0].Placement = App.Placement(App.Vector(value,y,z),App.Rotation(App.Vector(rot_x, rot_y, rot_z), angle))

                    elif geo == "Y":
                        #update y position
                        App.getDocument(doc).getObjectsByLabel(obj)[0].Placement = App.Placement(App.Vector(x,value,z),App.Rotation(App.Vector(rot_x, rot_y, rot_z), angle))

                    elif geo == "Z":
                        #update z position
                        App.getDocument(doc).getObjectsByLabel(obj)[0].Placement = App.Placement(App.Vector(x,y,value),App.Rotation(App.Vector(rot_x, rot_y, rot_z), angle))
                        
        #recompute the CAD model
        App.ActiveDocument.recompute()


    def run(self, with_dialog=True):
        '''method to run the server'''
        self.is_running=True

        #tcp setup
        self.input_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.input_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.input_socket.bind((self.listen_address, self.listen_port))
            self.input_socket.listen(1)

            read_list = [self.input_socket]

            if with_dialog:
                self._showDialog()
            
            write_list = []

            #main server loop
            while self.is_running:                
                #keep FreeCAD from freezing up:
                FreeCADGui.updateGui()

                #select statement
                readable, writable, errored = select.select(read_list, write_list, [], 0.05)
                
                for s in readable:
                    
                    if s is self.input_socket:
                        #this is the first communication between the server and the client
                        self.client_socket, address = self.input_socket.accept()

                        read_list.append(self.client_socket)

                        self.remote_address = address[0]

                        #update message box to show the connection
                        if self.message_box:
                            self.message_box.setText("Connection established!")

                        #receive scv (Send Current Values) request
                        try:
                            message = self._recvMessage()

                            if not message == "blocked!":
                                answer = self._handleRequest(message)

                        except:
                            print("Error receiving setup message")
                            continue
                        
                        #send CAD configuration to the client
                        self._sendMessage(answer)

                    else:
                        #all subsequent communication between server and client
                        
                        try:
                        #receive a message
                            message = self._recvMessage()
                            
                            if message is False:
                                #the client didn't send anything, so keep receiving
                                continue
                            elif message == "blocked":
                                #the socket is blocked, keep receiving
                                continue

                            #a message was received: handle the request
                            self._handleRequest(message)

                            #the model was updated: acknowledge readiness to receive 
                            #by returning the message sent by the client.
                            try:
                                self._sendMessage(message)
                            except:
                                print("error sending acknowledgement")

                        except:
                            #the socket is blocked, keep receiving
                            continue

        except ValueError:
            print("Value Error of FCMC Server: %s\r\n" % sys.exc_info()[1])

            try:
                self.input_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                print("OSError of FCMC Server while trying to close the socket")

        print("FCMC Server is terminating. Bye for now!")
        self.input_socket.close()


def main():
    '''main function of the server application'''
    server = FcmcServer(TCP_ADDRESS, TCP_PORT)
    server.run()


if __name__ == '__main__':
    main()
