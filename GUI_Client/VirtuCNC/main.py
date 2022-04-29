import sys
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QSlider
from PyQt5.QtWidgets import QLabel, QMainWindow, QWidget
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QTimer, qDebug
from PyQt5.QtGui import QCursor
from fcmcclient import FCMCClient

#Mapping constants: feed override slider values --> timer duration in ms
MAP_IN_MIN = 1
MAP_IN_MAX = 100
MAP_OUT_MIN = 200
MAP_OUT_MAX = 4

class VirtuCNC(QMainWindow):
    '''PyQt GUI example using the FCMC client class'''

    def __init__(self):
        super().__init__()

        #initialise current position value and target position value
        self.target_pos1 = self.cur_pos1 = 0

        #initial value of feed override slider
        self.fdovr_inital = 80

        #initial speed value calculated from feed override slider 
        self.speed = self.mapValue(self.fdovr_inital, 
                                   MAP_IN_MIN, MAP_IN_MAX, MAP_OUT_MIN, MAP_OUT_MAX)

        #initialise timer object
        self.timer = QTimer()

        #feed stop = False allows values to be sent to FCMC server 
        self.fd_stop = False

        self.initUI()
    

    def countUp(self):
        '''slot to increment and send position value'''
        if not self.fd_stop:
            #feed override slider > 0
            #increment target position value
            self.target_pos1 += 1

            #display new position value in GUI
            self.pos1.setText(str(self.target_pos1))

            if (self.cur_pos1 != "blocked"):
                #FCMC server ready to receive: send new value
                self.fcmc.sendValue(str(self.target_pos1))

            #check for acknowledgement from FCMC server
            self.cur_pos1 = self.fcmc.recvCurrentPos()


    def countDown(self):
        '''slot to decrement and send position value'''
        if not self.fd_stop:
            #changes to positon value enabled
            #decrement target position value
            self.target_pos1 -= 1

            #display new position value in GUI
            self.pos1.setText(str(self.target_pos1))

            if (self.cur_pos1 != "blocked"):
                #FCMC server ready to receive: send new value
                self.fcmc.sendValue(str(self.target_pos1))

            #check for acknowledgement from FCMC server
            self.cur_pos1 = self.fcmc.recvCurrentPos()


    def startTimer(self):
        '''starts the timer object with the speed (timer duration in ms)
        from the feed override slider'''
        #which button called this method?
        sender = self.sender()

        if sender.text() == "+":
            #call by "+" button: connect timeout signal to countUp method
            self.timer.timeout.connect(self.countUp)

            #start the timer
            self.timer.start(self.speed)
        elif sender.text() == "-":
            #call by "-" button: connect timeout signal to countDown method
            self.timer.timeout.connect(self.countDown)
            
            #start the timer
            self.timer.start(self.speed)


    def stopTimer(self):
        '''stop timer object and diconnect all connected slots'''
        #stop the timer
        self.timer.stop()

        #disconnect slots
        self.timer.disconnect()


    def connectFCMC(self):
        '''method to handle connection to FCMC server'''

        #initialise FCMC Client object
        self.fcmc = FCMCClient()
        
        #set target position value and current position value 
        #to FCMC Client's inital value
        self.target_pos1 = self.cur_pos1 = self.fcmc.inital_pos()
        
        #setup and display Machine Control Panel Frame
        self.displayMCPFrame()

    def fdOvrChanged(self):
        '''slot to handle changes of the feed override slider'''

        #display new value of the slider
        self.fdovr_val.setText(str(self.feed_ovr1.value()) + "%")

        if (self.feed_ovr1.value() == 0):
            #slider = 0: do not enable changes to position value
            self.fd_stop = True
        else:
            #slider > 0: map slider value to timer duration in ms, update speed value
            self.speed = self.mapValue(self.feed_ovr1.value(),
                                       MAP_IN_MIN, MAP_IN_MAX, MAP_OUT_MIN, MAP_OUT_MAX)

            #enable changes to position value
            self.fd_stop = False

    def mapValue(self, value, in_min, in_max, out_min, out_max):
        '''method to map a given value from an 
        input value range to an output value range'''
        #input range
        in_span = in_max - in_min

        #output range
        out_span = out_max - out_min

        #input value as % of input range
        value_scaled = float(value - in_min) / float(in_span)

        #mapping onto output range
        return int(out_min + (value_scaled * out_span))


    def displayMCPFrame(self):
        '''setup and display Machine Control Panel Widget'''
        #initialise qt widget
        mcp_widget = QWidget()

        #initialise qt grid layout
        grid = QGridLayout()

        #setup "+"-button
        self.plus = QPushButton("+")
        self.plus.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.plus.setStyleSheet(
            "border: 4px solid '#00ffff';" +
            "border-radius: 45px;" +
            "font-size: 35px;" +
            "color: 'white';" +
            "padding: 25px 0;" +
            "margin: 10px 20px}" +
            "*:hover{background: '#00ffff';}"
        )

        #setup "-"-button
        self.minus = QPushButton("-")
        self.minus.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.minus.setStyleSheet(
            "border: 4px solid '#00ffff';" +
            "border-radius: 45px;" +
            "font-size: 35px;" +
            "color: 'white';" +
            "padding: 25px 0;" +
            "margin: 10px 20px}" +
            "*:hover{background: '#00ffff';}"
        )

        #setup label to display current positon/constraint value
        self.pos1 = QLabel(str(self.cur_pos1))
        self.pos1.setAlignment(QtCore.Qt.AlignCenter)
        self.pos1.setStyleSheet(
            "font-size: 75px;" +
            "color: 'white';" +
            "padding: 20px 15px;" +
            "margin: 10 2px};"
        )

        #setup feed override slider
        self.feed_ovr1 = QSlider(QtCore.Qt.Horizontal)
        self.feed_ovr1.setMinimum(0)
        self.feed_ovr1.setMaximum(100)
        self.feed_ovr1.setMinimumHeight(30)
        self.feed_ovr1.setValue(self.fdovr_inital)
        self.feed_ovr1.setStyleSheet(
            "QSlider::groove:horizontal" + 
            "{border: 1px solid #00ffff;" +
            "height: 3px;" + 
            "background-color: #00ffff;" +
            "margin: 0;" + 
            "}" +
            "QSlider::handle:horizontal" +
            "{background-color: #2e3436;" +
            "border: 2px solid #00ffff;" +
            "height: 20px;" +
            "width: 18px;" +
            "margin: -10px 0;" +
            "border-radius: 10px;" +
            "}"
        )

        #setup label for feed override value
        self.fdovr_val = QLabel(str(self.fdovr_inital) + "%")
        self.fdovr_val.setAlignment(QtCore.Qt.AlignCenter)
        self.fdovr_val.setStyleSheet(
            "font-size: 32px;" +
            "color: 'white';" +
            "padding: 2px 1px;" +
            "margin: 10 2px};"
        )

        #add gui widgets to layout
        grid.addWidget(self.plus, 0, 0, 1, 5)
        grid.addWidget(self.minus, 1, 0, 1, 5)       
        grid.addWidget(self.pos1, 0, 5, 2, 5)
        grid.addWidget(self.feed_ovr1, 2, 0, 1, 9)
        grid.addWidget(self.fdovr_val, 2, 9, 1, 1)

        #connect signals to timer slots
        self.plus.pressed.connect(self.startTimer)
        self.plus.released.connect(self.stopTimer)
        self.minus.pressed.connect(self.startTimer)
        self.minus.released.connect(self.stopTimer)

        #connect feed ovr slider's valueChanged signal to
        #to feed ovr changed slot
        self.feed_ovr1.valueChanged.connect(self.fdOvrChanged)

        #apply layout to widget
        mcp_widget.setLayout(grid)

        #apply widget to window
        self.setCentralWidget(mcp_widget)

    
    def displayConnectFrame(self):
        '''setup and display connect frame Widget'''
        #initialise qt widget
        connectWidget = QWidget()

        #initialise qt grid layout
        grid = QGridLayout()

        #setup connect button
        self.connectBtn = QPushButton("Connect")
        self.connectBtn.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.connectBtn.setStyleSheet(
            "border: 4px solid '#00ffff';" +
            "border-radius: 45px;" +
            "font-size: 35px;" +
            "color: 'white';" +
            "padding: 25px 0;" +
            "margin: 100px 200px}" +
            "*:hover{background: '#00ffff';}"
        )

        #add widget to layout
        grid.addWidget(self.connectBtn, 0, 0)
        
        #connect button to FCMC connect method
        self.connectBtn.clicked.connect(self.connectFCMC)

        #apply layout to widget
        connectWidget.setLayout(grid)

        #apply widget to window
        self.setCentralWidget(connectWidget)


    def initUI(self):
        '''method to initialise GUI'''
        self.setWindowTitle("VirtuCNC")
        self.setStyleSheet("background-color: '#2e3436';")
        self.setFixedWidth(750)

        #first frame to be displayed
        self.displayConnectFrame()

        


def main():
    app = QApplication(sys.argv)
    cnc = VirtuCNC()
    cnc.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
