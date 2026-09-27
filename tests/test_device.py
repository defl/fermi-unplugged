"""Unit tests for DiracDevice — mock server, no real device needed."""
import pytest
from fermi_unplugged.device import DiracDevice
from tests.mock_server import mock_device_client


class TestDiscovery:
    def test_manual_construction(self):
        device = DiracDevice(ip="10.0.0.1", grpc_port=12345)
        assert device.ip == "10.0.0.1"
        assert device.grpc_port == 12345
        assert device.rest_port == 8090

    def test_repr(self):
        device = DiracDevice(ip="10.0.0.1", grpc_port=9999,
                             friendly_name="Test", manufacturer="Mock")
        assert device.friendly_name == "Test"
        assert device.manufacturer == "Mock"


class TestClientConnection:
    def test_connect_sets_client(self):
        device, call, _ = mock_device_client()
        assert device.client is not None
        assert device._client is not None

    def test_get_device_info(self):
        device, call, _ = mock_device_client()
        call.assert_not_called()  # not called until we use it
        di = device.client.call("GetDeviceInfo")
        assert di.manufacturer == "Mock"
        assert di.num_speakers == 10

    def test_get_active_slot(self):
        device, call, _ = mock_device_client(active_slot=-1)
        r = device.client.call("GetActiveSlot")
        assert r.i == -1


class TestStatus:
    def test_status_empty(self, capsys):
        device, call, _ = mock_device_client(active_slot=-1)
        device.status()
        captured = capsys.readouterr()
        assert "Mock X3900H-TEST" in captured.out
        assert "active slot: none" in captured.out
        assert "empty" in captured.out


class TestSlots:
    def test_slots_lists_every_slot(self):
        device, _, _ = mock_device_client(num_slots=3)
        assert [s.index for s in device.slots] == [0, 1, 2]

    def test_slot_out_of_range(self):
        device, _, _ = mock_device_client(num_slots=3)
        with pytest.raises(IndexError):
            device.slot(3)
        with pytest.raises(IndexError):
            device.slot(-1)

    def test_active_slot_none(self):
        device, _, _ = mock_device_client(active_slot=-1)
        assert device.active_slot is None

    def test_active_slot(self):
        device, _, _ = mock_device_client(active_slot=1)
        assert device.active_slot == device.slot(1)
        assert device.slot(1).is_active
        assert not device.slot(0).is_active

    def test_name_and_empty(self):
        device, _, _ = mock_device_client(slot_names=["Movies", None, None])
        assert device.slot(0).name == "Movies"
        assert not device.slot(0).is_empty
        assert device.slot(1).is_empty

    def test_activate(self):
        device, call, _ = mock_device_client()
        device.slot(2).activate()
        assert call.call_args[0][0] == "SetActiveSlot"
        assert call.call_args[0][1].i == 2

    def test_delete(self):
        device, call, _ = mock_device_client()
        device.slot(1).delete()
        assert call.call_args[0][0] == "DeleteSlot"
        assert call.call_args[0][1].i == 1


class TestUpload:
    def test_upload_passthrough(self):
        device, call, rest_mock = mock_device_client(num_speakers=10)
        slot = device.slot(2)
        call.reset_mock()
        slot.upload_passthrough(gain=0.5)

        call_names = [c[0][0] for c in call.call_args_list]
        assert call_names[0] == "GetDeviceInfo"
        for name in ("BeginFilterTransfer", "SetTransferCell", "SetFilterCell",
                     "SetFilterCommon", "EndFilterTransfer", "UpdateSlotInfo"):
            assert name in call_names

        # Every slot index sent is the slot we uploaded to
        begin = next(c for c in call.call_args_list if c[0][0] == "BeginFilterTransfer")
        end = next(c for c in call.call_args_list if c[0][0] == "EndFilterTransfer")
        update = next(c for c in call.call_args_list if c[0][0] == "UpdateSlotInfo")
        assert begin[0][1].slot_index == 2
        assert end[0][1].i == 2
        assert update[0][1].slot_index == 2

        # Uploading leaves activation and filtering to the caller
        assert "SetActiveSlot" not in call_names
        rest_mock.enable_filtering.assert_not_called()


class TestFiltering:
    def test_filtering_on_off(self):
        device, _, rest_mock = mock_device_client()
        device.filtering = True
        rest_mock.enable_filtering.assert_called_once()
        device.filtering = False
        rest_mock.disable_filtering.assert_called_once()

    def test_filtering_read(self):
        device, _, _ = mock_device_client(filtering_enabled=False)
        assert device.filtering is False
