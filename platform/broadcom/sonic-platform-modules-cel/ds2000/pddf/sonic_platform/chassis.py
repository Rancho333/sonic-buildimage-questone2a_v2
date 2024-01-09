#############################################################################
# PDDF
# Module contains an implementation of SONiC Chassis API
#
#############################################################################

try:
    from sonic_platform_pddf_base.pddf_chassis import PddfChassis
    import sys
    import subprocess
    import time
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

NUM_SFP = 56
GETREG_PATH="/sys/devices/platform/sys_cpld/getreg"
SETREG_PATH="/sys/devices/platform/sys_cpld/setreg"
BMC_PRESENCE="echo '0xA108' > {} && cat {}".format(GETREG_PATH, GETREG_PATH)
SET_SYS_STATUS_LED="echo {} {} > {}"
GET_REBOOT_CAUSE="echo '0xA107' > {} && cat {}".format(GETREG_PATH, GETREG_PATH)

class Chassis(PddfChassis):
    """
    PDDF Platform-specific Chassis class
    """
    sfp_status_dict={}

    def __init__(self, pddf_data=None, pddf_plugin_data=None):
        PddfChassis.__init__(self, pddf_data, pddf_plugin_data)

        for port_idx in range(1, NUM_SFP+1):
            present = self.get_sfp(port_idx).get_presence()
            self.sfp_status_dict[port_idx] = '1' if present else '0'
        
        # Component firmware version initialization
        from sonic_platform.component import Component
        status, presence =  self._getstatusoutput(BMC_PRESENCE)
        if status == 0 and presence == "0x00":
            NUM_COMPONENT = 9
        else:
            NUM_COMPONENT = 8
        for i in range(0, NUM_COMPONENT):
            component = Component(i)
            self._component_list.append(component)
    
    def _getstatusoutput(self, cmd):
        try:
            data = subprocess.check_output(cmd, shell=True,
                    universal_newlines=True, stderr=subprocess.STDOUT)
            status = 0
        except subprocess.CalledProcessError as ex:
            data = ex.output
            status = ex.returncode
        if data[-1:] == '\n':
            data = data[:-1]
        return status, data

    def initizalize_system_led(self):
        return True

    def get_status_led(self):
        return self.get_system_led("SYS_LED")

    def set_status_led(self, color):     
        if color == self.get_status_led():
            return False
                 
        current_color = self.get_status_led()
        if current_color == color:
            return True
                                      
        color_val="0xd0"                 
        if color == "green":             
            color_val="0xd0"             
        elif color == "amber":           
            color_val="0xe0"             
        
        cmd=SET_SYS_STATUS_LED.format("0xA162", color_val, SETREG_PATH)
        status, res = self._getstatusoutput(cmd)
                                         
        if status != 0:                       
            return False                  
        else:                            
            return True

    def get_sfp(self, index):
        """    
        Retrieves sfp represented by (1-based) index <index>
        For Quanta the index in sfputil.py starts from 1, so override
        Args:
            index: An integer, the index (1-based) of the sfp to retrieve.
            The index should be the sequence of a physical port in a chassis,
            starting from 1.
        Returns:
            An object dervied from SfpBase representing the specified sfp
       """
        sfp = None

        try:
            if (index == 0):
                raise IndexError
            sfp = self._sfp_list[index-1]
        except IndexError:
            sys.stderr.write("override: SFP index {} out of range (1-{})\n".format(
                index, len(self._sfp_list)))

        return sfp
    

    # Provide the functions/variables below for which implementation is to be overwritten

    def get_reboot_cause(self):
        """
        Retrieves the cause of the previous reboot
        Returns:
            A tuple (string, string) where the first element is a string
            containing the cause of the previous reboot. This string must be
            one of the predefined strings in this class. If the first string
            is "REBOOT_CAUSE_HARDWARE_OTHER", the second string can be used
            to pass a description of the reboot cause.
        """
        # Newer baseboard CPLD to get reboot cause from CPLD register
        hw_reboot_cause = ""
        status, hw_reboot_cause = self._getstatusoutput(GET_REBOOT_CAUSE)
        if status != 0:
            pass

        if hw_reboot_cause == "0x77":
            reboot_cause = self.REBOOT_CAUSE_POWER_LOSS
            description = 'Power Cycle Reset'
        elif hw_reboot_cause == "0x66":
            reboot_cause = self.REBOOT_CAUSE_WATCHDOG
            description = 'Hardware Watchdog Reset'
        elif hw_reboot_cause == "0x44":
            reboot_cause = self.REBOOT_CAUSE_NON_HARDWARE
            description = 'CPU Warm Reset'
        elif hw_reboot_cause == "0x33":
            reboot_cause = self.REBOOT_CAUSE_NON_HARDWARE
            description = 'Soft-Set Cold Reset'
        elif hw_reboot_cause == "0x22":
            reboot_cause = self.REBOOT_CAUSE_NON_HARDWARE
            description = 'Soft-Set Warm Reset'
        elif hw_reboot_cause == "0x11":
            reboot_cause = self.REBOOT_CAUSE_POWER_LOSS
            description = 'Power On Reset'
        else:
            reboot_cause = self.REBOOT_CAUSE_HARDWARE_OTHER
            description = 'Hardware reason'

        return (reboot_cause, description)

    def get_change_event(self, timeout=0):
        sfp_dict = {} 
                      
        SFP_REMOVED = '0'
        SFP_INSERTED = '1'
                      
        SFP_PRESENT = True
        SFP_ABSENT = False
                      
        start_time = time.time()
        time_period = timeout/float(1000) #Convert msecs to secs
                      
        while time.time() < (start_time + time_period) or timeout == 0:
            for port_idx in range(1, NUM_SFP+1):
                if self.sfp_status_dict[port_idx] == SFP_REMOVED and \
                    self.get_sfp(port_idx).get_presence() == SFP_PRESENT:                                                                                                                                                            
                    sfp_dict[port_idx] = SFP_INSERTED       
                    self.sfp_status_dict[port_idx] = SFP_INSERTED
                elif self.sfp_status_dict[port_idx] == SFP_INSERTED and \
                    self.get_sfp(port_idx).get_presence() == SFP_ABSENT:
                    sfp_dict[port_idx] = SFP_REMOVED        
                    self.sfp_status_dict[port_idx] = SFP_REMOVED
                      
            if sfp_dict:
                return True, {'sfp':sfp_dict}
                      
            time.sleep(0.5)
                      
        return True, {'sfp':{}} # Timeout 
	
    def get_watchdog(self):
        """ 
        Retreives hardware watchdog device on this chassis
            
        Returns:
            An object derived from WatchdogBase representing the hardware
            watchdog device
        """
        try:
            if self._watchdog is None:
                from sonic_platform.cpld_watchdog import Watchdog
                # Create the watchdog Instance
                self._watchdog = Watchdog()
            
        except Exception as e:                                                                                                                                                                                                       
            print("Fail to load watchdog due to {}".format(e))
        return self._watchdog

    def get_revision(self):
        """
        Retrieves the hardware revision for the chassis
        Returns:
            A string containing the hardware revision for this chassis.
        """
        return self._eeprom.revision_str().encode('utf-8').hex()
