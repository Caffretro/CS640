#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
import random
import time

class Delay_pkt(object):
    def __init__(self, pkt, arrival, delay):
        self.pkt = pkt
        self.arrival = arrival
        self.delay = delay

def drop(percent):
    return random.randrange(100) < percent

def delay(mean, std):
    delay =random.gauss(mean, std)
    return delay if delay > 0 else 0

def get_params(tag, line):
    parsedInput = line.split()
    tagIndex = parsedInput.index(tag)
    return parsedInput[tagIndex + 1]

def switchy_main(net):

    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]
    queue = []
    
    for intf in my_intf:
        if intf.name == 'middlebox-eth0':
            blaster_intf = intf
    for intf in my_intf:
        if intf.name == 'middlebox-eth1':
            blastee_intf = intf

    fp = open('middlebox_params.txt', 'r')
    if fp is not None:
        line = fp.readline()

    probability = int(get_params('-p', line))
    random.seed(int(get_params('-s', line)))
    mean = int(get_params('-dm', line))
    std = int(get_params('-dstd', line))
    recv_timeout = int(get_params('-r', line))

    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet(recv_timeout)
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet {}".format(pkt))
            if dev == "middlebox-eth1":
                log_debug("Received from blastee")
                '''
                Received ACK
                send directly to blaster. Not dropping ACK packets!
                net.send_packet("middlebox-eth0", pkt)
                '''
                pkt[0].src = blaster_intf.ethaddr
                pkt[0].dst = '10:00:00:00:00:01'
                net.send_packet(blaster_intf.name, pkt)
            elif dev == "middlebox-eth0":
                log_debug("Received from blaster")
                drop_packet = drop(probability)
                pkt_delay = delay(mean, std)
                if not drop_packet:
                    entry = Delay_pkt(pkt, timestamp, pkt_delay)
                    queue.append(entry)
            else:
                log_debug("Oops :))")
        
        for entry in queue:
            if entry.delay + entry.arrival <= time.time():
                entry.pkt[0].src = blastee_intf.ethaddr
                entry.pkt[0].dst = '20:00:00:00:00:01'
                # For debugging purpose
                #header_bytes = entry.pkt[3].to_bytes()
                #sequence_num = int.from_bytes(header_bytes[0:4], byteorder='big')
                net.send_packet('middlebox-eth1', entry.pkt)
                #print('sending packet ' + str(sequence_num))
                queue.remove(entry)

    net.shutdown()


