#!/usr/bin/env python

#############################################################################
# Celestica
#
# Component contains an implementation of SONiC Platform Base API and
# provides the components firmware management function
#
#############################################################################

import subprocess
import re

try:
    from sonic_platform_base.component_base import ComponentBase
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

COMPONENT_LIST = [
    ("BIOS",       "Basic input/output System"),
    ("ONIE",        "Open Network Install Environment"),
    ("SSD",         "Solid State Drive - {}"),
    ("BASE_CPLD",  "Base board CPLD"),
    ("SW_CPLD1",   "Switch board CPLD 1"),
    ("SW_CPLD2",   "Switch board CPLD 2"),
    ("SW_CPLD2",   "Switch board CPLD 2"),
    ("ASIC_PCIe",   "ASIC PCIe Firmware"),
    ("BMC",        "Used for monitoring and managing whole system")
]
NAME_INDEX = 0
DESCRIPTION_INDEX = 1

BIOS_VERSION_CMD = "dmidecode -s bios-version"
ONIE_VERSION_CMD = "cat /host/machine.conf"
SWCPLD1_VERSION_CMD = "i2cget -y -f 102 0x30 0x0"
SWCPLD2_VERSION_CMD = "i2cget -y -f 102 0x31 0x0"
GETREG_PATH="/sys/devices/platform/sys_cpld/getreg"
BASECPLD_VERSION_CMD="echo '0xA100' > {} && cat {}".format(GETREG_PATH, GETREG_PATH)
BMC_PRESENCE="echo '0xA108' > {} && cat {}".format(GETREG_PATH, GETREG_PATH)
SSD_VERSION_CMD = "smartctl -i /dev/sda"
ASIC_PCIE_VERSION_CMD = "bcmcmd 'pciephy fw version' | grep 'PCIe FW version' | cut -d ' ' -f 4"

UNKNOWN_VER = "Unknown"

class Component():
    """Platform-specific Component class"""

    DEVICE_TYPE = "component"

    def __init__(self, component_index):
        ComponentBase.__init__(self)
        self.index = component_index
        self.name = self.get_name()

    def __get_cpld_ver(self):
        cpld_version_dict = dict()
        cpld_ver_info = {
            'BASE_CPLD': self.__get_basecpld_ver(),
            'SW_CPLD1': self.__get_swcpld1_ver(),
            'SW_CPLD2': self.__get_swcpld2_ver(),
        }
        for cpld_name, cpld_ver in cpld_ver_info.items():
            cpld_ver_str = "{}.{}".format(int(cpld_ver[2], 16), int(
                cpld_ver[3], 16)) if cpld_ver else UNKNOWN_VER
            cpld_version_dict[cpld_name] = cpld_ver_str

        return cpld_version_dict

    def __get_asic_pcie_ver(self):
        status, raw_ver=self.run_command(ASIC_PCIE_VERSION_CMD)
        if status:
            return raw_ver
        else:
            return UNKNOWN_VER

    def __get_bios_ver(self):
        status, raw_ver=self.run_command(BIOS_VERSION_CMD)
        if status:
            return raw_ver
        else:
            return UNKNOWN_VER

    def __get_basecpld_ver(self):
        status, raw_ver=self.run_command(BASECPLD_VERSION_CMD)
        if status:
            return raw_ver
        else:
            return UNKNOWN_VER

    def __get_swcpld1_ver(self):
        status, raw_ver=self.run_command(SWCPLD1_VERSION_CMD)
        if status:
            return raw_ver
        else:
            return UNKNOWN_VER

    def __get_swcpld2_ver(self):
        status, raw_ver=self.run_command(SWCPLD2_VERSION_CMD)
        if status:
            return raw_ver
        else:
            return UNKNOWN_VER

    def __get_bmc_presence(self):
        status, raw_ver=self.run_command(BMC_PRESENCE)
        if status and raw_ver == "0x00":
            return True
        else:
            return False

    def __get_bmc_ver(self):
        cmd="ipmitool mc info | grep 'Firmware Revision'"
        status, raw_ver=self.run_command(cmd)
        if status:
            bmc_ver=raw_ver.split(':')[-1].strip()
            return {"BMC":bmc_ver}
        else:
            return {"BMC":"N/A"}

    def __get_onie_ver(self):
        onie_ver = "N/A"
        status, raw_onie_data = self.run_command(ONIE_VERSION_CMD)
        if status:
            ret = re.search(r"(?<=onie_version=).+[^\n]", raw_onie_data)
            if ret != None:
                onie_ver = ret.group(0)
        return onie_ver

    def __get_ssd_ver(self):
        ssd_ver = "N/A"
        status, raw_ssd_data = self.run_command(SSD_VERSION_CMD)
        if status:
            ret = re.search(r"Firmware Version: +(.*)[^\\]", raw_ssd_data)
            if ret != None:
                ssd_ver = ret.group(1)
        return ssd_ver

    def __get_ssd_desc(self, desc_format):
        description = "N/A"
        status, raw_ssd_data = self.run_command(SSD_VERSION_CMD)
        if status:
            ret = re.search(r"Device Model: +(.*)[^\\]", raw_ssd_data)
            if ret != None:
                try:
                    description = desc_format.format(ret.group(1))
                except (IndexError):
                    pass
        return description

    def get_name(self):
        """
        Retrieves the name of the component
         Returns:
            A string containing the name of the component
        """
        return COMPONENT_LIST[self.index][NAME_INDEX]

    def get_description(self):
        """
        Retrieves the description of the component
            Returns:
            A string containing the description of the component
        """
        # For SSD get the model name from device
        if self.get_name() == "SSD":
            return self.__get_ssd_desc(COMPONENT_LIST[self.index][1])

        return COMPONENT_LIST[self.index][DESCRIPTION_INDEX]

    def get_firmware_version(self):
        """
        Retrieves the firmware version of module
        Returns:
            string: The firmware versions of the module
        """
        fw_version_info = {
            "ONIE": self.__get_onie_ver(),
            "SSD": self.__get_ssd_ver(),
            "BIOS": self.__get_bios_ver(),
            "ASIC_PCIe": self.__get_asic_pcie_ver(),
        }
        fw_version_info.update(self.__get_cpld_ver())
        if self.__get_bmc_presence():
            fw_version_info.update(self.__get_bmc_ver())
        return fw_version_info.get(self.name, UNKNOWN_VER)
   
    def run_command(self, cmd):
        status = True
        result = ""
        try: 
            p = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            raw_data, err = p.communicate()
            if err.decode('UTF-8') == '': 
                result = raw_data.strip().decode('UTF-8')
        except Exception:
            status = False
        return status, result