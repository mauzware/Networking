import socket

target_host = "<INSERT_IP>"
target_port = 80

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.sendto("AAABBBCCCDDD", (target_host, target_port))
data, addr = client.recvfrom(4096)
print(data)
