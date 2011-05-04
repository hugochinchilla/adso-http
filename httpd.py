#! /usr/bin/env python
# coding: utf-8


import socket
import os
from stat import *
import sendfile
import mimetypes
from settings import DOCUMENT_ROOT as document_root

def respuesta(sock):
	try:
		OUT = sock.makefile()
		http_command = OUT.readline()
		
		headers = []
		command = http_command.split()
		#print "Commando:", command
		for line in OUT:
			if line.strip() == "": break
			headers.append(line)
		if command[0] == "GET":
			if command[1] == "/":
				filename = document_root + "/index.html"
			else:
				filename = document_root + command[1]
			try:
				FILE = open(filename, "rb")
				#print "Sending", filename
				OUT.write("HTTP/1.0 200 Va be\r\n")
				last_modified = os.stat(filename)[ST_MTIME]
				OUT.write("Last-Modified: %s \r\n" % last_modified)
				content_type = mimetypes.guess_type(filename)
				OUT.write("Content-Type: %s\r\n" % content_type[0])
				size = os.stat(filename)[ST_SIZE]
				OUT.write("Content-Length: %s\r\n\r\n" % size)

				OUT.flush()
				sendfile.sendfile(OUT.fileno(), FILE.fileno(), 0, size)
					
			except IOError:
				OUT.write("HTTP 404 Fichero no existe\r\n")
				print "Error con", filename
	except TypeError,e:  #Exception, e:
			print "Error en la conexión", e
	OUT.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind(("", 10000))
s.listen(1)

pids = set()

def start_server():
	pid = os.fork()
	if pid == 0:
		i = 0
		while True:
			try:
				conn, addr = s.accept()
				#print "Conexión desde:", addr, "PID:", os.getpid()
				respuesta(conn)
				conn.close()
				i += 1
				if i == 1000: exit(0)
			except socket.error: 
				pass
	else:
		return pid

"""
while True:
	for i in range(5 - len(pids)):
		pid = start_server()
		pids.add(pid)
		print "Nuevo proceso: ", pid
	
	try:
		(pid, status, rusage) = os.wait3(0)
		if pid > 0: 
			pids.remove(pid)
	except OSError: pass

	print "acabó:", pid, "status:", status

"""
