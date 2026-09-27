"""Mock gRPC handlers for testing DiracDevice without a real device.

Patches EndpointClient.call() to return canned responses matching the
X3900H's actual behavior.
"""
from unittest.mock import MagicMock


def mock_device_client(num_speakers=10, num_slots=3, active_slot=-1,
                       slot_names=None, filtering_enabled=True):
    """Create a DiracDevice with a mocked EndpointClient and DiracRest.

    Returns (device, mock_call) where mock_call is the MagicMock for
    client.call() — you can assert on it.
    """
    from fermi_unplugged.device import DiracDevice
    from fermi_unplugged.client import msg as _msg

    device = DiracDevice(
        ip="127.0.0.1",
        grpc_port=9999,
        friendly_name="Test device",
        manufacturer="Mock",
        model="X3900H-TEST",
    )

    # Create patched client
    mock_client = MagicMock()
    mock_client.host = "127.0.0.1:9999"
    mock_client.ip = "127.0.0.1"
    mock_call = MagicMock()
    mock_client.call = mock_call

    # Canned responses
    def canned_call(method, request=None, timeout=10):
        # Build response objects inline using msg()
        if method == "GetDeviceInfo":
            r = _msg("DeviceInfo")
            r.manufacturer = "Mock"
            r.model_name = "X3900H-TEST"
            r.num_speakers = num_speakers
            r.num_filter_slots = num_slots
            r.unique_device_identifier = "test-uuid"
            return r
        elif method == "GetActiveSlot":
            r = _msg("Index")
            r.i = active_slot
            return r
        elif method == "GetSlotInfo":
            idx = request.i if request else 0
            r = _msg("SlotInfo")
            if slot_names and idx < len(slot_names) and slot_names[idx]:
                r.name = slot_names[idx]
                r.num_inputs = num_speakers
                r.num_outputs = num_speakers
                r.num_sections = 1
                r.creation_time = 1
                r.filter_type_name = "Dirac Live"
            else:
                r.num_inputs = num_speakers
                r.num_outputs = num_speakers
                r.num_sections = 1
            return r
        elif method == "GetFilterInfo":
            # Return MRFIR info (type=6) or Resample info (type=7)
            r = _msg("FilterInfo")
            if request and request.type == 6:  # MRFIR
                r.mrfir.variant = request.variant
                r.mrfir.samplerate = 48000
                for _ in range(4):
                    layer = r.mrfir.layers.add()
                    layer.num_fir_taps = 256
                    layer.max_bulk_delay = 1104
            elif request and request.type == 7:  # Resample
                r.resample.variant = 0
                r.resample.type = 2  # FIR
                stage = r.resample.stages.add()
                stage.factor = 2
                stage.num_fir_taps = 33
            return r
        elif method == "EndFilterTransfer":
            # Server stream — return list of Progress messages
            r1 = _msg("Progress"); r1.progress = 0.33
            r2 = _msg("Progress"); r2.progress = 0.66
            r3 = _msg("Progress"); r3.progress = 1.0
            return [r1, r2, r3]
        else:
            # Most write methods return Void
            return _msg("Void")

    mock_call.side_effect = canned_call

    device._client = mock_client

    # Also mock the REST client
    rest_mock = MagicMock()
    rest_mock.filtering_enabled = filtering_enabled
    device._rest = rest_mock

    return device, mock_call, rest_mock