from machine import Pin, I2C

REGISTERS = {
   # Command: [Register, RW]
    "ENABLE": [0x00, 0b11], # Enables states and interrupts
    "ATIME":  [0x01, 0b11], # RGBC time
    "WTIME":  [0x03, 0b11], # Wait time
    "AILTL":  [0x04, 0b11], # Clear interrupt low threshold low byte
    "AILTH":  [0x05, 0b11], # Clear interrupt low threshold high byte
    "AIHTL":  [0x06, 0b11], # Clear interrupt high threshold low byte
    "AIHTH":  [0x07, 0b11], # Clear interrupt high threshold high byte
    "PERS":   [0x0C, 0b11], # Interrupt persistence filter
    "CONFIG": [0x0D, 0b11], # Configuration
    "CONTROL":[0x0F, 0b11], # Control
    "ID":     [0x12, 0b10], # Device ID
    "STATUS": [0x13, 0b10], # Device status
    "CDATAL": [0x14, 0b10], # Clear data low byte
    "CDATAH": [0x15, 0b10], # Clear data high byte
    "RDATAL": [0x16, 0b10], # Red data low byte
    "RDATAH": [0x17, 0b10], # Red data high byte
    "GDATAL": [0x18, 0b10], # Green data low byte
    "GDATAH": [0x19, 0b10], # Green data high byte
    "BDATAL": [0x1A, 0b10], # Blue data low byte
    "BDATAH": [0x1B, 0b10], # Blue data high byte
    
    "CLRINT": [0x06, 0b11], # Clear interrupt
}

DATA_REGISTERS = {
    "CDATA":  0x14, # Clear data low byte
    "CDATAH": 0x15, # Clear data high byte
    "RDATA":  0x16, # Red data low byte
    "RDATAH": 0x17, # Red data high byte
    "GDATA":  0x18, # Green data low byte
    "GDATAH": 0x19, # Green data high byte
    "BDATA":  0x1A, # Blue data low byte
    "BDATAH": 0x1B, # Blue data high byte
}


ENABLE_AIEN = 0x10 # RGBC Interrupt Enable
ENABLE_WEN = 0x08 # Wait enable - Writing 1 activates the wait timer
ENABLE_AEN = 0x02 # RGBC Enable - Writing 1 actives the ADC, 0 disables it
ENABLE_PON = 0x01 # Power on - Writing 1 activates the internal oscillator, 0 disables it

RESET_ATIME = 0xFF
RESET_WTIME = 0xFF
RESET_VALUE = 0x00


