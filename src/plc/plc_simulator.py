import time
import socket
import threading
import logging

logger = logging.getLogger(__name__)

class PLCSimulator:
    """
    Trình giả lập PLC Modbus TCP đơn giản tích hợp sẵn trong ứng dụng.
    Lắng nghe tín hiệu kết nối Modbus TCP từ ứng dụng chính và ghi nhận các thanh ghi.
    """
    def __init__(self, host="127.0.0.1", port=502):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.registers = [0] * 100  # 100 Holding Registers giả lập (Address 0 -> 99)
        self.thread = None
        self.on_register_change = None  # Callback khi thanh ghi thay đổi giá trị

    def start(self):
        """Khởi chạy server giả lập trên background thread"""
        if self.running:
            return True

        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        logger.info(f"PLC Simulator started on {self.host}:{self.port}")
        return True

    def stop(self):
        """Dừng server giả lập"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        logger.info("PLC Simulator stopped.")

    def _run_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Thử bind port 502, nếu bận hoặc thiếu quyền Admin thì chuyển sang port 5020
            try:
                self.server_socket.bind((self.host, self.port))
            except Exception as e:
                logger.warning(f"Could not bind to port {self.port} ({e}). Falling back to port 5020.")
                self.port = 5020
                self.server_socket.bind((self.host, self.port))

            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)

            while self.running:
                try:
                    client_sock, client_addr = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_sock, client_addr), 
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Simulator server error: {e}")
                    break

        except Exception as e:
            logger.error(f"Failed to start PLC Simulator: {e}")
        finally:
            self.running = False

    def _handle_client(self, client_sock, client_addr):
        client_sock.settimeout(2.0)
        while self.running:
            try:
                data = client_sock.recv(1024)
                if not data:
                    break
                
                # Xử lý frame Modbus TCP đơn giản (MBAP Header + PDU)
                # Structure: [Transaction ID (2B)][Protocol ID (2B)][Length (2B)][Unit ID (1B)][Function Code (1B)][Payload...]
                if len(data) >= 10:
                    trans_id = data[0:2]
                    proto_id = data[2:4]
                    unit_id = data[6]
                    func_code = data[7]

                    # Function 6 (0x06): Write Single Register
                    if func_code == 6 and len(data) >= 12:
                        reg_addr = (data[8] << 8) | data[9]
                        reg_val = (data[10] << 8) | data[11]

                        if 0 <= reg_addr < len(self.registers):
                            old_val = self.registers[reg_addr]
                            self.registers[reg_addr] = reg_val
                            logger.info(f"[SIMULATOR] Written Reg {reg_addr} = {reg_val}")
                            
                            if self.on_register_change:
                                try:
                                    self.on_register_change(reg_addr, reg_val)
                                except Exception as cb_e:
                                    logger.error(f"Callback error: {cb_e}")

                        # Response bằng chính packet yêu cầu (Standard Modbus FC6 Echo response)
                        client_sock.sendall(data[:12])

                    # Function 3 (0x03) hoặc 4 (0x04): Read Registers
                    elif (func_code == 3 or func_code == 4) and len(data) >= 12:
                        reg_addr = (data[8] << 8) | data[9]
                        reg_cnt = (data[10] << 8) | data[11]
                        
                        byte_count = reg_cnt * 2
                        response_pdu = bytearray([unit_id, func_code, byte_count])
                        
                        for i in range(reg_cnt):
                            addr = reg_addr + i
                            val = self.registers[addr] if 0 <= addr < len(self.registers) else 0
                            response_pdu.append((val >> 8) & 0xFF)
                            response_pdu.append(val & 0xFF)

                        length = len(response_pdu)
                        header = trans_id + proto_id + bytes([(length >> 8) & 0xFF, length & 0xFF])
                        client_sock.sendall(header + response_pdu)

                    # Function 16 (0x10): Write Multiple Registers
                    elif func_code == 16 and len(data) >= 13:
                        reg_addr = (data[8] << 8) | data[9]
                        reg_cnt = (data[10] << 8) | data[11]
                        reg_val = (data[13] << 8) | data[14]

                        if 0 <= reg_addr < len(self.registers):
                            self.registers[reg_addr] = reg_val
                            if self.on_register_change:
                                self.on_register_change(reg_addr, reg_val)

                        # Response for FC16
                        response_pdu = bytearray([unit_id, func_code, data[8], data[9], data[10], data[11]])
                        length = len(response_pdu)
                        header = trans_id + proto_id + bytes([(length >> 8) & 0xFF, length & 0xFF])
                        client_sock.sendall(header + response_pdu)

            except socket.timeout:
                continue
            except Exception:
                break

        client_sock.close()
