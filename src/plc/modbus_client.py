import time
import logging
import threading

logger = logging.getLogger(__name__)

class ModbusPLCClient:
    """
    Client truyền thông Modbus TCP kết nối với PLC (Siemens S7, Mitsubishi, Delta, Schneider, Omron, Modbus Simulator).
    """
    def __init__(self, host="127.0.0.1", port=502, slave_id=1, auto_reconnect=True):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.auto_reconnect = auto_reconnect
        self.connected = False
        self.client = None
        self.lock = threading.Lock()
        self.last_error = ""

    def connect(self):
        """Kết nối tới Modbus TCP Server / PLC"""
        with self.lock:
            try:
                # Thử sử dụng pymodbus nếu có
                try:
                    from pymodbus.client import ModbusTcpClient
                    self.client = ModbusTcpClient(self.host, port=self.port, timeout=3)
                    self.connected = self.client.connect()
                except ImportError:
                    # Hỗ trợ phiên bản pymodbus cũ hơn
                    from pymodbus.client.sync import ModbusTcpClient
                    self.client = ModbusTcpClient(self.host, port=self.port, timeout=3)
                    self.connected = self.client.connect()

                if self.connected:
                    logger.info(f"Connected to PLC at {self.host}:{self.port}")
                    self.last_error = ""
                    return True
                else:
                    self.last_error = f"Failed to connect to {self.host}:{self.port}"
                    logger.warning(self.last_error)
                    return False
            except Exception as e:
                self.connected = False
                self.last_error = str(e)
                logger.error(f"PLC connection error: {e}")
                return False

    def disconnect(self):
        """Ngắt kết nối PLC"""
        with self.lock:
            if self.client and self.connected:
                try:
                    self.client.close()
                except Exception:
                    pass
            self.connected = False
            logger.info("Disconnected from PLC.")

    def _call_modbus_method(self, method_name, *args, **kwargs):
        """Helper gọi hàm Modbus tương thích mọi phiên bản pymodbus (2.x, 3.x, 3.14+)"""
        func = getattr(self.client, method_name)
        # Thử lần lượt các tên keyword argument tương thích: device_id (pymodbus 3.8+), slave (pymodbus 3.x), unit (pymodbus 2.x)
        for slave_key in ['device_id', 'slave', 'unit']:
            kw = dict(kwargs)
            kw[slave_key] = self.slave_id
            try:
                return func(*args, **kw)
            except TypeError as te:
                if 'unexpected keyword argument' in str(te) or 'unexpected keyword' in str(te):
                    continue
                raise
        # Nếu cả 3 keyword đều không khớp, thử gọi không kwarg slave
        return func(*args, **kwargs)

    def write_register(self, register_address, value):
        """
        Gửi giá trị phân loại (int) tới Holding Register của PLC.
        Ví dụ: Register 0 = 1 (Gate 1), Register 0 = 2 (Gate 2), ...
        """
        with self.lock:
            if not self.connected:
                if self.auto_reconnect:
                    logger.info("Attempting auto-reconnect to PLC...")
                    if not self._reconnect_nolock():
                        return False
                else:
                    return False

            try:
                # Ghi giá trị số nguyên (16-bit) vào thanh ghi
                response = self._call_modbus_method('write_register', register_address, int(value))
                if hasattr(response, 'isError') and response.isError():
                    self.last_error = f"Modbus Error: {response}"
                    logger.error(self.last_error)
                    return False
                
                logger.info(f"Successfully wrote value {value} to PLC Register {register_address}")
                return True
            except Exception as e:
                self.connected = False
                self.last_error = f"Write register error: {e}"
                logger.error(self.last_error)
                return False

    def read_register(self, register_address):
        """Đọc giá trị từ Holding Register của PLC"""
        with self.lock:
            if not self.connected:
                return None
            try:
                result = self._call_modbus_method('read_holding_registers', register_address, count=1)
                if hasattr(result, 'isError') and result.isError():
                    return None
                return result.registers[0]
            except Exception as e:
                logger.error(f"Read register error: {e}")
                return None

    def _reconnect_nolock(self):
        try:
            if self.client:
                self.client.close()
            self.client.connect()
            self.connected = self.client.connected if hasattr(self.client, 'connected') else True
            return self.connected
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            return False
