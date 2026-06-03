import requests

BASE_URL = "http://spi3bridge:5000"


def readBytes():
    # See: https://docs.docker.com/compose/how-tos/networking/#default-network-and-service-discovery
    request_url = f"{BASE_URL}/read/bytes"
    response = requests.get(request_url).text
    return response

def readFloats():
    # See: https://docs.docker.com/compose/how-tos/networking/#default-network-and-service-discovery
    request_url = f"{BASE_URL}/read/floats"
    response = requests.get(request_url).text
    return response

def readInts():
    # See: https://docs.docker.com/compose/how-tos/networking/#default-network-and-service-discovery
    request_url = f"{BASE_URL}/read/ints"
    response = requests.get(request_url).text
    return response

def config_speed(hz):
    url = f"{BASE_URL}/config/speed"
    response = requests.post(url, json={"hz": hz})
    return response.json()

def config_mode(mode):
    url = f"{BASE_URL}/config/mode"
    response = requests.post(url, json={"mode": mode})
    return response.json()

def config_bits(bits):
    url = f"{BASE_URL}/config/bits"
    response = requests.post(url, json={"bits": bits})
    return response.json()

def config_bytes_to_read(n):
    url = f"{BASE_URL}/config/bytes"
    return requests.post(url, json={"bytes": n}).json()

