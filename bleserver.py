# https://github.com/petzval/btferret

import btfpy
import random

class BLEServer:
  def __init__(self):
    self.count = 0
    self.local_node = None
    self.abcd_index = None
    self.cdef_index = None
    self.dcba_index = None
    self.deaf_index = None

  def string_to_hex(self, input_string):
    return [ord(char) for char in input_string]

  def initialize(self, device_name="bleserver_devices.txt", bug_name="bleserver_bug.txt"):
    # if (btfpy.Init_blue(device_name) == 0):
    #   exit(0)

    if (btfpy.Pre_init_blue(0) == 0):
      exit(0)
    device_name = "My New Pi"
    if (btfpy.Set_device_name(device_name, len(device_name)) == 0):
      exit(0)
    if (btfpy.Set_type(btfpy.BTYPE_ME) == 0):
      exit(0)
    node = 1000
    if (btfpy.Set_node(node) == 0):
      exit(0)
    address = "2C:CF:67:3D:C8:B7"
    if (btfpy.Set_address(address, len(address)) == 0):
      exit(0)
    primary_service = "1800"
    char_name = "Device Name"
    char_permit = 0x02
    char_size = 16
    char_uuid = "2A00"
    if (btfpy.Set_lechar(primary_service, char_name, char_permit, char_size, char_uuid) == 0):
      exit(0)



    
    

    if(btfpy.Post_init_blue() == 0):
      exit(0)
    btfpy.Output_file(bug_name)
    self.local_node = btfpy.Localnode()
    # self.abcd_index = btfpy.Find_ctic_index(self.local_node, btfpy.UUID_2, [0xAB,0xCD])
    # if self.abcd_index != 4:
    #   print("Not 4")
    #   exit(0)
    # self.cdef_index = btfpy.Find_ctic_index(self.local_node, btfpy.UUID_2, [0xCD,0xEF])
    # if self.cdef_index != 5:
    #   print("Not 5")
    #   exit(0)
    # self.deaf_index = btfpy.Find_ctic_index(self.local_node, btfpy.UUID_2, [0xDE,0xAF])
    # if self.deaf_index != 6:
    #   print("Not 6")
    #   exit(0)
    # self.dcba_index = btfpy.Find_ctic_index(self.local_node, btfpy.UUID_2, [0xDC,0xBA])
    # if self.dcba_index != 7:
    #   print("Not 7")
    #   exit(0)

    # Have self.abcd show "ENTER" at startup
    # btfpy.Write_ctic(self.local_node, self.abcd_index, self.string_to_hex("ENTER"), 0)  

    # btfpy.Keys_to_callback(btfpy.KEY_ON,0)
                                  # OPTIONAL - key presses are sent to le_callback
                                  # with operation=LE_KEYPRESS and cticn=key code 
                                  # The key that stops the server changes from x to ESC
                                  
    # section 3-7-1 Random address alternative setup
    btfpy.Set_le_random_address([0xD3,0x56,0xDB,0x04,0x32,0xA7])

    btfpy.Set_le_wait(5000)   # 5 second wait for connect/pair to complete

      # Ask for Just Works security which avoids passkey entry
    btfpy.Le_pair(self.local_node, btfpy.JUST_WORKS, 0)

  def start_server(self):
    btfpy.Le_server(lambda clientnode, operation, cticn: self.callback(clientnode, operation, cticn), 50)
                                  
    # btfpy.Le_server(le_callback,100)
                      # Become an LE server and wait for clients to connect.   
                      # when a client performs an operation such as connect, or
                      # write a characteristic, call the function le_callback()
                      # Call LE_TIMER in le_callback every 100 deci-seconds (10 seconds)
  def close(self):
    btfpy.Close_all()

  def callback(self, clientnode, operation, cticn):
    if(operation == btfpy.LE_CONNECT):
      self.count = 0
    elif(operation == btfpy.LE_READ):
      pass
    elif(operation == btfpy.LE_WRITE):
      data = btfpy.Read_ctic(self.local_node,cticn)
      if cticn == self.abcd_index:  # if abcd is written then update dcba
        btfpy.Write_ctic(self.local_node, self.dcba_index, [data], 0)
      elif cticn == self.cdef_index:  # Update cdef and write SET CNT to dcba
        idata = int.from_bytes(data)
        if 0 <= idata <= 255:
          btfpy.Write_ctic(self.local_node, self.cdef_index, [idata], 0)
          self.count = idata
          btfpy.Write_ctic(self.local_node, self.dcba_index, self.string_to_hex("SET CNT"), 0)
      else: # Other index write show error
        btfpy.Write_ctic(self.local_node, self.dcba_index, self.string_to_hex("ERROR"), 0)
    elif(operation == btfpy.LE_DISCONNECT):
      # clientnode has just disconnected
      # uncomment next line to stop LE server when client disconnects
      # return(btfpy.SERVER_EXIT)
      # otherwise LE server will continue and wait for another connection
      # or operation from other clients that are still connected
      pass
    elif(operation == btfpy.LE_TIMER):
      # The server timer calls here every timerds deci-seconds  
      # clientnode and cticn are invalid
      # This is called by the server, not a client   
      self.count = self.count + 5
      if self.count > 255:
        self.count = 0
      btfpy.Write_ctic(self.local_node, self.cdef_index, [self.count], 0)
      btfpy.Write_ctic(self.local_node, self.deaf_index, [random.randint(0,255)], 0)
      pass
    elif(operation == btfpy.LE_KEYPRESS):
      # Only active if btfpy.Keys_to_callback(btfpy.KEY_ON,0) has been called before le_server()
      # clientnode is invalid
      # cticn = key code
      #       = ASCII code of key (e.g. a=97)  OR
      #         btferret custom code for other keys such as Enter, Home,
      #         PgUp. Full list in keys_to_callback() section             
      pass  
    return(btfpy.SERVER_CONTINUE)

if __name__ == "__main__":
  ble_server = BLEServer()
  ble_server.initialize()
  ble_server.start_server()
  ble_server.close()
