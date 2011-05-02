#! /usr/bin/env python
# coding: utf-8

import socket
import os
import time

import multiprocessing
from multiprocessing import Process, Manager

from httpd import respuesta as response


class ActivePool(object):
    def __init__(self):
        self.mgr = multiprocessing.Manager()
        self.active = self.mgr.list()
        self.lock = multiprocessing.Lock()
        
    def get_active(self):
        with self.lock:
            return self.active
        
    def make_active(self, name):
        with self.lock:
            self.active.append(name)
            
    def make_inactive(self, name):
        with self.lock:
            self.active.remove(name)
            
    def __str__(self):
        with self.lock:
            return str(self.active)


class Server(object):
    def __init__(self):
        self.bind_to = ('127.0.0.1', 8080)
        self.socket = None
        self.start_servers = 5
        self.max_spare_servers = 5
        self.min_spare_servers = 2
        self.max_clients = 250
        self.max_request_per_child = 100
        self.workers = set()
        self.pool = ActivePool()
        self.semaphore = multiprocessing.Semaphore(1)
        
    def serve(self):
        self.init_socket()
        
        for i in range(self.start_servers):
            self.spawn()
            
        while True:
            self.manage_pool()
        
    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.bind_to)
        self.socket.listen(1)
        
    def worker_process(self, pool, semaphore):
        name = multiprocessing.current_process().name
        req_completed = 0
        while req_completed < self.max_request_per_child:
            req_completed += 1
            with semaphore:
                conn,addr = self.socket.accept()
                pool.make_active(name)
            response(conn)
            conn.close()
            #print "%s - request completed %s/%s" % (name,req_completed,self.max_request_per_child)
            pool.make_inactive(name)
            
    def manage_pool(self):
        #print self.pool
        
        for w in self.workers.copy():
            with self.semaphore:
                if not w.is_alive():
                    #w.terminate()
                    w.join()
                    self.workers.remove(w)
                    print self.pool
                    print "Terminated %s" % w.name
        
        while self.count_spare_servers() < self.min_spare_servers:
            self.spawn()
        
        """
        while self.count_spare_servers() > self.max_spare_servers:
            for w in self.workers:
                with self.semaphore:
                    if w.name not in self.pool.active:
                        w.terminate()
                        w.join()
                        break
        """
            
    def spawn(self):
        w = Process(target=self.worker_process, args=(self.pool, self.semaphore))
        w.daemon = True
        w.start()
        with self.semaphore:
            self.workers.add(w)
        print "Nuevo proceso: ", w.pid
        
    def count_spare_servers(self):
        with self.semaphore:
            return len(self.workers) - len(self.pool.get_active())

if __name__ == '__main__':
    server = Server()
    server.serve()
