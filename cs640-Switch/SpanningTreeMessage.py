import struct
from switchyard.lib.userlib import *


class SpanningTreeMessage(PacketHeaderBase):
    _PACKFMT = "6sxB6s"

    # switch_id is the id of the switch that forwarded the stp packet
    # in case the stp packet is generated ensure switch_id=root_id

    def __init__(self, root_id="00:00:00:00:00:00", hops_to_root=0, switch_id="00:00:00:00:00:00", **kwargs):
        self._root = EthAddr(root_id)
        self._hops_to_root = hops_to_root
        self._switch_id = EthAddr(switch_id)
        PacketHeaderBase.__init__(self, **kwargs)

    def to_bytes(self):
        raw = struct.pack(self._PACKFMT, self._root.raw, self._hops_to_root, self._switch_id.raw)
        return raw

    def from_bytes(self, raw):
        packsize = struct.calcsize(self._PACKFMT)
        if len(raw) < packsize:
            raise ValueError("Not enough bytes to unpack SpanningTreeMessage")
        xroot,xhops, xswitch = struct.unpack(self._PACKFMT, raw[:packsize])
        self._root = EthAddr(xroot)
        self.hops_to_root = xhops
        self._switch_id = EthAddr(xswitch)
        return raw[packsize:]

    @property
    def hops_to_root(self):
        return self._hops_to_root

    @hops_to_root.setter
    def hops_to_root(self, value):
        self._hops_to_root = int(value)

    @property
    def switch_id(self):
        return self._switch_id

    @switch_id.setter
    def switch_id(self, switch_id):
        self._switch_id = switch_id

    @property
    def root(self):
        return self._root

    def __str__(self):
        return "{} (root: {}, hops-to-root: {}, switch_id: {})".format(
            self.__class__.__name__, self.root, self.hops_to_root, self.switch_id)
