import jssc.SerialPort
import jssc.SerialPortEvent
import jssc.SerialPortEventListener
import jssc.SerialPortException
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
from java.util.function import Consumer
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable
from org.slf4j import Logger, LoggerFactory

@NonNullByDefault
class NikobusConnection(SerialPortEventListener):
    def __init__(self, serial_port_manager, port_name, process_data):
        self.logger = LoggerFactory.getLogger(NikobusConnection)
        self.serial_port_manager = serial_port_manager
        self.port_name = port_name
        self.process_data = process_data
        self.serial_port = None

    def is_connected(self):
        return self.serial_port is not None

    def connect(self):
        if self.is_connected():
            return

        port_id = self.serial_port_manager.get_identifier(self.port_name)
        if port_id is None:
            raise IOException(f"Port '{self.port_name}' is not known!")

        self.logger.info(f"Connecting to {self.port_name}")

        try:
            serial_port = SerialPort(port_id.getPortIdentifier())
            serial_port.openPort()
            serial_port.setParams(SerialPort.BAUDRATE_9600, SerialPort.DATABITS_8, SerialPort.STOPBITS_1, SerialPort.PARITY_NONE)
            serial_port.addEventListener(self)
            serial_port.notifyOnDataAvailable(True)
            self.serial_port = serial_port
            self.logger.info(f"Connected to {self.port_name}")
        except SerialPortException as e:
            raise IOException(f"Error opening serial port {self.port_name}", e)

    def close(self):
        serial_port = self.serial_port
        self.serial_port = None

        if serial_port is not None:
            try:
                serial_port.removeEventListener()
                serial_port.closePort()
                self.logger.debug("Closed serial port.")
            except SerialPortException as e:
                self.logger.debug("Error closing serial port.", e)

    def get_output_stream(self):
        serial_port = self.serial_port
        if serial_port is None:
            return None
        return serial_port.getOutputStream()

    def serial_event(self, event):
        if event.isRXCHAR():
            try:
                read_buffer = self.serial_port.readBytes(event.getEventValue())
                if read_buffer is not None:
                    for byte_value in read_buffer:
                        self.process_data.accept(byte_value)
            except SerialPortException as e:
                self.logger.debug(f"Error reading from serial port: {e.getMessage()}", e)
