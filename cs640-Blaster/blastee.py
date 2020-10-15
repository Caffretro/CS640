#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import time

def switchy_main(net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]

    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet from {}".format(dev))
            log_debug("Pkt: {}".format(pkt))
            '''
            Extracting information from pkt
            '''
            header_bytes = pkt[3].to_bytes()
            sequence_num = int.from_bytes(header_bytes[0:4], byteorder='big')
            length = int.from_bytes(header_bytes[4:6], byteorder='big')
            payload = header_bytes[6:length] + bytes(max(0, 8 - length))
            '''
            Creating the headers for the packet and send
            '''
            pkt = Ethernet() + IPv4() + UDP()
            pkt[1].protocol = IPProtocol.UDP
            pkt[2].src = 4444
            pkt[2].dst = 5555
            pkt[0].src = my_interfaces[0].ethaddr
            pkt[0].dst = '40:00:00:00:00:01'
            pkt[1].src = my_interfaces[0].ipaddr
            pkt[1].dst = '192.168.100.1'
            pkt = pkt + RawPacketContents(sequence_num.to_bytes(4, byteorder='big')) + RawPacketContents(payload)
            net.send_packet(my_interfaces[0].name, pkt)

    net.shutdown()

