# constants.py
"""
Constants for the Network Monitoring Dashboard
"""

# Column names
BEGIN_TIME = "Begin Time"
END_TIME = "End Time"
TARGET_ME = "Target ME"
MAX_OPTICAL_POWER = "Max Value of Input Optical Power(dBm)"
MIN_OPTICAL_POWER = "Min Value of Input Optical Power(dBm)"
INPUT_OPTICAL_POWER = "Input Optical Power(dBm)"
MAX_MIN_DIFF = "Max - Min (dB)"
OCCURRENCE_TIME = "Occurrence Time"
CLEAR_TIME = "Clear Time"
INSTANT_BER = "Instant BER After FEC"
OUTPUT_OPTICAL_POWER = "Output Optical Power (dBm)"
INPUT_OPTICAL_POWER_ALT = "Input Optical Power(dBm)"

# Menu items
MENU_ITEMS = [
    "Home", "Dashboard", "CPU", "FAN", "MSU", "Line board", "Client board",
    "Fiber Flapping", "Loss between Core", "Loss between EOL", "Preset status", "APO Remnant", "Summary table & report"
]

# Performance settings
DEFAULT_BATCH_SIZE = 1000
MEMORY_OPTIMIZATION_THRESHOLD = 10000
