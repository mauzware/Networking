import sys
import socket
import getopt
import threading
import subprocess

listen = False
command = False
upload = False
execute = ""
target = ""
upload_destination = ""
port = 0

def usage():
	"""CLI Usage"""
	
	print("netcat.py")
	print("Usage: netcat.py -t target -p port")
	print("-l, --listen			-listen on [host]:[port] for incoming connections")
	print("-e, --execute=file_to_run	-execute the given file upon receiving a connection")
	print("-c, --command			-initialize a command shell")
	print("u, --upload=destination		-upon receiving connection upload a file and write to [destination]")
	print("Examples:")
	print("netcat.py -t 192.168.1.0 -p 5555 -l -c")
	print("netcat.py -t 192.168.1.0 -p 5555 -l -u=c:\\target.exe")
	print("netcat.py -t 192.168.1.0 -p 5555 -l -e=\"cat /etc/passwd"")
	print("echo 'ABCDEFGHIJ' | netcat.py -t 192.168.1.0 -p 5555")
	sys.exit(0)
	
def main():
	"""Reading commands"""
	
	global listen
	global port
	global execute
	global command
	global upload_destination
	global target
	
	#read commandline options
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:cu:", ["help", "listen", "execute", "target", "port", "command", "upload"])
		
	except getopt.GetoptError as e:
		print(str(e))
		usage()
		
	for o,a in opts:
		if o in ("-h", "--help"):
			usage()
			
		elif o in ("-l", "--listen"):
			listen = True
			
		elif o in ("-e", "--execute"):
			execute = a
			
		elif o in ("-c", "--command"):
			command = True
			
		elif o in ("-u", "--upload"):
			upload_destination = a
			
		elif o in ("-t", "--target"):
			target = a
			
		elif o in ("-p", "--port"):
			port = int(a)
			
		else:
			assert False, "Unhandled Option"
			
	#is it going to listen or just send data from stdin?
	if not listen and len(target) and port > 0:
		
		#read in buffer from commandline; this will block so send CTRL+D if not sending input to stdin
		buffer = sys.stdin.read()
		client_sender(buffer) #send data off
		
	#listen, upload things, execute commands and drop shell back
	if listen:
		server_loop()
		
def client_sender(buffer):
	"""Checks if input was received, ships it off to remote target and receives data back until there is no more data to receive"""
	
	client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	try:
		#connect to target host
		client.connect((target, port))
		
		if len(buffer):
			client.send(buffer)
			
			while True:
				#now wait for data back
				recv_len = 1
				response = ""
				
				while recv_len:
					data = client.recv(4096)
					recv_len = len(data)
					response += data
					
					if recv_len < 4096:
						break
				
				print(response)
				
				#wait for more input
				buffer = raw_input("")
				buffer += "\n"
				client.send(buffer) #sends it off
				
	except:
		print("[*] Exception! Exiting!")
		client.close() #closes connection
			
def server_loop():
	"""Basically creates TCP server, you already made one"""
	
	global target
	
	#if no target is defined, listen on all interfaces
	if not len(target):
		target = "0.0.0.0"
		
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((target, port))
	server.listen(5)
	
	while True:
		client_socket, addr = server.accept()
		
		#spin off a thread to handle new client
		client_thread = threading.Thread(target=client_handler, args=(client_socket,))
		client_thread.start()
	
def run_command(command):
	"""Runs whatever command is passed"""
	
	#trim the newline
	command = command.strip()
	
	#run the command and the output back
	try:
		output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
		
	except:
		output = "Failed to execute command. \r\n"
		
	return output #sends the output back
	
def client_handler(client_socket):
	"""1st It checks whether the network tool is set to receive the file
	   2nd Receives the file, opens it and writes out the content
	   3rd Processes execute functionality and handles command
	"""
	
	global upload
	global execute
	global command
	
	#check for upload
	if len(upload_destination):
		#read in all of the bytes and write to destination
		file_buffer = ""
		
		#keep reading data until non is available
		while True:
			data = client_socket.recv(1024)
			
			if not data:
				break
				
			else:
				file_buffer += data
				
		#now takes these bytes and tries to write them out
		try:
			file_descriptor = open(upload_destination, "wb")
			file_descriptor.write(file_buffer)
			file_descriptor.close()
			
			#acknowledge that it wrote the file out
			client_socket.send("[!] Successfully saved file to %s\r\n" % upload_destination)
			
		except:
			client_socket.send("[-] Failed to save the file to %s\r\n" % upload_destination)
			
	#check for command execution
	if len(execute):
		#run the command
		output = run_command(execute)
		client_socket.send(output)
		
	#now it goes into another loop if a command shell was requested
	if command:
		while True:
			#show a simple prompt
			client_socket.send("<CMD:#> ")
			
			#now it receives until you see a linefeed (enter key)
			cmd_buffer = ""
			while "\n" not in cmd_buffer:
				cmd_buffer += client_socket.recv(1024)
				
			#send back the command output
			response = run_command(cmd_buffer)
			
			#send back the response
			client_socket.send(response) 

main()
