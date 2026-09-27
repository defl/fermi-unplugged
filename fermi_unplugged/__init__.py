"""Fermi Unplugged — Dirac Live protocol client for devices.

Usage:
    from fermi_unplugged import DiracDevice

    device = DiracDevice.discover()
    device.connect()
    slot = device.slot(0)
    slot.upload_passthrough(gain=0.5)
    slot.activate()
    device.filtering = True
"""

from fermi_unplugged.device import DiracDevice, FilterSlot

__version__ = "0.1.0"