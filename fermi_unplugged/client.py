"""gRPC client for dio.endpoint.EndpointDevice.

Message types come from protos/dio_endpoint.proto (compiled to dio_endpoint_pb2.py).
"""
try:
    import grpc
    from fermi_unplugged import dio_endpoint_pb2
except ImportError as e:
    raise ImportError(
        "fermi-unplugged needs grpcio and protobuf. pip install grpcio protobuf"
    ) from e

# method -> (request_type, response_type, kind)
METHODS = {
    "GetDeviceInfo": ("Void", "DeviceInfo", "unary"),
    "GetSlotInfo": ("Index", "SlotInfo", "unary"),
    "GetActiveSlot": ("Void", "Index", "unary"),
    "GetFilterInfo": ("FilterInfoQuery", "FilterInfo", "unary"),
    "BeginFilterTransfer": ("SlotInfo", "Void", "unary"),
    "SetTransferCell": ("CellIndex", "Void", "unary"),
    "SetFilterCell": ("FilterCell", "Void", "unary"),
    "SetFilterCommon": ("FilterCommon", "Void", "unary"),
    "EndFilterTransfer": ("Index", "Progress", "server_stream"),
    "UpdateSlotInfo": ("SlotInfoUpdate", "Void", "unary"),
    "SetActiveSlot": ("Index", "Void", "unary"),
    "DeleteSlot": ("Index", "Void", "unary"),
}


def msg(_type, **kw):
    return getattr(dio_endpoint_pb2, _type)(**kw)


class EndpointClient:
    """Typed gRPC client for dio.endpoint.EndpointDevice."""

    def __init__(self, host):
        self.host = host
        self.ch = grpc.insecure_channel(host)

    @property
    def ip(self):
        return self.host.split(":")[0]

    def call(self, method, request=None, timeout=10):
        req_t, resp_t, kind = METHODS[method]
        request = request if request is not None else msg(req_t)
        rcls = type(msg(resp_t))
        path = f"/dio.endpoint.EndpointDevice/{method}"
        ser = lambda x: x.SerializeToString()
        de = rcls.FromString
        if kind == "unary":
            return self.ch.unary_unary(
                path, request_serializer=ser, response_deserializer=de)(
                    request, timeout=timeout)
        if kind == "client_stream":
            return self.ch.stream_unary(
                path, request_serializer=ser, response_deserializer=de)(
                    iter(request), timeout=timeout)
        return list(self.ch.unary_stream(
            path, request_serializer=ser, response_deserializer=de)(
                request, timeout=timeout))