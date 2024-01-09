import os

try:
    from sonic_platform_pddf_base.pddf_fan import PddfFan
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

class Fan(PddfFan):
    """PDDF Platform-Specific Fan class"""

    def __init__(self, tray_idx, fan_idx=0, pddf_data=None, pddf_plugin_data=None, is_psu_fan=False, psu_index=0):
        # idx is 0-based 
        PddfFan.__init__(self, tray_idx, fan_idx, pddf_data, pddf_plugin_data, is_psu_fan, psu_index)

    def get_presence(self):
        """
          Retrieves the presence of fan
        """
        if self.is_psu_fan:
            from sonic_platform.platform import Platform
            return Platform().get_chassis().get_psu(self.fans_psu_index-1).get_presence()

        return super().get_presence() and self.get_status()
   
    def get_direction(self):
        """
          Retrieves the direction of fan
 
          Returns:
               A string, either FAN_DIRECTION_INTAKE or FAN_DIRECTION_EXHAUST
               depending on fan direction
               Or N/A if fan removed or abnormal
        """
        if not self.get_status():
           return 'N/A'
 
        return super().get_direction()


    def get_target_speed(self):
        """
        Retrieves the target (expected) speed of the fan

        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
                 to 100 (full speed)
        """
        target_speed = 0
        if self.is_psu_fan:
            # Target speed not usually supported for PSU fans
            raise NotImplementedError
        else:
            fan_name = self.get_name()
            f_r_fan = "Front" if fan_name.endswith("1") else "Rear"
            speed_rpm = self.get_speed_rpm()
            max_fan_rpm = eval(self.plugin_data['FAN']['FAN_MAX_RPM_SPEED'][f_r_fan])
            speed_percentage = round(int((speed_rpm * 100) / max_fan_rpm))
            target_speed = speed_percentage

        return target_speed

    def get_speed(self):
        """
        Retrieves the speed of fan as a percentage of full speed

        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
                 to 100 (full speed)
        """
        fan_name = self.get_name()
        if self.is_psu_fan:
            attr = "psu_fan{}_speed_rpm".format(self.fan_index)
            device = "PSU{}".format(self.fans_psu_index)
            output = self.pddf_obj.get_attr_name_output(device, attr)
            if not output:
                return 0

            output['status'] = output['status'].rstrip()
            if output['status'].isalpha():
                return 0
            else:
                speed = int(float(output['status']))

            max_speed = int(self.plugin_data['PSU']['PSU_FAN_MAX_SPEED'])
            speed_percentage = round((speed*100)/max_speed)
            if speed_percentage >= 100:
                speed_percentage = 100
            return speed_percentage
        else:
            idx = (self.fantray_index-1)*self.platform['num_fans_pertray'] + self.fan_index
            attr = "fan" + str(idx) + "_input"
            output = self.pddf_obj.get_attr_name_output("FAN-CTRL", attr)

            if not output:
                return 0

            output['status'] = output['status'].rstrip()
            if output['status'].isalpha():
                return 0
            else:
                speed = int(float(output['status']))

            f_r_fan = "Front" if fan_name.endswith("1") else "Rear"
            max_speed = eval(self.plugin_data['FAN']['FAN_MAX_RPM_SPEED'][f_r_fan])
            speed_percentage = round((speed*100)/max_speed)
            if speed_percentage >= 100:
                speed_percentage = 100

            return speed_percentage

    def get_status_led(self):
        if not self.get_presence():
            return self.STATUS_LED_COLOR_OFF
        if self.is_psu_fan:
            # Usually no led for psu_fan hence raise a NotImplementedError
            raise NotImplementedError
        else:
            fan_led_device = "FANTRAY{}".format(self.fantray_index) + "_LED"
            if (not fan_led_device in self.pddf_obj.data.keys()):
                # Implement a generic status_led color scheme
                if self.get_status():
                    return self.STATUS_LED_COLOR_GREEN
                else:
                    return self.STATUS_LED_COLOR_OFF

            result, color = self.pddf_obj.get_system_led_color(fan_led_device)
            return (color)

