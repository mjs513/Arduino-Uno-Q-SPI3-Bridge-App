import requests

BASE_URL = "http://spi3bridge:5000"

# -----------------------------
# READ: BYTES
# -----------------------------
def readBytes(n=None):
    url = f"{BASE_URL}/read/bytes"
    if n is not None:
        url += f"?n={n}"
    return requests.get(url).json()

# -----------------------------
# READ: FLOATS
# -----------------------------
def readFloats(n=None):
    url = f"{BASE_URL}/read/floats"
    if n is not None:
        url += f"?n={n}"
    return requests.get(url).json()


# -----------------------------
# READ: INTS
# -----------------------------
def readInts(n=None):
    url = f"{BASE_URL}/read/ints"
    if n is not None:
        url += f"?n={n}"
    return requests.get(url).json()


# -------------------------------
# Write endpoint interface
# --------------------------------
def writeBytes(payload):
    url = f"{BASE_URL}/write/bytes"
    return requests.post(url, json={"payload": payload}).json()

def writeFloats(payload):
    url = f"{BASE_URL}/write/floats"
    return requests.post(url, json={"payload": payload}).json()

def writeInts(payload):
    url = f"{BASE_URL}/write/ints"
    return requests.post(url, json={"payload": payload}).json()

def writeStruct(format_list, values):
    url = f"{BASE_URL}/write/struct"
    return requests.post(url, json={
        "format": format_list,
        "values": values
    }).json()

def writeStructs(struct_list):
    url = f"{BASE_URL}/write/structs"
    return requests.post(url, json={"structs": struct_list}).json()

def writeStructArrayFields(format_dict, values_dict):
    url = f"{BASE_URL}/write/struct_arrayfields"
    return requests.post(url, json={
        "format": format_dict,
        "values": values_dict
    }).json()


# -----------------------------
# CONFIG 
# -----------------------------
def config_speed(hz):
    url = f"{BASE_URL}/config/speed"
    return requests.post(url, json={"hz": hz}).json()

def config_mode(mode):
    url = f"{BASE_URL}/config/mode"
    return requests.post(url, json={"mode": mode}).json()

def config_bits(bits):
    url = f"{BASE_URL}/config/bits"
    return requests.post(url, json={"bits": bits}).json()

def config_bytes_to_read(n):
    url = f"{BASE_URL}/config/bytes"
    return requests.post(url, json={"bytes": n}).json()

def config_command(cmd_type, command):
    url = f"{BASE_URL}/config/cmd/{cmd_type}"
    return requests.post(url, json={"command": command}).json()

def configWriteCommand(cmd_type, command):
    url = f"{BASE_URL}/config/writecmd/{cmd_type}"
    return requests.post(url, json={"command": command}).json()
