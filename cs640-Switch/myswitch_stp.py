'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
from switchyard.lib.userlib import *
import datetime
from SpanningTreeMessage import SpanningTreeMessage

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    hostList = []
    portList = []
    blockList = []

    two_sec = datetime.timedelta(days=0,seconds=2,microseconds=0,milliseconds=0,minutes=0,hours=0,weeks=0)
    ten_sec = datetime.timedelta(days=0,seconds=10,microseconds=0,milliseconds=0,minutes=0,hours=0,weeks=0)
    
    #TODO: change the initialized values
    switch_id = min(mymacs)
    root_id = switch_id
    root_switch_id = switch_id
    root_interface = None #my_interfaces[mymacs.index(min(mymacs))].name
    last_stp_time = datetime.datetime.now()
    num_hops = 0

    spm = SpanningTreeMessage(root_id, num_hops, switch_id)
    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
    pkt = Ethernet(src=switch_id, dst='ff:ff:ff:ff:ff:ff', ethertype=EtherType.SLOW) + spm
    last_stp_time = datetime.datetime.now()
    for intf in my_interfaces:
        log_debug ("Flooding packet {} to {}".format(pkt, intf.name))
        net.send_packet(intf.name, pkt)

    while True:
        # re-initialize switch
        if root_id != switch_id and datetime.datetime.now() - last_stp_time > ten_sec:
            root_id = switch_id
            num_hops = 0
            blockList = []

        #generate the root stp message
        if root_id == switch_id and datetime.datetime.now() - last_stp_time > two_sec:
            spm = SpanningTreeMessage(root_id, num_hops, switch_id)
            Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
            pkt = Ethernet(src=switch_id, dst='ff:ff:ff:ff:ff:ff', ethertype=EtherType.SLOW) + spm
            last_stp_time = datetime.datetime.now()
            for intf in my_interfaces:
                log_debug ("Flooding packet {} to {}".format(pkt, intf.name))
                net.send_packet(intf.name, pkt)



        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))

        # has header (spanningtreemessage) ?
        if packet[0].ethertype == EtherType.SLOW:

            # incoming interface == root interface
            if input_port == root_interface:
                root_id = packet[SpanningTreeMessage].root
                num_hops = packet[SpanningTreeMessage].hops_to_root + 1
                root_switch_id = packet[SpanningTreeMessage].switch_id
                last_stp_time = datetime.datetime.now()
                spm = SpanningTreeMessage(root_id, num_hops, switch_id)
                Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
                pkt = Ethernet(src=switch_id, dst='ff:ff:ff:ff:ff:ff', ethertype=EtherType.SLOW) + spm
                last_stp_time = datetime.datetime.now()
                for intf in my_interfaces:
                    if input_port != intf.name:
                        log_debug ("Flooding packet {} to {}".format(pkt, intf.name))
                        net.send_packet(intf.name, pkt)

            elif packet[SpanningTreeMessage].root < root_id:
                root_id = packet[SpanningTreeMessage].root
                num_hops = packet[SpanningTreeMessage].hops_to_root + 1
                root_switch_id = packet[SpanningTreeMessage].switch_id
                last_stp_time = datetime.datetime.now()

                blockList = []

                spm = SpanningTreeMessage(root_id, num_hops, switch_id)
                Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
                pkt = Ethernet(src=switch_id, dst='ff:ff:ff:ff:ff:ff', ethertype=EtherType.SLOW) + spm
                last_stp_time = datetime.datetime.now()
                for intf in my_interfaces:
                    if input_port != intf.name:
                        log_debug ("Flooding packet {} to {}".format(pkt, intf.name))
                        net.send_packet(intf.name, pkt)

            elif packet[SpanningTreeMessage].root > root_id:
                if input_port in blockList:
                    blockList.remove(input_port)
                    continue


            else:
                if packet[SpanningTreeMessage].hops_to_root + 1 > num_hops:
                    continue
                elif (packet[SpanningTreeMessage].hops_to_root + 1 < num_hops) or (packet[SpanningTreeMessage].hops_to_root + 1 == num_hops and root_switch_id > packet[SpanningTreeMessage].switch_id):
                    if input_port in blockList:
                        blockList.remove(input_port)

                    if root_interface not in blockList:
                        blockList.append(root_interface)

                    num_hops = packet[SpanningTreeMessage].hops_to_root + 1
                    root_id = packet[SpanningTreeMessage].root
                    root_switch_id = packet[SpanningTreeMessage].switch_id
                    root_interface = input_port

                    spm = SpanningTreeMessage(root_id, num_hops, switch_id)
                    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
                    pkt = Ethernet(src=switch_id, dst='ff:ff:ff:ff:ff:ff', ethertype=EtherType.SLOW) + spm
                    last_stp_time = datetime.datetime.now()
                    for intf in my_interfaces:
                        if input_port != intf.name:
                            log_debug ("Flooding packet {} to {}".format(pkt, intf.name))
                            net.send_packet(intf.name, pkt)

                else:
                    if input_port not in blockList:
                        blockList.append(input_port)
                        continue

        else:
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
            elif packet[0].dst == 'FF:FF:FF:FF:FF:FF':
                for intf in my_interfaces:
                    if input_port != intf.name and intf.name not in blockList:
                        log_debug ("Flooding packet {} to {}".format(packet, intf.name))
                        net.send_packet(intf.name, packet)


            elif packet[0].dst not in hostList:
                for intf in my_interfaces:
                    if input_port != intf.name and intf.name not in blockList:
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
