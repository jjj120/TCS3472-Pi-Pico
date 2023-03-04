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
    def __init__(self, i2c: I2C, ledPin: Pin, addr: int = 0x29) -> None:
        self.I2C_ADDR = addr
        self.i2c = i2c
        self.ledPin = ledPin
        self._glassAttenuation = 1.
        self.enable()
    
    #region led Control
    def ledOn(self) -> None:
        self.ledPin.value(1)

    def ledOff(self) -> None:
        self.ledPin.value(0)
    #endregion led Control
    
    #region from Datasheet
    #region communication
    def __sendCommand(self, command: str, value: int, commType: int = 0b01):
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
        self.i2c.writeto_mem(self.I2C_ADDR, commandByte, value.to_bytes(1, "big"))
        return
    
    def __readRegister(self, register: str, length: int = 1) -> int:
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
    #endregion communication


    #region enable/disable
    def __enableComm(self, value: int):
        """
        Enables the TCS34725
        value: The value to send to the ENABLE register [int]
        """
        self.__sendCommand("ENABLE", value)
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
    #endregion enable/disable
    
    #region timing
    @property
    def timing_ms(self) -> float:
        """
        Gets the timing of the TCS34725 in ms
        """
        value = self.__readRegister("ATIME")
        timing_ms = {
            0xFF: 2.4,
            0xF6:  24,
            0xD5: 101,
            0xC0: 154,
            0x00: 700
        }.get(value, 2.4)
        return timing_ms

    @timing_ms.setter
    def timing_ms(self, timing: float) -> None:
        """
        Sets the timing of the TCS34725
        timing: The timing to set in ms [int]
        """
        # if timing not in range(256): raise ValueError("Timing must be between 0 and 255, {} was given".format(timing))
        if timing not in [2.4, 24, 50, 101, 154, 700]: raise ValueError("Timing must be 2.4, 24, 50, 101, 154 or 700 ms, {} was given".format(timing))
        timingValue = {
            2.4: 0xFF,
            24:  0xF6,
            101: 0xD5,
            154: 0xC0,
            700: 0x00
        }.get(timing, 1)

        self.__sendCommand("ATIME", timingValue)


    @property
    def timing_cycles(self) -> int:
        """
        Gets the timing of the TCS34725
        """
        value = self.__readRegister("ATIME")
        timingCycles = {
            0xFF:  1,
            0xF6: 10,
            0xD5: 42,
            0xC0: 64,
            0x00: 256
        }.get(value, 2.4)
        return self.__readRegister("ATIME")

    @timing_cycles.setter
    def timing_cycles(self, timing: int) -> None:
        """
        Sets the timing of the TCS34725
        timing: The timing to set in cycles [int]
        """
        if timing not in [1, 10, 42, 64, 256]: raise ValueError("Timing must be 1, 10, 42, 64 or 256 cycles, {} was given".format(timing))
        timingValue = {
              1: 0xFF,
             10: 0xF6,
             42: 0xD5,
             64: 0xC0,
            256: 0x00
        }.get(timing, 1)
        self.__sendCommand("ATIME", timing)
    #endregion timing

    #region wait timing
    @property
    def wait_time_value(self) -> int:
        """
        Gets the wait timing of the TCS34725 in ms
        """
        value = self.__readRegister("WTIME")
        waitTiming_ms = {
            0xFF : 1,
            0xAB : 85,
            0x00 : 256
        }.get(value, 1)
        return waitTiming_ms

    @wait_time_value.setter
    def wait_time_value(self, timing: int) -> None:
        """
        Sets the wait timing of the TCS34725
        timing: The timing to set in ms [int]
        """
        if timing not in [1, 85, 256]: raise ValueError("Timing must be 1, 85 or 256 ms, {} was given".format(timing))
        timingValue = {
              1: 0xFF,
             85: 0xAB,
            256: 0x00
        }.get(timing, 1)
        self.__sendCommand("WTIME", timingValue)
    
    @property
    def wait_time_ms(self) -> float:
        """
        Gets the wait timing of the TCS34725 in ms
        """
        value = self.__readRegister("WTIME")
        if self.WLONG:
            waitTiming_ms = {
                0xFF : 2.4,
                0xAB : 204,
                0x00 : 614
            }.get(value, 2.4)
        else:
            waitTiming_ms = {
                0xFF : 0.029 * 1000,
                0xAB : 2.45  * 1000,
                0x00 : 7.4   * 1000
            }.get(value, 1)
        return waitTiming_ms
    
    @wait_time_ms.setter
    def wait_time_ms(self, timing: float) -> None:
        """
        Sets the wait timing of the TCS34725
        timing: The timing to set in ms [int]
        """
        if timing not in [2.4, 204, 614] and timing not in [0.029 * 1000, 2.45 * 1000, 7.4 * 1000]: raise ValueError("Timing must be 2.4, 204, 614 or 29, 2450, 7400 ms, {} was given".format(timing))
        if timing in [2.4, 204, 614]:
            if timing == 2.4:
                timingValue = 0xFF
            elif timing == 204:
                timingValue = 0xAB
            else: # timing == 614:
                timingValue = 0x00
            self.WLONG = False
        else:
            if timing == 0.029 * 1000:
                timingValue = 0xFF
            elif timing == 2.45 * 1000:
                timingValue = 0xAB
            else: # timing == 7.4 * 1000:
                timingValue = 0x00
            self.WLONG = True

        self.__sendCommand("WTIME", timingValue)
    
    @property
    def wait_time_seconds(self) -> float:
        """
        Gets the wait timing of the TCS34725 in seconds
        """
        return self.wait_time_ms / 1000

    @wait_time_seconds.setter
    def wait_time_seconds(self, timing: float) -> None:
        """
        Sets the wait timing of the TCS34725
        timing: The timing to set in seconds [int]
        """
        self.wait_time_ms = timing * 1000
    #endregion wait timing

    #region thresholds
    @property
    def minThreshold(self) -> int:
        """
        Gets the minimum threshold of the TCS34725
        """
        return self.__readRegister("AILT") + (self.__readRegister("AILTH") << 8)
    
    @minThreshold.setter
    def minThreshold(self, threshold: int) -> None:
        """
        Sets the minimum threshold of the TCS34725
        threshold: The threshold to set [int]
        """
        if threshold > 0xFFFF or threshold < 0: raise ValueError("Threshold must be between 0 and 0xFFFF, {} was given".format(hex(threshold)))
        self.__sendCommand("AILT", threshold & 0xFF)
        self.__sendCommand("AILTH", (threshold >> 8) & 0xFF)
        return
    
    @property
    def maxThreshold(self) -> int:
        """
        Gets the maximum threshold of the TCS34725
        """
        return self.__readRegister("AIHT") + (self.__readRegister("AIHTH") << 8)
    
    @maxThreshold.setter
    def maxThreshold(self, threshold: int) -> None:
        """
        Sets the maximum threshold of the TCS34725
        threshold: The threshold to set [int]
        """
        if threshold > 0xFFFF or threshold < 0: raise ValueError("Threshold must be between 0 and 0xFFFF, {} was given".format(hex(threshold)))
        self.__sendCommand("AIHT", threshold & 0xFF)
        self.__sendCommand("AIHTH", (threshold >> 8) & 0xFF)
        return
    #endregion thresholds

    #region persistance
    @property
    def persistance(self) -> int:
        """
        Interrupt persistence, controls rate of interrupts from the sensor
        can be 1, 2, 3 or 5, 10, 15, ... 60 [int]
        """
        return self.__readRegister("PERS")
    
    @persistance.setter
    def persistance(self, persistance: int) -> None:
        if persistance not in [1, 2, 3] and persistance not in range(5, 61, 5): raise ValueError("Persistance must be 1, 2, 3 or 5, 10, 15, ... 60, {} was given".format(persistance))
        self.__sendCommand("PERS", persistance)
        return
    #endregion persistance

    #region configuration/wlong
    @property
    def WLONG(self) -> bool:
        """
        Gets the WLONG bit of the TCS34725
        """
        return bool(bin(self.__readRegister("CONFIG"))[-2]) #return second last bit -> WLONG
    
    @WLONG.setter
    def WLONG(self, value: bool) -> None:
        """
        Sets the WLONG bit of the TCS34725
        value: The value to set the WLONG bit to [bool]
        """
        if not isinstance(value, bool): raise ValueError("WLONG must be a boolean, {} was given".format(value))
        self.__sendCommand("CONFIG", value << 1)
    #endregion configuration/wlong

    #region control/gain
    @property 
    def gain(self) -> int:
        """
        Gets the gain of the TCS34725
        """
        gainBits = int(bin(self.__readRegister("CONTROL"))[-2:], 2) # get the last two bits and convert to int
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
        self.__sendCommand("CONTROL", valueBits)
    #endregion control/gain

    #region sensorId
    @property
    def sensorId(self) -> int:
        """
        Gets the sensor ID, read only!
        """
        return self.__readRegister("ID")
    
    @sensorId.setter
    def sensorId(self, value: int) -> None:
        raise ValueError("Sensor ID is read-only and cannot be changed")
    #endregion sensorId

    #region status
    @property
    def status(self) -> int:
        """
        Gets the sensor status, read only!
        0b10: No interrupt
        0b01: A valid RGBC cycle has completed and the RGBC data is ready to be read
        0b00 or 0b11: an error has occurred
        """
        status = self.__readRegister("STATUS")
        statusRelBits = [bin(status)[3], bin(status)[7]]
        statusBits = 0x00
        if statusRelBits[0] == "1": statusBits += 0b01
        if statusRelBits[1] == "1": statusBits += 0b10
        return statusBits
    
    @status.setter
    def status(self, value: int) -> None:
        raise ValueError("Status is read-only and cannot be changed")
    #endregion status
    #endregion Datasheet

    #region get Color
    def getColor(self) -> tuple[int, int, int, int]:
        """
        Gets the color from the sensor
        returns: A tuple of clear, red, green and blue data [tuple(int, int, int, int)]
        """
        return (
            self.__readRegister("CDATA", length=2), # clear data bytes
            self.__readRegister("RDATA", length=2), # red data bytes
            self.__readRegister("GDATA", length=2), # green data bytes
            self.__readRegister("BDATA", length=2)  # blue data bytes
        )

    def getRGB(self) -> tuple[int, int, int]:
        """
        Gets the color from the sensor
        returns: A tuple of red, green and blue data [tuple(int, int, int)]
        """
        return self.getColor()[1:]
    #endregion get Color
    
    #region Color Temperature and Lux calculations DN40
        # inspired by _temperature_and_lux_dn40() from Adafruit CircuitPython library https://github.com/adafruit/Adafruit_CircuitPython_TCS34725/blob/main/adafruit_tcs34725.py
        # in turn using the calculations from DN40 algorithm from AMS https://ams.com/documents/20143/36005/ColorSensors_AN000166_1-00.pdf/d1290c78-4ef1-5b88-bff0-8e80c2f92b6b

    def colorTemperatureLux(self) -> tuple[int, int]:
        """
        Gets the color temperature from the sensor
        returns: The color temperature in Kelvin and light intensitiy in lux tuple[int, int]
        returns: -1 if sensor is oversaturated
        """
        # inspired by _temperature_and_lux_dn40() from Adafruit CircuitPython library https://github.com/adafruit/Adafruit_CircuitPython_TCS34725/blob/main/adafruit_tcs34725.py
        # in turn using the calculations from DN40 algorithm from AMS https://ams.com/documents/20143/36005/ColorSensors_AN000166_1-00.pdf/d1290c78-4ef1-5b88-bff0-8e80c2f92b6b

        #basic input data
        r, g, b, c = self.getColor()
        ATIME_MS = self.timing_ms
        AGAIN = self.gain

        #coefficents from DN40 Appendix I
        GA        =  self._glassAttenuation     #glass attenuation
        DF        =  310.0   #device factor
        DGF       =  GA * DF #device and glass factor
        R_COEF    =  0.136   #coefficient for red
        G_COEF    =  1.000   #coefficient for green
        B_COEF    = -0.444   #coefficient for blue
        CT_COEF   =  3810.0  #coefficient for color temperature
        CT_OFFSET =  1391.0  #offset for color temperature

        #device saturation DN40 3.5
        if (256 - ATIME_MS) > 63.0: SATURATION = 65535 #digital saturation
        else: SATURATION = 1024 * (256 - ATIME_MS)     #analog  saturation

        #ripple saturation DN40 3.7
        if ATIME_MS < 150: SATURATION -= SATURATION / 4

        #check saturation, reject if oversaturated
        if c > SATURATION: return (-1, -1)

        #ir rejection DN40 3.1
        ir = (r + g + b - c) / 2
        r1 = r - ir
        g1 = g - ir
        b1 = b - ir
        c1 = c - ir

        #lux calculation DN40 3.2
        g2 = R_COEF * r1 + G_COEF * g1 + B_COEF * b1
        CPL = (ATIME_MS * AGAIN) / DGF
        lux = g2 / CPL

        #color temperature calculation DN40 3.4
        colorTemp = CT_COEF * b1 / r1 + CT_OFFSET

        return (int(lux), int(colorTemp))
    
    #region glass attenuation
    @property
    def glass_attenuation(self):
        """The Glass Attenuation (FA) factor used to compensate for lower light
        levels at the device due to the possible presence of glass. The GA is
        the inverse of the glass transmissivity (T), so :math:`GA = 1/T`. A transmissivity
        of 50% gives GA = 1 / 0.50 = 2. If no glass is present, use GA = 1.
        See Application Note: DN40-Rev 1.0 – Lux and CCT Calculations using
        ams Color Sensors for more details.
        """
        return self._glass_attenuation

    @glass_attenuation.setter
    def glass_attenuation(self, value: float):
        if value < 1:
            raise ValueError("Glass attenuation factor must be at least 1.")
        self._glass_attenuation = value
    #endregion glass attenuation

    #endregion Color Temperature and Lux calculations DN40


if __name__ == "__main__":
    i2c = I2C(id=0, freq=400_000, scl=Pin(22), sda=Pin(21)) # type: ignore
    ledPin = Pin(2, Pin.OUT)
    sensor = TCS34725(i2c, ledPin)