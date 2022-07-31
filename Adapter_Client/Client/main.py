import sys
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QSlider, QLineEdit, QComboBox
from PyQt5.QtWidgets import QLabel, QMainWindow, QWidget
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QTimer, qDebug
from PyQt5.QtGui import QCursor
from fcmcclient import FCMCClient
from fcmcconfig import FCMCConfig as config
from fcmckinematics import FCMCKinematics as kinematics

#Mapping constants: feed override slider values --> timer duration in ms
MAP_IN_MIN = 1
MAP_IN_MAX = 100
MAP_OUT_MIN = 200
MAP_OUT_MAX = 4

#CAD model configuration info
CAD_CONFIG_PATH = 'fc_kine_config_plotter.json'

class ExampleGui(QMainWindow):
    '''PyQt GUI example using the FCMC client class'''

    def __init__(self):
        super().__init__()

        #initialise current position value and target position value
        self.target_pos = self.act_pos = 0

        #initial value of feed override slider
        self.fdovr_inital = 80

        #initial speed value calculated from feed override slider 
        self.speed = self.mapValue(self.fdovr_inital, 
                                   MAP_IN_MIN, MAP_IN_MAX, MAP_OUT_MIN, MAP_OUT_MAX)

        #initialise timer object
        self.timer = QTimer()

        #feed stop = False allows values to be sent to FCMC server 
        self.fd_stop = False

        #dictionary to house list of setup info by axis label
        self.axis_setup = {}

        self.initUI()

    
    def updateCAD(self, tar_pos):
        '''handling method to update target positions in FCMC Adapter object 
        and trigger mechanism to update server'''
        #set the current geometry axis target value in the configuration object
        self.kine_handler.setGeoAxValue(self.axis_sel.currentText(), tar_pos)
        
        #calculate the target machine axis values from the geometry axis values in the configuration object
        self.kine_handler.calcAxValues("machAxes")

        #send all machine axis values in the configuration object to the fcmc server
        self.fcmc.sendValuesToCAD()

        #display new position value in GUI
        self.pos.setText(str(tar_pos))
    

    def countUp(self):
        '''slot to increment and send position value'''
        if not self.fd_stop:
            #feed override slider > 0
            #increment target position value
            self.target_pos += 1

            #call the mechanism to update the FreeCAD model 
            self.updateCAD(self.target_pos)


    def countDown(self):
        '''slot to decrement and send position value'''
        if not self.fd_stop:
            #changes to positon value enabled
            #decrement target position value
            self.target_pos -= 1

            #call the mechanism to update the FreeCAD model 
            self.updateCAD(self.target_pos)


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
        #initialise configuration object with path to the configuration file
        self.fcmc_config_handler = config(CAD_CONFIG_PATH)
        
        #get the reference to the fcmc configuration object
        self.cad_config = self.fcmc_config_handler.get_config()
        
        #initialise fcmc client object with configuration object reference as argument
        self.fcmc = FCMCClient(self.cad_config)

        #initialise fcmc kinematics object with configuration object reference as argument
        self.kine_handler = kinematics(self.cad_config)
        
        #calculate the geometry axis values to be displayed in the GUI 
        #from the machine axi values reported by the fcmc server
        self.kine_handler.calcAxValues("geoAxes")

        #get the names of the geometry axes
        self.geo_axes = list(self.kine_handler.axis_list())
        
        #initialise position value and label:
        #by default initialize to the first geo axis that is listed in the config-file
        first_geo = self.geo_axes[0]

        #initialize target position and actual position
        self.target_pos = self.act_pos = self.kine_handler.axis_pos(first_geo)
        
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

    
    def setActualPosLabel(self):
        '''sets the actual position label according to what is selected by the combo box'''
        #get the corresponding geo axis and CAD object
        geo = self.axis_sel.currentText()

        #set target position value to the value of the selected axis
        self.target_pos = self.kine_handler.axis_pos(geo)

        #set the actual pos display label
        self.pos.setText(str(self.target_pos))


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


        #setup axis selection dropdown
        self.axis_sel = QComboBox(self)
        self.axis_sel.addItems(self.geo_axes)
        self.axis_sel.setStyleSheet(
            "border: 1px solid 'transparent';" +
            "font-size: 35px;" +
            "color: '#00ffff';" 
        )
        


        #setup label to display current positon/constraint value
        self.pos = QLabel(str(self.act_pos))
        self.pos.setAlignment(QtCore.Qt.AlignCenter)
        self.pos.setStyleSheet(
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
        grid.addWidget(self.axis_sel, 0, 5, 1, 5)   
        grid.addWidget(self.pos, 1, 5, 1, 5)
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

        #connect comboBox to its slot
        self.axis_sel.currentTextChanged.connect(self.setActualPosLabel)

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
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.connect_btn.setStyleSheet(
            "border: 4px solid '#00ffff';" +
            "border-radius: 45px;" +
            "font-size: 35px;" +
            "color: 'white';" +
            "padding: 25px 0;" +
            "margin: 25px 200px}" +
            "*:hover{background: '#00ffff';}"
        )

        #add widget to layout
        grid.addWidget(self.connect_btn, 0, 0)
        
        #connect signals to their slots
        self.connect_btn.clicked.connect(self.connectFCMC)

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
    gui = ExampleGui()
    gui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()