"""DiracDevice — OO interface for Dirac-enabled devices."""
import re
import select
import socket
import time
import urllib.request
import uuid

import numpy as np

from fermi_unplugged.client import EndpointClient, msg
from fermi_unplugged.rest import DiracRest

DIAG_VARIANT = {32000: 0, 44100: 2, 48000: 4}


def _local_ipv4_addresses():
    """This machine's IPv4 addresses, excluding loopback."""
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        infos = []
    addrs = sorted({i[4][0] for i in infos} - {"127.0.0.1"})
    return addrs or ["0.0.0.0"]


class DiracDevice:
    """A Dirac-capable device discovered via SSDP.

    Usage:
        device = DiracDevice.discover()
        device.connect()
        slot = device.slot(0)
        slot.upload_passthrough(gain=0.5)
        slot.activate()
        device.filtering = True
    """

    def __init__(self, ip, grpc_port, rest_port=8090,
                 friendly_name="", manufacturer="", model="", uuid_str="",
                 upnp_port=0, capabilities=""):
        self.ip = ip
        self.grpc_port = grpc_port
        self.rest_port = rest_port
        self.friendly_name = friendly_name
        self.manufacturer = manufacturer
        self.model = model
        self.uuid = uuid_str
        self.upnp_port = upnp_port
        self.capabilities = capabilities
        self._client = None
        self._rest = DiracRest(ip, rest_port)

    # ── discovery ──────────────────────────────────────────────

    @staticmethod
    def discover(timeout=10.0):
        """Find a Dirac device on the network via SSDP."""
        msg_str = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 4\r\n"
            "ST: upnp:rootdevice\r\n\r\n"
        )
        # Search from every local IPv4 address: multicast leaves through a
        # single interface, which may not be the one the device is on.
        socks = []
        for addr in _local_ipv4_addresses():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                         socket.inet_aton(addr))
            try:
                s.bind((addr, 0))
                s.sendto(msg_str.encode(), ("239.255.255.250", 1900))
            except OSError:
                s.close()
                continue
            socks.append(s)

        seen = set()
        deadline = time.time() + timeout
        try:
            while socks and time.time() < deadline:
                ready, _, _ = select.select(socks, [], [], 1.0)
                for s in ready:
                    data, addr = s.recvfrom(65535)
                    hdr = {}
                    for line in data.decode(errors="replace").split("\r\n")[1:]:
                        if ":" in line:
                            k, v = line.split(":", 1)
                            hdr[k.strip().upper()] = v.strip()
                    loc = hdr.get("LOCATION", "")
                    if loc and loc not in seen:
                        seen.add(loc)
                        device = DiracDevice._from_upnp(addr[0], loc)
                        if device:
                            return device
        finally:
            for s in socks:
                s.close()
        return None

    @staticmethod
    def _from_upnp(ip, location_url, timeout=5.0):
        try:
            r = urllib.request.urlopen(location_url, timeout=timeout)
            xml = r.read().decode(errors="replace")
        except Exception:
            return None
        if "diracns:X_port" not in xml:
            return None

        def tag(name):
            m = re.search(rf"<{name}>(.+?)</{name}>", xml, re.DOTALL)
            return m.group(1).strip() if m else ""

        m = re.match(r"http://[\d.]+:(\d+)", location_url)
        upnp_port = int(m.group(1)) if m else 0

        return DiracDevice(
            ip=ip,
            grpc_port=int(tag(r"diracns:X_port")),
            rest_port=int(tag(r"diracns:X_rest_api") or "8090"),
            friendly_name=tag("friendlyName"),
            manufacturer=tag("manufacturer"),
            model=tag("modelName"),
            uuid_str=tag("UDN"),
            upnp_port=upnp_port,
            capabilities=tag(r"diracns:X_type"),
        )

    # ── connection ─────────────────────────────────────────────

    def connect(self):
        """Open the gRPC channel to the device."""
        self._client = EndpointClient(f"{self.ip}:{self.grpc_port}")
        return self

    # ── slots ──────────────────────────────────────────────────

    @property
    def slots(self):
        """All filter slots on the device."""
        n = self.client.call("GetDeviceInfo").num_filter_slots
        return [FilterSlot(self, i) for i in range(n)]

    def slot(self, index):
        """The filter slot at `index`."""
        n = self.client.call("GetDeviceInfo").num_filter_slots
        if not 0 <= index < n:
            raise IndexError(f"slot {index} out of range; device has {n} slots")
        return FilterSlot(self, index)

    @property
    def active_slot(self):
        """The slot currently in use, or None when no slot is active."""
        i = self.client.call("GetActiveSlot").i
        return FilterSlot(self, i) if i >= 0 else None

    # ── filtering ──────────────────────────────────────────────

    @property
    def filtering(self):
        """Whether Dirac filtering is on."""
        return self.rest.filtering_enabled

    @filtering.setter
    def filtering(self, on):
        if on:
            self.rest.enable_filtering()
        else:
            self.rest.disable_filtering()

    # ── status ─────────────────────────────────────────────────

    def status(self):
        """Print current device and filter state."""
        di = self.client.call("GetDeviceInfo")
        print(f"{di.manufacturer} {di.model_name}")
        print(f"  uuid={di.unique_device_identifier}")
        print(f"  speakers={di.num_speakers}  slots={di.num_filter_slots}")

        active = self.active_slot
        print(f"  active slot: {active.index if active else 'none'}")

        for slot in self.slots:
            si = slot.info
            if si.name:
                print(f"  slot {slot.index}: {si.name!r}  {si.num_inputs}x{si.num_outputs}"
                      f"x{si.num_sections}  type={si.filter_type_name!r}")
            else:
                print(f"  slot {slot.index}: empty")

        print(f"  filtering: {'on' if self.filtering else 'off'}")

    @property
    def client(self):
        if self._client is None:
            self.connect()
        return self._client

    @property
    def rest(self):
        return self._rest


