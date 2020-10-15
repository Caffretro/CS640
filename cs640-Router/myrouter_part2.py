#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time

from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *
from switchyard.lib.address import *

class ForwardingTableEntry(object):
    def __init__(self, network=None, next_hop=None, intf_name=None):
        self.network = network
        self.next_hop = next_hop
        self.intf_name = intf_name

class WaitingPacket(object):
    '''
    Object that contains info about IP packets awaiting ARP resolution
    '''
    def __init__(self, dst_entry=None, next_ip_addr=None, pkt=None):
        self.dst_entry = dst_entry
        self.next_ip_addr = next_ip_addr
        self.pkt = pkt
        self.timestamp = None
        self.ttl = 3

class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here
        self.arp_table = {}
        self.my_interfaces = net.interfaces()
        self.forwarding_table = []
        self.queue = []
        
        # establishing forwarding table using .txt file and itself
        for interface in self.my_interfaces: 
            # pdf switchyard doc p.46
            entry = ForwardingTableEntry(IPv4Network(str(interface.ipaddr) + "/" + str(interface.netmask), False), None, interface.name)
            self.forwarding_table.append(entry)
        fp = open('forwarding_table.txt', 'r')
        if fp is not None:
            for line in fp:
                info = line.split()
                entry = ForwardingTableEntry(IPv4Network(info[0] + '/' + info[1]), IPv4Address(info[2]), info[3])
                self.forwarding_table.append(entry)
            fp.close()

    def get_longest_prefix(self, ip):
        '''
        Checks the longest prefix matched entry in forwarding table
        '''
        entries = []
        for entry in self.forwarding_table:
            if ip in entry.network:
                entries.append(entry)
        # longest prefixlen match is applied, sort in correct order
        entries.sort(key=lambda x: x.network.prefixlen, reverse=True)
        if not entries:
            return None
        else:
            return entries[0]

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

                # start receiving IP packets
                if pkt.has_header(IPv4):
                    ipv4 = pkt.get_header(IPv4)
                    ipv4.ttl = ipv4.ttl - 1
                    # drop the packet if ttl <= 0
                    if ipv4.ttl <= 0:
                        continue

                    # get longest prefix matched dst addr 
                    dst_entry = self.get_longest_prefix(ipv4.dst)
                    
                    # if pkt has no match, drop it
                    if dst_entry is None:
                        continue

                    dst_is_router = False
                    for interface in self.my_interfaces:
                        if ipv4.dst == interface.ipaddr:
                             dst_is_router = True
                    # if pkt is for the router itself, drop pkt
                    if dst_is_router:
                        continue

                    dst_ether_addr = None
                    next_ip_addr = None
                    if dst_entry.next_hop is None:
                        if ipv4.dst in self.arp_table:
                            dst_ether_addr = self.arp_table[ipv4.dst]
                        else:
                            next_ip_addr = ipv4.dst
                    else:
                        if dst_entry.next_hop in self.arp_table:
                            dst_ether_addr = self.arp_table[dst_entry.next_hop]
                        else:
                            next_ip_addr = dst_entry.next_hop
                
                    if next_ip_addr is not None:
                        # add an item to queue
                        waiting_pkt = WaitingPacket(dst_entry, next_ip_addr, pkt)
                        self.queue.append(waiting_pkt)
                    else:
                        for interface in self.my_interfaces:
                            if interface.name == dst_entry.intf_name:
                                next = pkt
                                next[0].src = interface.ethaddr
                                next[0].dst = dst_ether_addr
                                self.net.send_packet(dst_entry.intf_name, next)
                    
            # process queued waiting packets
            for wp in self.queue:
                if wp.next_ip_addr in self.arp_table:
                    for interface in self.my_interfaces:
                        if interface.name == wp.dst_entry.intf_name:
                            next = wp.pkt
                            next[0].src = interface.ethaddr
                            next[0].dst = self.arp_table[wp.next_ip_addr]
                            self.net.send_packet(dst_entry.intf_name, next)

                # If no ARP reply is received after 3 requests, give up and drop the packet.
                elif wp.ttl <= 0: 
                    continue
            
                # If no ARP reply is received within 1 second in response to an ARP request, 
                # send another ARP request.
                elif wp.timestamp is None or time.time() - wp.timestamp > 1:
                    wp.timestamp = time.time()
                    wp.ttl -= 1
                    for interface in self.my_interfaces:
                        if wp.dst_entry.intf_name == interface.name:
                            arp_request = create_ip_arp_request(interface.ethaddr, interface.ipaddr, wp.next_ip_addr)
                            self.net.send_packet(interface.name, arp_request)
            # remove the wps being processed
            for wp in self.queue:
                if wp.next_ip_addr in self.arp_table:
                    self.queue.remove(wp)

                            

def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()
