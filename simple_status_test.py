
import socket
import json

# Create a simple socket connection to test the server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)

try:
    print("Connecting to 127.0.0.1:3000...")
    sock.connect(("127.0.0.1", 3000))
    print("Connected!")
    
    # Send a simple GET request for /api/status
    request = b"GET /api/status HTTP/1.1\r\nHost: 127.0.0.1:3000\r\nConnection: close\r\n\r\n"
    sock.sendall(request)
    
    # Read the response
    response = b""
    while True:
        data = sock.recv(4096)
        if not data:
            break
        response += data
    
    print("Response received!")
    # Print the response
    print("\n--- Full response:")
    print(response.decode('utf-8', errors='ignore'))
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    sock.close()
