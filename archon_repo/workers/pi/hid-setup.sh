#!/bin/bash
# -----------------------------------------------------------------
# ARCHON SYSTEM - HARDWARE AGENT SETUP SCRIPT (vFINAL)
#
# This script configures the Raspberry Pi Zero (or similar)
# to act as a USB Human Interface Device (HID) Gadget.
#
# It creates a "Composite Device" that appears to the host
# computer as *both* a keyboard and a mouse.
#
# It spoofs a Logitech Unifying Receiver for OPSEC.
# -----------------------------------------------------------------

set -e

# --- 1. Define Device Parameters ---
# We are spoofing a Logitech Unifying Receiver
VID="0x046d"
PID="0xc52b"
SERIAL="ARCHON-HID-001"
MANUFACTURER="Logitech"
PRODUCT="USB Receiver"

# Define the gadget directory
GADGET_DIR="/sys/kernel/config/usb_gadget/g1"

# --- 2. Create the Gadget Structure ---
# This creates the main gadget directory.
echo "[+] Creating HID gadget directory..."
mkdir -p $GADGET_DIR
cd $GADGET_DIR

# --- 3. Set Device IDs (The "Spoof") ---
# Write the Logitech Vendor/Product IDs
echo $VID > idVendor
echo $PID > idProduct
echo 0x0200 > bcdUSB # USB 2.0

# --- 4. Set Device Strings (The "Identity") ---
echo "[+] Setting device identity strings..."
mkdir -p strings/0x409
echo $SERIAL > strings/0x409/serialnumber
echo $MANUFACTURER > strings/0x409/manufacturer
echo $PRODUCT > strings/0x409/product

# --- 5. Configure the Keyboard Function (hid.g0) ---
echo "[+] Configuring Keyboard Function (hid.g0)..."
mkdir -p functions/hid.g0
echo 1 > functions/hid.g0/protocol    # 1 = Keyboard
echo 1 > functions/hid.g0/subclass   # 1 = Boot Interface Subclass
echo 8 > functions/hid.g0/report_length # 8 bytes for standard 6-key rollover
# This is the raw USB Report Descriptor for a standard 6-key keyboard
echo -ne "\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x03\x95\x05\x75\x01\x05\x08\x19\x01\x29\x05\x91\x02\x95\x01\x75\x03\x91\x03\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0" > functions/hid.g0/report_desc

# --- 6. Configure the Mouse Function (hid.g1) ---
echo "[+] Configuring Mouse Function (hid.g1)..."
mkdir -p functions/hid.g1
echo 1 > functions/hid.g1/protocol    # 1 = Mouse (for boot protocol)
echo 2 > functions/hid.g1/subclass   # 2 = Boot Interface Subclass
echo 4 > functions/hid.g1/report_length # 4 bytes for (Buttons, X, Y, Wheel)
# This is the raw USB Report Descriptor for a 3-button, relative-position mouse
echo -ne "\x05\x01\x09\x02\xa1\x01\x09\x01\xa1\x00\x05\x09\x19\x01\x29\x03\x15\x00\x25\x01\x95\x03\x75\x01\x81\x02\x95\x01\x75\x05\x81\x03\x05\x01\x09\x30\x09\x31\x15\x81\x25\x7f\x75\x08\x95\x02\x81\x06\xc0\xc0" > functions/hid.g1/report_desc

# --- 7. Create and Link the Configuration ---
# This ties both the keyboard and mouse to one configuration
echo "[+] Linking functions to configuration..."
mkdir -p configs/c.1/strings/0x409
echo "Keyboard+Mouse Composite Device" > configs/c.1/strings/0x409/configuration
echo 120 > configs/c.1/MaxPower # 120 mA

# Link the functions
ln -s functions/hid.g0 configs/c.1
ln -s functions/hid.g1 configs/c.1

# --- 8. Activate the Gadget ---
# This binds the gadget to the USB Device Controller (UDC)
# and makes it "live" to the host PC.
echo "[+] Activating USB Gadget..."
# Find the first available UDC (e.g., 'dwc2_a_udc' or similar)
echo $(ls /sys/class/udc | head -n1) > UDC

echo "[SUCCESS] Archon HID Gadget is now live."
echo "  Keyboard: /dev/hidg0"
echo "  Mouse:    /dev/hidg1"
