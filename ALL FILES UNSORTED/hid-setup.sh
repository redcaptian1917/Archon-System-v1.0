#!/bin/bash
# This script sets up a composite USB device: Keyboard + Mouse

# To create script File run:
# sudo nano /usr/local/bin/hid-setup.sh

# To make executable run:
# sudo chmod +x /usr/local/bin/hid-setup.sh

# 1. Create the gadget
mkdir -p /sys/kernel/config/usb_gadget/g1
cd /sys/kernel/config/usb_gadget/g1

# 2. Set IDs (Spoofing a Logitech Unifying Receiver for compatibility)
echo 0x046d > idVendor  # Logitech
echo 0xc52b > idProduct # Unifying Receiver
echo 0x0200 > bcdUSB

# 3. Create strings (identifies the device)
mkdir -p strings/0x409
echo "archon-hid-001" > strings/0x409/serialnumber
echo "Logitech" > strings/0x409/manufacturer
echo "USB Receiver" > strings/0x409/product

# 4. Create Keyboard Function (hid.g0)
mkdir -p functions/hid.g0
echo 1 > functions/hid.g0/protocol    # Keyboard
echo 1 > functions/hid.g0/subclass   # Boot Interface
echo 8 > functions/hid.g0/report_length
# Standard 6-key rollover keyboard descriptor
echo -ne "\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x03\x95\x05\x75\x01\x05\x08\x19\x01\x29\x05\x91\x02\x95\x01\x75\x03\x91\x03\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0" > functions/hid.g0/report_desc

# 5. Create Mouse Function (hid.g1)
mkdir -p functions/hid.g1
echo 1 > functions/hid.g1/protocol    # Mouse (use 1 for boot protocol)
echo 2 > functions/hid.g1/subclass   # Boot Interface
echo 4 > functions/hid.g1/report_length
# Standard 3-button mouse descriptor (relative position)
echo -ne "\x05\x01\x09\x02\xa1\x01\x09\x01\xa1\x00\x05\x09\x19\x01\x29\x03\x15\x00\x25\x01\x95\x03\x75\x01\x81\x02\x95\x01\x75\x05\x81\x03\x05\x01\x09\x30\x09\x31\x15\x81\x25\x7f\x75\x08\x95\x02\x81\x06\xc0\xc0" > functions/hid.g1/report_desc

# 6. Create configuration
mkdir -p configs/c.1/strings/0x409
echo "Keyboard+Mouse" > configs/c.1/strings/0x409/configuration
echo 120 > configs/c.1/MaxPower

# 7. Link functions to config
ln -s functions/hid.g0 configs/c.1
ln -s functions/hid.g1 configs/c.1

# 8. Activate the gadget by binding it to the UDC
# Find the first available UDC (USB Device Controller)
echo $(ls /sys/class/udc | head -n1) > UDC