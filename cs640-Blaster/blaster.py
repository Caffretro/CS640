#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from random import randint
import time

class Entry(object):
    def __init__(self, seq, time):
        self.seq = seq
        self.time = time
        self.ack = False

def print_output(total_time, num_ret, num_tos, throughput, goodput,  estRTT, TO, min_rtt, max_rtt):
    print("Total TX time (s): " + str(total_time))
    print("Number of reTX: " + str(num_ret))
    print("Number of coarse TOs: " + str(num_tos))
    print("Throughput (Bps): " + str(throughput))
    print("Goodput (Bps): " + str(goodput))
    print("Final estRTT(ms): " + str(estRTT))
    print("Final TO(ms): " + str(TO))
    print("Min RTT(ms):" + str(int(min_rtt)))
    print("Max RTT(ms):" + str(int(max_rtt)))

def get_params(tag, line):
    parsedInput = line.split()
    tagIndex = parsedInput.index(tag)
    return parsedInput[tagIndex + 1]

def send_ack(net, intf, sequence, l):
    pkt = Ethernet() + IPv4() + UDP()

    pkt[0].src = intf.ethaddr
    pkt[0].dst = '40:00:00:00:00:01'

    pkt[1].src = intf.ipaddr
    pkt[1].dst = '192.168.200.1'
    pkt[1].protocol = IPProtocol.UDP

    pkt[2].src = 4444
    pkt[2].dst = 5555

    pkt += RawPacketContents(sequence.to_bytes(4, byteorder='big') + l.to_bytes(2, byteorder='big'))

    for i in range(l):
        pkt += RawPacketContents(bytes(randint(0, l)))

    net.send_packet(intf.name, pkt)

def switchy_main(net):
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]

    fp = open('blaster_params.txt', 'r')
    if fp is not None:
        line = fp.readline()

    LHS = 1
    RHS = 1
    SW = []
    start_time = None
    last_ack_time = None
    num_ret = 0
    num_tos = 0
    total_payload = 0
    total_good_payload = 0

    num_pkts = int(get_params('-n', line))
    payload_len = int(get_params('-l', line))
    sender_window = int(get_params('-w', line))
    RTT = int(get_params('-rtt', line))
    recv_timeout = int(get_params('-r', line)) / 1000
    alpha = float(get_params('-alpha', line))
    
    estRTT = RTT
    TO = 2 * estRTT
    # Set min and max RTT as infinity and 0
    minRTT = float("inf")
    maxRTT = 0

    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet(timeout=recv_timeout)
        except NoPackets:
            log_debug('No packets available in recv_packet')
            gotpkt = False
        except Shutdown:
            log_debug('Got shutdown signal')
            break

        if start_time is None:
            start_time = time.time()

        if gotpkt:
            log_debug("I got a packet")
            '''
            Extracting information from pkt
            '''
            header_bytes = pkt[3].to_bytes()
            sequence_num = int.from_bytes(header_bytes[0:4], byteorder='big')
            #print(str(sequence_num) + ' received\n')

            if sequence_num >= LHS and sequence_num < RHS:
                SW[sequence_num - LHS].ack = True
                for entry in list(SW):
                    if entry.ack:
                        pkt_RTT = (time.time() - entry.time) * 1000
                        if(pkt_RTT < minRTT):
                            minRTT = pkt_RTT
                        if(pkt_RTT > maxRTT):
                            maxRTT = pkt_RTT
                        SW.remove(entry)
                        LHS += 1
                    else:
                        break
                # break and set the last ack time
                last_ack_time = time.time()
        else:
            if RHS - LHS < sender_window and RHS <= num_pkts:
                # print('append ' + str(entry.seq) + ' to window\n')
                SW.append(Entry(RHS, time.time()))
                l = randint(0, payload_len)
                send_ack(net, my_intf[0], RHS, l)
                RHS += 1
                total_payload += l
                total_good_payload += l
            else:
                for entry in SW:
                    if not entry.ack:
                        if time.time() - entry.time > TO / 1000:
                            #print('retransmit' + str(entry.seq) +'\n')
                            pkt_RTT = (time.time() - entry.time) * 1000
                            if(pkt_RTT < minRTT):
                                minRTT = pkt_RTT
                            if(pkt_RTT > maxRTT):
                                maxRTT = pkt_RTT
                            estRTT = (1 - alpha) * estRTT + alpha * pkt_RTT
                            TO = 2 * estRTT

                            entry.time = time.time()
                            l = randint(0, payload_len)
                            send_ack(net, my_intf[0], entry.seq, l)
                            num_ret += 1
                            num_tos += 1
                            total_payload += l
                            break
        
        if LHS > num_pkts:
            #print('break here\n')
            break

    if last_ack_time is not None:
        total_time = last_ack_time - start_time
        total_throughput = total_payload / total_time
        good_throughput = total_good_payload / total_time
        print_output(total_time, num_ret, num_tos, total_throughput, good_throughput, estRTT, TO, minRTT, maxRTT)

    net.shutdown()
