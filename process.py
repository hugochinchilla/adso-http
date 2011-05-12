#! /usr/bin/env python
# coding: utf-8


import socket
import os
from stat import *
import sendfile
from multiprocessing import Process, Queue, current_process


document_root = "/home/gallir/Docencia/AdmSO/www"

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
				size = os.stat(filename)[ST_SIZE]
				OUT.write("HTTP/1.0 200 Va be\r\n")
				OUT.write("Content-Length: %d\r\n\r\n" % size)
				OUT.flush()
				sendfile.sendfile(OUT.fileno(), FILE.fileno(), 0, size)

			except IOError:
				OUT.write("HTTP 404 Fichero no existe\r\n")
				#print "Error con", filename
	except Exception, e:
			print "Error en la conexión", e
	OUT.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind(("", 8080))
s.listen(1)

def run_server(q):
	i = 0
	p = current_process()
	while True:
		try:
			conn, addr = s.accept()
			#print "Conexión desde:", addr, "PID:", os.getpid()
			try:
				respuesta(conn)
			except:
				pass
			conn.close()
			i += 1
			if i == 1000:
				q.put(p.pid)
				break
		except socket.error:
			pass

pids = set()
workers = {}
q = Queue()
while True:
	for i in range(5 - len(pids)):
		p = Process(target=run_server, args=(q,))
		p.start()
		pids.add(p.pid)
		workers[p.pid] = p
		print "Nuevo proceso: ", p.pid

	pid = q.get(True)
	workers[pid].join()
	pids.remove(pid)
	del(workers[pid])
	print "acabó:", pid