class TCS34725():
    def __init__(self, i2c, addr=0x29) -> None:
        self.I2C_ADDR = addr
        self.i2c = i2c
        self.enable()
    

    def sendCommand(self, command: str, value: int, commType: int = 0b01):
        """
        Sends a command to the TCS34725
        command: The command to send [str]
        value: The value to send [int]
        commType: The type of command to send [int], refer to datasheet for more info
        """
        # error checking
        if type == 0b10: raise ValueError("Command type 0b10 is reserved by the TCS34725 and should not be used")
        if command not in REGISTERS: raise ValueError("Command {} is not a valid command".format(command))
        if REGISTERS[command][1] == 0b10: raise ValueError("Command {} is a read-only command".format(command))
        # write to the command register
        commType = commType << 5
        commandByte = 0x80 + commType + REGISTERS[command][0]
        self.i2c.writeto_mem(self.I2C_ADDR, commandByte, value)
        return
    
    def readRegister(self, register: str, length: int = 1) -> int:
        """
        Reads a register from the TCS34725
        register: The register to read [str]
        """
        # error checking
        if register not in REGISTERS: raise ValueError("Register {} is not a valid register".format(register))
        if REGISTERS[register][1] == 0b01: raise ValueError("Register {} is a write-only register".format(register))
        # read from the register
        if length == 1: return self.i2c.readfrom_mem(self.I2C_ADDR, REGISTERS[register][0], length)[0]
        else: #if length > 1, so more than one byte is read
            data = self.i2c.readfrom_mem(self.I2C_ADDR, REGISTERS[register][0], length)
            returnValue = 0
            for index, byte in enumerate(data):
                returnValue += byte << (8 * index)
            return returnValue

    def __enableComm(self, value: int):
        """
        Enables the TCS34725
        value: The value to send to the ENABLE register [int]
        """
        self.sendCommand("ENABLE", value)
        return
    
    def enable(self):
        """
        Enables the TCS34725
        """
        self.__enableComm(ENABLE_PON)
        self.__enableComm(ENABLE_PON | ENABLE_AEN)
        return
    
    def disable(self):
        """
        Disables the TCS34725
        """
        self.__enableComm(0x00)
        return
    

    @property
    def persistance(self) -> int:
        """
        Interrupt persistence, controls rate of interrupts from the sensor
        can be 1, 2, 3 or 5, 10, 15, ... 60 [int]
        """
        return self.readRegister("PERS")
    
    @persistance.setter
    def persistance(self, persistance: int) -> None:
        if persistance not in [1, 2, 3] and persistance not in range(5, 61, 5): raise ValueError("Persistance must be 1, 2, 3 or 5, 10, 15, ... 60, {} was given".format(persistance))
        self.sendCommand("PERS", persistance)
        return
    

    @property 
    def gain(self) -> int:
        """
        Gets the gain of the TCS34725
        """
        gainBits = int(bin(self.readRegister("CONTROL"))[-2:], 2) # get the last two bits and convert to int
        gain = {
            0b00: 1,
            0b01: 4,
            0b10: 16,
            0b11: 60
        }.get(gainBits, 1)
        return gain
    
    @gain.setter 
    def gain(self, value: int) -> None:
        """
        Sets the gain of the TCS34725
        value: The gain to set, can be 1x, 4x, 16x or 60x [int]
        """
        if value not in [1, 4, 16, 60]: raise ValueError("Gain must be 1, 4, 16 or 60, {} was given".format(value))
        valueBits = {
            1:  0b00,
            4:  0b01,
            16: 0b10,
            60: 0b11
        }.get(value, 0b00)
        self.sendCommand("CONTROL", valueBits)
    

    @property
    def sensorId(self) -> int:
        """
        Gets the sensor ID, read only!
        """
        return self.readRegister("ID")
    
    @sensorId.setter
    def sensorId(self, value: int) -> None:
        raise ValueError("Sensor ID is read-only and cannot be changed")
    
    @property
    def status(self) -> int:
        """
        Gets the sensor status, read only!
        0b10: No interrupt
        0b01: A valid RGBC cycle has completed and the RGBC data is ready to be read
        0b00 or 0b11: an error has occurred
        """
        status = self.readRegister("STATUS")
        statusRelBits = [bin(status)[3], bin(status)[7]]
        statusBits = 0x00
        if statusRelBits[0] == "1": statusBits += 0b01
        if statusRelBits[1] == "1": statusBits += 0b10
        return statusBits
    
    @status.setter
    def status(self, value: int) -> None:
        raise ValueError("Status is read-only and cannot be changed")
    

    def getColor(self) -> tuple[int, int, int, int]:
        """
        Gets the color from the sensor
        returns: A tuple of clear, red, green and blue data [tuple(int, int, int, int)]
        """
        return (
            self.readRegister("CDATA", length=2), # clear data bytes
            self.readRegister("RDATA", length=2), # red data bytes
            self.readRegister("GDATA", length=2), # green data bytes
            self.readRegister("BDATA", length=2)  # blue data bytes
        )

    

if __name__ == "__main__":
    i2c = I2C(id=0, freq=400_000, scl=Pin(22), sda=Pin(21)) # type: ignore
    sensor = TCS34725(i2c)