'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
from switchyard.lib.userlib import *

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    hostList = []
    portList = []

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))

        if packet[0].src in hostList:
            idx = hostList.index(packet[0].src)
            del hostList[idx]
            del portList[idx]
        hostList.insert(0, packet[0].src)
        portList.insert(0, input_port)
        hostList = hostList[0:5]
        portList = portList[0:5]

        if packet[0].dst in mymacs:
            log_debug ("Packet intended for me")
        elif packet[0].dst == "FF:FF:FF:FF:FF:FF" or packet[0].dst not in hostList:
            for intf in my_interfaces:
                if input_port != intf.name:
                    log_debug ("Flooding packet {} to {}".format(packet, intf.name))
                    net.send_packet(intf.name, packet)
        else:
            idx = hostList.index(packet[0].dst)
            newHost = hostList[idx]
            newPort = portList[idx]
            del hostList[idx]
            del portList[idx]
            hostList.insert(0, newHost)
            portList.insert(0, newPort)
            log_debug ("Flooding packet {} to {}".format(packet, newPort))
            net.send_packet(newPort, packet)
    net.shutdown()
