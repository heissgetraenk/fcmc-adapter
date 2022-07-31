from tkinter import Y
import FreeCAD as App
import FreeCADGui
from PySide import QtGui
import select
import socket
import sys
import pickle
import math

#tcp info
TCP_ADDRESS = 'localhost'
TCP_PORT = 1234
HEADER_LENGTH = 10

#rounding ceiling for actual values
RND_PARAM = 3

class FcmcServer:
    '''FreeCAD Motion Control Server: TCP server that connects a custom tcp client with a FreeCAD Document'''

    def __init__(self, listen_address, listen_port):
        self.is_running = False
        self.is_waiting = False
        self.remote_address = ""
        self.listen_address = listen_address
        self.listen_port = listen_port
        self.message_box = False

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
            
            #the type property is no longer required, delete it so it won't get sent back to the client
            del answ_dict['type']

            #iterate through all configured objects
            for machAx in answ_dict:
                #append actual values to the recv'd dict
                try:
                    answ_dict[machAx] = self._getActValues(answ_dict[machAx])
                except:
                    pass

            #return updated dict
            return answ_dict

        elif req_type == 'umr':
        #handle umr request
            del request['type']
            self._updateCAD(request)

        
        
    def _getActValues(self, axis_dict):
        '''get actual values from FreeCAD Document for a given machine axis''' 
        #extract relevant info for querying actual values from FreeCAD
        doc = axis_dict['docName']
        obj = axis_dict['object']

        #actual placement
        axis_dict['placement']['x'] = round(App.getDocument(doc).getObjectsByLabel(obj)[0].AttachmentOffset.Base.x, RND_PARAM)
        axis_dict['placement']['y'] = round(App.getDocument(doc).getObjectsByLabel(obj)[0].AttachmentOffset.Base.y, RND_PARAM)
        axis_dict['placement']['z'] = round(App.getDocument(doc).getObjectsByLabel(obj)[0].AttachmentOffset.Base.z, RND_PARAM)

        #actual rotation
        rad_angle = App.getDocument(doc).getObjectsByLabel(obj)[0].AttachmentOffset.Rotation.Angle
        axis_dict['rotation']['angle'] = round(rad_angle * 180 / math.pi, RND_PARAM)
        axis_dict['rotation']['x'] = round(App.getDocument(doc).getObjectsByLabel(obj)[0].AttachmentOffset.Rotation.Axis.x, RND_PARAM)
        axis_dict['rotation']['y'] = round(App.getDocument(doc).getObjectsByLabel(obj)[0].AttachmentOffset.Rotation.Axis.y, RND_PARAM)
        axis_dict['rotation']['z'] = round(App.getDocument(doc).getObjectsByLabel(obj)[0].AttachmentOffset.Rotation.Axis.z, RND_PARAM)

        return axis_dict     


    def _updateCAD(self, upd_dict):
        '''method to interact with FreeCAD model'''
        #iterate through all axes that need to be updated
        for machAx in upd_dict:
            #extract relevant info fo rupdating the values
            doc = upd_dict[machAx]['docName']
            obj = upd_dict[machAx]['object']

            #placement vector components
            x = upd_dict[machAx]['placement']['x']
            y = upd_dict[machAx]['placement']['y']
            z = upd_dict[machAx]['placement']['z']

            #rotation vector components
            rot_x = upd_dict[machAx]['rotation']['x']
            rot_y = upd_dict[machAx]['rotation']['y']
            rot_z = upd_dict[machAx]['rotation']['z']
            angle = upd_dict[machAx]['rotation']['angle']

            #update the axis values in the freecad document
            App.getDocument(doc).getObjectsByLabel(obj)[0].AttachmentOffset = App.Placement(App.Vector(x,y,z),App.Rotation(App.Vector(rot_x, rot_y, rot_z), angle))

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
                        #first communication between server and client
                        self.client_socket, address = self.input_socket.accept()

                        read_list.append(self.client_socket)

                        self.remote_address = address[0]

                        #update message box to show the connection state
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
