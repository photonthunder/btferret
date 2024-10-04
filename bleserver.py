# https://github.com/petzval/btferret

import btfpy
import random

count = 0
def le_callback(clientnode,operation,cticn):
  global count
  if(operation == btfpy.LE_CONNECT):
    count = 0
    # clientnode has just connected
    # pass
  elif(operation == btfpy.LE_READ):
    # clientnode has just read local characteristic cticn
    pass
  elif(operation == btfpy.LE_WRITE):
    # clientnode has just written local characteristic cticn
    data = btfpy.Read_ctic(btfpy.Localnode(),cticn)  # read characteristic to data
    btfpy.Write_ctic(btfpy.Localnode(),7,[data],0)
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
    # Data (index 6) is notify capable
    # so if the client has enabled notifications for this characteristic
    # the following write will send the data as a notification to the client
    # btfpy.Write_ctic(btfpy.Localnode(),6,[0x67],0)
    count = count + 5
    btfpy.Write_ctic(btfpy.Localnode(),5,[count],0)
    btfpy.Write_ctic(btfpy.Localnode(),6,[random.randint(0,255)],0)
  elif(operation == btfpy.LE_KEYPRESS):
    # Only active if btfpy.Keys_to_callback(btfpy.KEY_ON,0) has been called before le_server()
    # clientnode is invalid
    # cticn = key code
    #       = ASCII code of key (e.g. a=97)  OR
    #         btferret custom code for other keys such as Enter, Home,
    #         PgUp. Full list in keys_to_callback() section             
    pass  
  return(btfpy.SERVER_CONTINUE)
 
##### START #####
  
if(btfpy.Init_blue("bleserver_devices.txt") == 0):
  exit(0)
btfpy.Output_file("bleserver_bug.txt")
                 # write 0x56 to Info (index 5 in devices.txt)
                 # find index from UUID = CDEF
index = btfpy.Find_ctic_index(btfpy.Localnode(),btfpy.UUID_2,[0xCD,0xEF])  # should be 5
# count = count + 5
# btfpy.Write_ctic(btfpy.Localnode(),5,count,0)
                           # local device is allowed to write to its own
                           # characteristic Info
                           # Size is known from devices.txt, so last
                           # parameter (count) can be 0           
                   # write 0x12 0x34 to Control (index 4)
btfpy.Write_ctic(btfpy.Localnode(),4,[0x45,0x4E,0x54,0x45, 0x52],0)  

btfpy.Keys_to_callback(btfpy.KEY_ON,0)
                              # OPTIONAL - key presses are sent to le_callback
                              # with operation=LE_KEYPRESS and cticn=key code 
                              # The key that stops the server changes from x to ESC
                              
# section 3-7-1 Random address alternative setup
btfpy.Set_le_random_address([0xD3,0x56,0xDB,0x04,0x32,0xA7])

btfpy.Set_le_wait(5000)   # 5 second wait for connect/pair to complete

   # Ask for Just Works security which avoids passkey entry
                                  
btfpy.Le_pair(btfpy.Localnode(),btfpy.JUST_WORKS,0)

btfpy.Le_server(le_callback,50)
                              
# btfpy.Le_server(le_callback,100)
                   # Become an LE server and wait for clients to connect.   
                   # when a client performs an operation such as connect, or
                   # write a characteristic, call the function le_callback()
                   # Call LE_TIMER in le_callback every 100 deci-seconds (10 seconds)
btfpy.Close_all()