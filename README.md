# fcmc-adapter
FreeCAD Motion Control Adapter

The purpose of this project is to provide an interface for controlling FreeCAD objects.
The client sends a value to the server, which uses it to update a constraint in the FreeCAD document.

This project contains the following items:
<ul>
  <li>fcmc_server.py: A TCP server to run inside of FreeCAD</li>
  <li>fcmcclient.py: A TCP Client that provides some mehtods to communicate with the server</li>
  <li>main.py: An example application that uses the fcmc client to position values to FreeCAD</li>
  <li>Some FreeCAD files to test on</li>
<ul/>
  