class FilterSlot:
    """One filter slot on a DiracDevice. Get it from `device.slot(i)`,
    `device.slots` or `device.active_slot`."""

    def __init__(self, device, index):
        self.device = device
        self.index = index

    def __repr__(self):
        return f"FilterSlot({self.index})"

    def __eq__(self, other):
        return (isinstance(other, FilterSlot) and other.device is self.device
                and other.index == self.index)

    @property
    def _client(self):
        return self.device.client

    @property
    def info(self):
        """The slot's SlotInfo, read from the device."""
        return self._client.call("GetSlotInfo", msg("Index", i=self.index))

    @property
    def name(self):
        return self.info.name

    @property
    def is_empty(self):
        return not self.info.name

    @property
    def is_active(self):
        return self._client.call("GetActiveSlot").i == self.index

    def activate(self):
        """Make this the slot the device filters with."""
        self._client.call("SetActiveSlot", msg("Index", i=self.index))
        return self

    def delete(self):
        """Delete the filter in this slot."""
        self._client.call("DeleteSlot", msg("Index", i=self.index))
        return self

    def upload_passthrough(self, gain=0.5, rate=48000, name="fermi-passthrough"):
        """Write a pass-through filter at `gain` into this slot, replacing
        what is there."""
        client = self._client
        di = client.call("GetDeviceInfo")
        variant = DIAG_VARIANT[rate]

        # Build MRFIR filter
        info = client.call("GetFilterInfo",
                           msg("FilterInfoQuery", variant=variant, type=6)).mrfir
        layers = []
        for n, li in enumerate(info.layers):
            taps = [0.0] * li.num_fir_taps
            if n == 0 and taps:
                taps[0] = gain
            layers.append(msg("MRFIRLayer", fir=msg("FIR", fir_taps=taps), bulk_delay=0))
        cell_filter = msg("MRFIR", info=info, layers=layers)

        # Build resample anti-alias FIRs
        rinfo = client.call("GetFilterInfo",
                            msg("FilterInfoQuery", variant=0, type=7)).resample
        stages = []
        for st in rinfo.stages:
            n = np.arange(st.num_fir_taps) - (st.num_fir_taps - 1) / 2
            fc = 0.9 / (2 * st.factor)
            h = 2 * fc * np.sinc(2 * fc * n) * np.blackman(st.num_fir_taps)
            h /= h.sum()
            stages.append(msg("ResampleStage", factor=st.factor,
                              fir=msg("FIR", fir_taps=h.tolist())))
        resample = msg("FilterCommon",
                       resample=msg("ResampleCoeffsCommon", variant=rinfo.variant,
                                    type=rinfo.type, stages=stages))

        cells = [msg("FilterCell", input_idx=i, output_idx=i, mrfir=cell_filter)
                 for i in range(di.num_speakers)]

        u = uuid.uuid4().int
        slot_info = msg(
            "SlotInfo", slot_index=self.index, name=name,
            filter_type_name="Dirac Live",
            description=f"Pass-through, gain={gain} ({20*np.log10(gain):.1f} dB)",
            num_inputs=di.num_speakers, num_outputs=di.num_speakers,
            num_sections=1,
            unique_id=msg("UUID", low=u & (2**64 - 1), high=u >> 64),
            slot_metadata=msg("SlotMetadata",
                              endpoint_manufacturer=di.manufacturer,
                              endpoint_model=di.model_name),
        )

        # gRPC upload sequence
        client.call("BeginFilterTransfer", slot_info)
        for c in cells:
            client.call("SetTransferCell", msg(
                "CellIndex", input_idx=c.input_idx,
                output_idx=c.output_idx, section_idx=0))
            client.call("SetFilterCell", c)
        client.call("SetFilterCommon", resample)
        for _ in client.call("EndFilterTransfer",
                             msg("Index", i=self.index), timeout=60):
            pass
        client.call("UpdateSlotInfo", msg(
            "SlotInfoUpdate", slot_index=self.index, name=name,
            filter_type_name="Dirac Live",
            description=f"Pass-through, gain={gain}"))
        return self
