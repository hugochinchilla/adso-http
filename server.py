#! /usr/bin/env python
# coding: utf-8

import socket
import os
import time

from multiprocessing import Process, Lock, Manager, Semaphore, current_process

from httpd import respuesta as response


class ActivePool(object):
    def __init__(self):
        self.mgr = Manager()
        self.active = self.mgr.list()
        self.lock = Lock()
        
    def get_active(self):
        with self.lock:
            return self.active
        
    def make_active(self, name):
        with self.lock:
            print "%s comes in" % name
            self.active.append(name)
            
    def make_inactive(self, name):
        with self.lock:
            print "%s comes out" % name
            self.active.remove(name)
            
    def __str__(self):
        with self.lock:
            return str(self.active)


class Server(object):
    def __init__(self):
        # self.CONNECTION_OPENED = 'opened'
        # self.CONNECTION_CLOSED = 'closed'
        # self.MAX_REQUESTS_REACHED = 'reached'
        
        self.bind_to = ('127.0.0.1', 8080)
        self.socket = None
        self.start_servers = 2
        self.min_spare_servers = 5
        self.max_spare_servers = 10
        self.max_clients = 250
        self.max_request_per_child = 100
        self.workers = set()
        self.pool = ActivePool()
        self.lock = Semaphore(1)
        
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
        
    def worker_process(self, pool, lock=None):
        this = current_process()
        req_completed = 0
        
        try:
            while True: #req_completed < self.max_request_per_child:
                with lock:
                    conn,addr = self.socket.accept()
                #pool.make_active(this.name)
                
                response(conn)
                conn.close()
                #pool.make_inactive(this.name)
                req_completed += 1
        except Exception, e:
            print "ERROR %s\titer: %s, addr: %s" % (this.name,req_completed,addr)
            raise e

        print "%s: max requests processed" % this.name
        return
            
    def manage_pool(self):
        #print self.pool
        
        """
        for w in self.workers.copy():
            if not w.is_alive():
                w.terminate()
                w.join()
                self.workers.remove(w)
                print "Terminated %s: %s" % (w.name, self.pool)
        """
        """
        while self.count_spare_servers() < self.min_spare_servers:
            self.spawn()
        """
        """
        while self.count_spare_servers() > self.max_spare_servers:
            for w in self.workers:
                if w.name not in self.pool.get_active():
                    w.terminate()
                    w.join()
                    break
        """
            
    def spawn(self):
        w = Process(target=self.worker_process, args=(self.pool, self.lock))
        w.daemon = True
        print self.workers
        w.start()
        self.workers.add(w)
        print "Nuevo proceso: ", w.name
        
    def count_spare_servers(self):
        return len(self.workers) - len(self.pool.get_active())

if __name__ == '__main__':
    server = Server()
    server.serve()
