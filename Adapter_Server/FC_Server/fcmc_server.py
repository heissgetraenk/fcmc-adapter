import FreeCAD as App
import FreeCADGui
from PySide import QtGui
import select
import socket
import sys

#tcp info
TCP_ADDRESS = 'localhost'
TCP_PORT = 1243
HEADER_LENGTH = 10

#configuration of CAD model
FC_DOC_NAME = 'PistonAnimation'
FC_OBJ_NAME = 'Sketch'
FC_CONSTR_NUM = 10

AXIS_TYPE = "ROTATING"
AXIS_VALUE_RANGE = 360


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

    def terminate(self):
        '''terminate the server'''
        self.is_running = False

    def showDialog(self):
        '''present a message box to show status of server. Close-button is used to terminate the server'''
        mb = QtGui.QMessageBox()
        mb.setIcon(mb.Icon.Warning)
        mb.setText("Wait for connection...")
        mb.setWindowTitle("Connection")
        mb.setModal(False)
        mb.setStandardButtons(mb.StandardButton.Close)
        mb.buttonClicked.connect(lambda btn : self.terminate())
        mb.show()
        self.message_box = mb


    def axis_info(self):
        '''prepares the string of the CAD config info to be sent to the client'''
        #in the FreeCAD Document: collect the inital value of the constraint
        act_val = App.getDocument(FC_DOC_NAME).getObject(FC_OBJ_NAME).getDatum(FC_CONSTR_NUM).Value

        #preparing the message string
        msg = AXIS_TYPE + "," + str(AXIS_VALUE_RANGE) + "," + str(act_val)
        msg = msg.encode('utf-8')
        msg_header = f"{len(msg) :< {HEADER_LENGTH}}".encode("utf-8")
        full_msg = msg_header + msg

        return full_msg


    def cur_pos_msg(self, pos):
        '''Current position message: this method prepares the acknoledgement string. 
        this message is used to inform the client that the server is done
        setting the constraint to the received value'''
        msg = pos
        msg = msg.encode('utf-8')
        msg_header = f"{len(msg) :< {HEADER_LENGTH}}".encode("utf-8")
        full_msg = msg_header + msg
        return full_msg

    def recvMessage(self, client_socket):
        '''method to receive messages from the client'''
        try:
            message_header = client_socket.recv(HEADER_LENGTH)

            if not len(message_header):
                #nothing was sent, exit from method
                return False

            #figure out how long the message body will be
            message_length = int(message_header.decode("utf-8").strip())

            #return the message header and the message body as a dictonary   
            return {"header": message_header, "data": client_socket.recv(message_length)}      

        except:
            #something went wrong while receiving
            return False


    def updateCAD(self, pos):
        '''method to interact with FreeCAD model'''
        #in the FreeCAD Document: set the constraint
        App.getDocument(FC_DOC_NAME).getObject(FC_OBJ_NAME).setDatum(FC_CONSTR_NUM, App.Units.Quantity(pos + ' deg'))
        #in the FreeCAD Document: update the CAD model
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
                self.showDialog()

            self.is_waiting = True
            
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
                        client_socket, address = self.input_socket.accept()

                        read_list.append(client_socket)

                        self.remote_address = address[0]

                        #update message box to show the connection
                        if self.message_box:
                            self.message_box.setText("Connection established!")

                        #send CAD configuration to the client
                        client_socket.send(self.axis_info())    

                        self.is_waiting = False

                    else:
                        #all subsequent communication between server and client
                        
                        #receive a message
                        message = self.recvMessage(client_socket)
                        
                        if message is False:
                            #the client didn't send anything, so keep receiving
                            continue

                        #a message was received: decode it and update the model with it
                        recv_pos = message['data'].decode('utf-8')
                        self.updateCAD(recv_pos)

                        #the model was updated: acknoledge readiness to receive 
                        #by returning the current constraint value to the client.
                        #the client may use this to stay in sync with the server
                        try:
                            client_socket.send(self.cur_pos_msg(recv_pos))
                        except:
                            print("error sending acknoledgement")

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