#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time

from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *

class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here
        self.arp_table = {}
        self.my_interfaces = net.interfaces()

    def router_main(self):    
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''
        while True:
            gotpkt = True
            try:
                timestamp,dev,pkt = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            if gotpkt:
                log_debug("Got a packet: {}".format(str(pkt)))
                
                # obtain the ARP header if exists, ignore if pkt is not ARP
                if pkt.has_header(Arp):
                    arp = pkt.get_header(Arp)
                   
                    # if pkt is an ARP request
                    if arp.operation == ArpOperation.Request:
                        for interface in self.my_interfaces:
                             if interface.ipaddr == arp.targetprotoaddr:
                                # create and send ARP reply from target to the source
                                arp_reply = create_ip_arp_reply(interface.ethaddr, arp.senderhwaddr, arp.targetprotoaddr, arp.senderprotoaddr)
                                self.net.send_packet(dev, arp_reply)
                    
                    else:  # if pkt is an ARP reply
                        for interface in self.my_interfaces:
                            if interface.ipaddr == arp.targetprotoaddr:
                                self.arp_table[arp.senderprotoaddr] = arp.senderhwaddr
def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()
