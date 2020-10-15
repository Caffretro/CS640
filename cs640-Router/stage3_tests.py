import struct

from dynamicroutingmessage import DynamicRoutingMessage
from ipaddress import IPv4Address
from switchyard.lib.userlib import *
from switchyard.lib.packet import *


def mk_dynamic_routing_packet(ethdst, advertised_prefix, advertised_mask,
                               next_hop):
    drm = DynamicRoutingMessage(advertised_prefix, advertised_mask, next_hop)
    Ethernet.add_next_header_class(EtherType.SLOW, DynamicRoutingMessage)
    pkt = Ethernet(src='00:00:22:22:44:44', dst=ethdst,
                   ethertype=EtherType.SLOW) + drm
    xbytes = pkt.to_bytes()
    p = Packet(raw=xbytes)
    return p

def mk_pkt(hwsrc, hwdst, ipsrc, ipdst, reply=False, ttl = 64):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=ttl)
    icmppkt = ICMP()
    if reply:
        icmppkt.icmptype = ICMPType.EchoReply
    else:
        icmppkt.icmptype = ICMPType.EchoRequest
    return ether + ippkt + icmppkt


def router_tests():
    s = TestScenario("Basic functionality testing for DynamicRoutingMessage")

    # Initialize switch with 3 ports.
    s.add_interface('router-eth0', '10:00:00:00:00:01', ipaddr = '192.168.1.1', netmask = '255.255.255.252')
    s.add_interface('router-eth1', '10:00:00:00:00:02', ipaddr = '10.10.0.1', netmask = '255.255.0.0')
    s.add_interface('router-eth2', '10:00:00:00:00:03', ipaddr = '172.16.42.1', netmask = '255.255.255.0')



    # TODO for students: Write your own test for the above mentioned comment. This is not a deliverable. But will help
    #  you test if your code is correct or not.

    # Test 1: checking the basic IPv4 package delivery function of router
    #   Testing if sending a packet to 172.16.42.4 arrives at router-eth0
    pkt = mk_pkt('10:00:00:00:00:03', '30:00:00:00:00:01', '192.168.1.1', '172.16.42.4')
    s.expect(PacketInputEvent("router-eth0", pkt), "IP packet to 172.16.42.2 should arrive on router-eth0 interface")
    #   Testing if router creates arp request for 172.16.42.4
    arp_request = create_ip_arp_request('10:00:00:00:00:03', '172.16.42.1', '172.16.42.4')
    s.expect(PacketOutputEvent("router-eth2", arp_request), "Router should send an ARP request to router-eth2 interface for sending packet to 172.16.42.4")
    #   Testing if router receives the correct response from router-eth2
    arp_reply = create_ip_arp_reply('30:00:00:00:00:01', '10:00:00:00:00:03', '172.16.42.4', '172.16.42.1')
    s.expect(PacketInputEvent("router-eth2", arp_reply), "Router should receive an ARP reply from router-eth2 interface after sending ARP request to router-eth2")
    #   Testing if packets can be forwarded to router-eth2
    pkt = mk_pkt('10:00:00:00:00:03', '30:00:00:00:00:01', '192.168.1.1', '172.16.42.4', ttl=63)
    s.expect(PacketOutputEvent("router-eth2", pkt), "IP packet should be forwarded to 172.16.42.4 through router-eth2 interface")

    
    # 1 Dynamic message received, new entry should be added
    drm_pkt = mk_dynamic_routing_packet('10:00:00:00:00:01',
                                        IPv4Address('172.0.0.0'),
                                        IPv4Address('255.255.0.0'),
                                        IPv4Address('192.168.1.2'))
    s.expect(PacketInputEvent("router-eth0", drm_pkt),
             "Dynamic routing message on eth0")
    # Test 2: checking if the new forwarding information can be correctly used for sending packets
    # DRM packet coming from interface router-eth0 with the pair: (172.0.0.0/16, 192.168.1.2), which is a new entry
    #   Testing if sending a packet to 172.0.1.17 arrives at router-eth1
    pkt = mk_pkt('10:00:00:00:00:02', '30:00:00:00:00:01', '10.10.0.1', '172.0.1.17')
    s.expect(PacketInputEvent("router-eth1", pkt), "IP packet to 172.0.1.17 should arrive on router-eth1 interface")
    #   Testing if router creates arp request for 172.0.1.17
    arp_request = create_ip_arp_request('10:00:00:00:00:01', '192.168.1.1', '192.168.1.2')
    s.expect(PacketOutputEvent("router-eth0", arp_request), "Router should send an ARP request to router-eth0 interface for sending packet to 172.0.1.17")
    #   Testing if router receives the correct response from router-eth0
    arp_reply = create_ip_arp_reply('30:00:00:00:00:01', '10:00:00:00:00:01', '192.168.1.2', '192.168.1.1')
    s.expect(PacketInputEvent("router-eth0", arp_reply), "Router should receive an ARP reply from router-eth0 interface after sending ARP request to router-eth0")
    #   Testing if packets can be forwarded to router-eth0
    pkt = mk_pkt('10:00:00:00:00:01', '30:00:00:00:00:01', '10.10.0.1', '172.0.1.17', ttl = 63)
    s.expect(PacketOutputEvent("router-eth0", pkt), "IP packet should be forwarded to 172.0.1.17 through router-eth0 interface")
    # After the above dynamic routing packet has been received your forwarding table should get updated.
    # After this if another packet is received with its prefix in the same network as both static and dynamic routes,
    # the dynamic one gets chosen.
    
    # 2 Dynamic message received and table entry created above should be updated
    drm_pkt = mk_dynamic_routing_packet('10:00:00:00:00:03',
                                        IPv4Address('172.0.0.0'),
                                        IPv4Address('255.255.0.0'),
                                        IPv4Address('192.168.1.4'))
    s.expect(PacketInputEvent("router-eth2", drm_pkt),
             "Dynamic routing message on eth0")
    # Test 3: checking if the dynamic forwarding table entry has been correctly updated
    #   Testing if sending a packet to 172.0.1.17 arrives at router-eth1
    pkt = mk_pkt('10:00:00:00:00:02', '30:00:00:00:00:01', '10.10.0.1', '172.0.1.17')
    s.expect(PacketInputEvent("router-eth1", pkt), "IP packet to 172.0.1.17 should arrive on router-eth1 interface")
    #   Testing if router creates arp request for 172.0.1.17
    arp_request = create_ip_arp_request('10:00:00:00:00:03', '172.16.42.1', '192.168.1.4')
    s.expect(PacketOutputEvent("router-eth2", arp_request), "Router should send an ARP request to router-eth0 interface for sending packet to 172.0.1.17")
    #   Testing if router receives the correct response from router-eth2
    arp_reply = create_ip_arp_reply('30:00:00:00:00:01', '10:00:00:00:00:03', '192.168.1.4', '172.16.42.1')
    s.expect(PacketInputEvent("router-eth2", arp_reply), "Router should receive an ARP reply from router-eth0 interface after sending ARP request to router-eth0")
    #   Testing if packets can be forwarded to router-eth0
    pkt = mk_pkt('10:00:00:00:00:03', '30:00:00:00:00:01', '10.10.0.1', '172.0.1.17', ttl = 63)
    s.expect(PacketOutputEvent("router-eth2", pkt), "IP packet should be forwarded to 172.0.1.17 through router-eth0 interface")

    
    return s

scenario = router_tests()