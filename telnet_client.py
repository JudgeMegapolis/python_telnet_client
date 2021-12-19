#!/usr/bin/env python3
import sys
import os
import os.path
import re
import telnetlib
import getpass
import time
import getopt
import base64

#global debug
#debug = True

global download
download = False

def telnet_connect(host, port, user, password, command_lines, output_file):
	debug = True
	
	try:
		t = telnetlib.Telnet(host, port)
	except Exception as error:
		end(6, "Connection refused!")
	
	prompts = [b'\#', b'\>'] # NOTE: A space is not a prompt. A space is virtually in every message returned, independant of the message's meaning.
	# space is a prompt.
	
	t.open(host)
	
	if debug:
		t.set_debuglevel(1)
	
	l = t.expect([b'ogin', b'sername'], 10)
	
	if l[0] == -1:
		t.close()
		end(1, "No login prompt!")
	
	t.write(user.encode('utf-8'))
	t.write(b'\r\n')
	
	#if debug:
	#	print(t.read_very_lazy().decode('utf-8'))
	
	l = t.expect([b'assword'], 10)
	if l[0] == -1:
		t.close()
		end(2, "No password prompt!")
	
	t.write(password.encode('utf-8'))
	t.write(b'\r\n')
	
	#if debug:
	#	print(t.read_very_lazy().decode('utf-8'))
	
	n = t.expect([b'\:'], 10)
	output = " "

	if(download):
		f = open(output_file, "wb")
	else:
		f = open("telnet_output.txt", "w")
		
	# TODO: Change to check for "sername" and prompt instead, since the output of zhones doesn't only use ":" by default when a successful login happened.
	#	If "sername" is received, its a bad login, if its a prompt, good login. A timeout means you got the wrong prompt. (Make sure the timeout is the same then the lockout timeout of zhones)
	#	Yes some prompts are really weird, the ones like: "someword ", however, those can still be handled this way. And once you know you have the wrong prompt, you can extract it using this strategy.
	if n[0] == 0: # check if semicolon was recv in output after trying to login
		t.close()
		end(3, "Login failed!")
	else:
		t.write(b'\r\n') # NOTE: telnet requires \n or \r at the end of a message to recognise that the user input has ended, just like any shell.
		pe = t.expect(prompts, 10)
		if pe[0] != -1: # make sure we do recv a valid prompt
			print("Connected.")
			for line in command_lines:
				# BONUS TODO: if the commands provided do not allow us to gain a bash shell, we may want to employ our 0days to do so instead.
				#if downloadEndCommands is not None: # TODO: Implement download mode.
				#	print("Special things are to be done here.") # no. you arent my mom.
				t.write(b'\r\n')
				sh_prompt = [b'\#', b'\>', b'\:']
				busybox = [b'\~ #']
				ce = t.expect(sh_prompt, 10)
				if(ce[0] != -1):
					print("Sleeping for one second")
					time.sleep(1)
					print("Running command {}".format(line))
					if(line == "sh"):
						print("Waiting for shell prompt")
						string = line + '\r\n'
						byte_command = bytes(string, 'utf-8')
						t.write(byte_command)
						t.write(b'\r\n')
						t.expect(busybox, 10)						
					else:
						time.sleep(1)
						string = line + '\r\n'
						byte_command = bytes(string, 'utf-8')
						t.write(byte_command)
						t.write(b'\r\n')
			if(download):
				output = decode_base64(t.read_all().decode('utf-8'))
			else:
				output = t.read_all().decode('utf-8')
			f.write(output)					
				# TODO: check if command passed, aka check for prompt before sending next command. If not found, exit with error. This prevents a DoS on the device & allows us to not waste our time if the shell connection is shot somehow.
			print("Comand execution done.")
			#if output_file != "" and downloadEndCommands is None:
			#if output_file != "":
			#	data = t.read_all().decode('utf-8') # TODO: Save output as it comes in, this allows you to avoid saving junk stuff like the login banner etc & produces a clean log that is easy to read & simple to parse.
			#	t.close()
			#	write_file(output_file, data)
			#sys.exit(0)
	t.close()
	f.close()
	sys.exit()
	end(4, "Prompt check failed!")

# Function to convert  
def list_tostr(string): 
    
    # initialize an empty string
    final_str = "" 
    
    # traverse in the string  
    for list_value in string: 
        final_str += list_value
    
    # return string  
    return final_str

def decode_base64(b64_string):
	find = re.findall(r'<foo2>(.*?)</foo2>', b64_string)
	string = list_str(find)
	base64_bytes = string
	message_bytes = base64.standard_b64decode(base64_bytes) # base64 returns the decoded values in the stupid byte datatype

	return message_bytes

# this function is so we can read the file with the commands for telnet
def read_file(fileName):
	final_list = []
	fd = open(fileName, mode="r", encoding="utf-8")
	file_list = fd.readlines() # read whole file putting each line in its own place in a list
	fd.close()
	
	for i in file_list:
		final_list.append(i.strip()) # strip newline
	
	return final_list # we return the list of commands

def upload_file(fileName, output_file):
	commands = []
	commands.append("rm -rf " + output_file)
	with open(fileName, "r") as f:
		while chunk := f.read(77 * 5):
			commands.append("echo \"" + chunk.strip() + "\" >> " + output_file + "\n")
	f.close
	return commands

