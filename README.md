# Fermi Unplugged

[![CI](https://github.com/defl/fermi-unplugged/actions/workflows/ci.yml/badge.svg)](https://github.com/defl/fermi-unplugged/actions/workflows/ci.yml) [![License](https://img.shields.io/badge/license-GPL--3.0%20%2B%20Commons%20Clause-blue)](LICENSE.txt)

An unofficial Python client for the Dirac Live protocol on devices. It lets you
inspect a device's Dirac filter engine and load your own filters from
Python, over your local network.

> **Experimental.** This has only been tried on one Denon AVR-X3900H. It can
> overwrite your Dirac calibration and a bad filter can be loud. Read the
> [Disclaimer](DISCLAIMER.md) before pointing it at your device.

## Install

Install from GitHub:

```bash
pip install git+https://github.com/defl/fermi-unplugged
```

## Usage

```python
from fermi_unplugged import DiracDevice

# Discover the device on your network
device = DiracDevice.discover()
device.connect()
device.status()  # model, speakers, filter slots, filtering on/off

# Filter slots
for slot in device.slots:
    print(slot.index, slot.name or "empty", "(active)" if slot.is_active else "")

# Write a -6 dB pass-through filter into slot 2, switch to it, and turn
# filtering on
slot = device.slot(2)
slot.upload_passthrough(gain=0.5)
slot.activate()
device.filtering = True

# Low-level gRPC access
info = device.client.call("GetDeviceInfo")
print(f"{info.manufacturer} {info.model_name}, {info.num_speakers} speakers")
```

## How It Works

As far as we can tell from the one device tested:

1. **SSDP discovery** finds the gRPC port (`X_port`) and REST endpoint
   (`X_rest_api`) the device advertises over UPnP.
2. **gRPC upload** sends the filter in this sequence:
   `BeginFilterTransfer` → cells → `SetFilterCommon` → `EndFilterTransfer` →
   `UpdateSlotInfo` → `SetActiveSlot`.
3. **REST** `PUT /api/filtering?enabled=1` turns filtering on. On the X3900H
   the filter survived a reboot after this sequence.

## Filter Format

What the X3900H reported and accepted:

- A 10-input × 10-output matrix of filter cells.
- Each cell is a multi-rate FIR (MRFIR) with 4 layers: layer 0 is 256 taps at
  48 kHz, layers 1–3 are 256 taps each at decimated rates (low frequencies only).
- Cross-feed cells (input ≠ output) use only the low-frequency layers.

## Disclaimer

Use at your own risk — see [DISCLAIMER.md](DISCLAIMER.md).

## License

GPL-3.0 with the Commons Clause — see [LICENSE.txt](LICENSE.txt).
