
import socket

def check_port(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            print(f"Port {port} on {host} is open!")
            return True
        else:
            print(f"Port {port} on {host} is closed.")
            return False
    except Exception as e:
        print(f"Error checking port: {e}")
        return False
    finally:
        sock.close()

print("Testing if server is listening...")
check_port('127.0.0.1', 3000)
check_port('localhost', 3000)
check_port('0.0.0.0', 3000)
