#!/bin/bash
# Set SYS_LED to Green, assuming everything came up fine.
#ipmitool raw 0x3A 0x0C 0x00 0x03 0x62 0xdc

# Enable thermal shutdown by default
#i2cset -y -f 103 0x0d 0x75 0x1
