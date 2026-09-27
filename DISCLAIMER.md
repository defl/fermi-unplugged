# Legal Disclaimer

## No Warranty — Absolutely None

**THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED.** There is no guarantee that this software works correctly, does what
it claims to do, or is safe to use. The authors make no representations about
the accuracy, reliability, completeness, or timeliness of the software or of
anything written about the protocol in this repository.

**Use entirely at your own risk.** The authors are not responsible for any
damage to your device, speakers, amplifiers, hearing, or data. This includes
but is not limited to:

- A malformed or badly scaled filter producing loud, distorted or full-scale
  output that damages speakers, amplifiers or hearing. Start at low volume and
  with a conservative gain.
- Overwriting an existing Dirac Live calibration in a filter slot. Uploading
  replaces whatever is in the target slot, and persisting it commits the
  change to the device's flash. Keep your Dirac Live project so you can
  re-send the original calibration.
- A device left in a state that needs a factory reset, a firmware reflash, or
  service to recover
- Voiding your device's warranty or breaching the terms of the software it
  runs
- Any other direct, indirect, incidental, or consequential damages

## Intended Use

This project is intended for **people who own a Dirac-capable device** and 
who want to talk to it from their own code.

It is **not** intended for, and cannot work in a way to, obtain Dirac Live 
features, licences or upgrades (such as Bass Control or ART).

## Interoperability

This project exists to let owners of a Dirac-capable device talk to hardware
they own from their own software. The authors believe this is lawful
interoperability under DMCA Section 1201(f) (US) and EU Software Directive
Article 6.

**This project does not include, redistribute, or modify any Dirac code or
binaries**, and it does not contain or bypass any Dirac licence key, signing
key or copy-protection mechanism.

## Trademarks

- "Dirac", "Dirac Live" and "Dirac ART" are trademarks of Dirac Research AB.
- This project is not affiliated with, endorsed by, or sponsored by any of
  these companies. The names are used only to identify the software and
  equipment this project interoperates with.

## Privacy

- This library talks only to devices on your local network: SSDP multicast for
  discovery, then gRPC and the device's REST API (port 8090) on the device
  it finds. It makes no requests to the internet and sends nothing to Dirac,
  the device manufacturer or the authors.
- The device's gRPC and REST interfaces are unauthenticated. Anything on
  your network can use them the same way this library does — that is a
  property of the device, not something this project adds.