def download_file(output_file):
	tar_file = output_file + ".tar.gz"
	b64_file = output_file + "_b64" 
	commands = []
	commands.append("cd /var/tmp")
	commands.append("rm -rf " + tar_file)
	commands.append("rm -rf " + b64_file)
	commands.append("tar -czf " + tar_file  + " " + output_file)
	commands.append("openssl base64 -in " + tar_file + " -out " + b64_file)
	commands.append("sed -i -e 's/^/<foo2>/' " + b64_file)
	commands.append("sed -i 's/.*/&<\/foo2>/' " + b64_file)
	commands.append("len=$(sed -n '$=' " + b64_file + ")")
	#commands.append("echo \"<foo>\"")
	commands.append("c=$(($len/900)); x=0; y=0; while [ $x -le $c ]; do  head -n $(( $x * 900)) " + b64_file + " | tail -n 900; x=$(($x+1)); done; if [ \"$(($len % 900))\" -ne 0 ]; then tail -n \"$(($len % 900))\" " + b64_file + ";fi")
	commands.append("sleep 30")
	#commands.append("echo \"</foo>\"")
	commands.append("rm -rf " + tar_file)
	commands.append("rm -rf " + b64_file)
	return commands
     
# func to write the output from telnet to a file
def write_file(fileName, data):
	fd = open(fileName, mode="w", encoding="utf-8")
	if fd:
		fd.write(data)
	else:
		end(5, "Cannot write data to " + fileName + "!")
	
	fd.close() # NOTE: If you don't close the file descriptor, it stays open. (Can create problems further down the road & wastes resources)

USAGE = "Purpose: Automate tasks over a telnet channel such as file transfers & command execution.\nUsage: telnet_client.py <-h help>\n - <-e execute commands> <ip[:port]> <user:password> <file1[,file2]> [output file]\n - <-u upload> <ip[:port]> <user:password> <file1[,file2]> <source file> <output file>\n - <-d download> <ip[:port]> <user:password> <file1[,file2]> <source file> <output file>"

def end(code, message): # Exit handling to simplify it.
	if (code != 0):
		print(message)
	print(USAGE)
	sys.exit(code)

def checkFile(fileName):
	if os.path.isfile(fileName) == False:
		end(3, "Bad input file in checkfile!")
	return fileName

def parseArgStart(args):
	if ":" in args[0]:
		ip = args[0].split(':')[0]
		port = int(args[0].split(':')[1])
	else:
		ip = args[0]
		port = 23
	
	username = args[1].split(':')[0]
	password = args[1].split(':')[1]
	
	command_start = read_file(checkFile(args[2].split(',')[0]))
	command_end = read_file(checkFile(args[2].split(',')[1]))

	return (ip, port, username, password, command_start, command_end)

if __name__ == '__main__':
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], "heud", ["help"])
	except getopt.GetoptError as error:
		end(1, error)
	if len(sys.argv) == 1:
			end(0, "help")
	elif len(sys.argv) < 4:
		end(1, "Missing arguments")
	for o, arg in opts:
		if o in ("-h", "--help"):
			end(0, "help")
		elif o in ("-e", "--execute"):
			# <-e execute commands> <ip[:port]> <user:password> <file1[,file2]> [output file]
			try: # Was lazy
				(ip, port, username, password, command_start, command_end) = parseArgStart(args)

				output_file = args[3]
				# TODO: Maybe add a check if folder is valid?
				command_lines = command_start
				for line in command_end:
					command_lines.append(line)
				
				telnet_connect(ip, port, username, password, command_lines, output_file)
			except Exception as error:
				end(2, "Bad input in args!")
			sys.exit(0)
		elif o in ("-u", "--upload"):
			# <-u upload> <ip[:port]> <user:password> <file1[,file2]> <source file> <output file>
			try: # Was lazy
				(ip, port, username, password, command_start, command_end) = parseArgStart(args)
				
				source_file = checkFile(args[3])
				
				output_file = args[4]
							
				command_lines = command_start

				#for line in command_lines:
				#	print(line)
				
				#sys.exit()
				
				
				#for line in  upload_file(source_file, output_file):
				#	command_lines.append(line)
					#command_lines.extend(line)

				command_lines += upload_file(source_file, output_file)

				#for line in command_lines:
				#	print(line)
				
				#sys.exit()
				
				for line in command_end:
					command_lines.append(line)

				#for line in command_lines:
				#	print(line)

				#sys.exit()
				
				telnet_connect(ip, port, username, password, command_lines, "")
			except Exception as error:
				end(2, "Bad input!")
				sys.exit(0)
		elif o in ("-d", "--download"):
			# <-d download> <ip[:port]> <user:password> <file1[,file2]> <source file> <output file>
			#try: # Was lazy
				(ip, port, username, password, command_start, command_end) = parseArgStart(args)
				
				source_file = args[3]
				output_file = args[4]

				command_lines = command_start

				command_lines += download_file(source_file)

				#for line in command_lines:
				#	print(line)
				
				#sys.exit()
				
				for line in command_end:
					command_lines.append(line)

				#for line in command_lines:
				#	print(line)

				#sys.exit()

				download = True
				
				# TODO: Maybe add a check if folder is valid?
				telnet_connect(ip, port, username, password, command_lines, output_file)
			#except Exception as error:
			#	end(2, "Bad input!")
			#	sys.exit(0)
		elif o in ("-i", "--infect"):
			# <-i infect> <ip[:port]> <user:password> <source file> <output location> # Uses dynamically generated commands to allow for: random output file name, automated execution & automated unpackaging.
			try: # Was lazy
				(ip, port, username, password, command_start, command_end) = parseArgStart(args)
				
				# Will be done when all the rest is done, because it depends on the other commands to work.
				
			except Exception as error:
				end(2, "Bad input!")
	end(2, "Bad input!") # If no good commands.
