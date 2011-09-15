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
        self.workers = self.mgr.list()
        self.active = self.mgr.list()
        self.sem = Semaphore(1)
        self.debug = False
        
    def get_workers(self):
        with self.sem:
            return self.workers
        
    def get_active(self):
        with self.sem:
            return self.active
        
    def count_spare(self):
        with self.sem:
            return len(self.workers) - len(self.active)
        
    def add(self, name):
        with self.sem:
            self.workers.append(name)
            
    def remove(self, name):
        with self.sem:
            self.workers.remove(name)
        
    def make_active(self, name):
        with self.sem:
            self.active.append(name)
            if self.debug:
                print "%s comes in" % name
            
    def make_inactive(self, name):
        with self.sem:
            self.active.remove(name)
            if self.debug:
                print "%s comes out" % name
            
    def __str__(self):
        with self.sem:
            return str(self.active)


class Server(object):
    def __init__(self):
        # self.CONNECTION_OPENED = 'opened'
        # self.CONNECTION_CLOSED = 'closed'
        # self.MAX_REQUESTS_REACHED = 'reached'
        
        self.bind_to = ('127.0.0.1', 8080)
        self.socket = None
        self.start_servers = 5
        self.min_spare_servers = 10
        self.max_spare_servers = 20
        self.max_clients = 250
        self.max_request_per_child = 10
        self.workers = set()
        self.pool = ActivePool()
        self.lock = Semaphore(1)
        
    def start(self):
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
            while req_completed < self.max_request_per_child:
                #with lock:
                conn,addr = self.socket.accept()
                pool.make_active(this.name)
                
                response(conn)
                conn.close()
                pool.make_inactive(this.name)
                req_completed += 1
                print "%s served the response (%s/%s)" % (this.name, req_completed, self.max_request_per_child)
        except Exception, e:
            print "ERROR %s\titer: %s, addr: %s" % (this.name,req_completed,addr)
            raise e
        finally:
            print "%s: max requests processed" % this.name
            if this.name in pool.get_active():
                pool.make_inactive(this.name)
            pool.remove(this.name)
            return
            
    def manage_pool(self):       
        time.sleep(0.1)
        for w in self.workers.copy():
            if not w.is_alive():
                self.workers.remove(w)
                w.join()
                
        while self.pool.count_spare() < self.min_spare_servers:
            self.spawn()
            
        while self.pool.count_spare() > self.max_spare_servers:
            for w in self.workers:
                if w.name not in self.pool.get_active():
                    w.terminate()
                    self.pool.remove(w.name)
                    w.join()
                    break

        print len(self.workers)

    def spawn(self):
        w = Process(target=self.worker_process, args=(self.pool, self.lock))
        w.daemon = True
        self.workers.add(w)
        self.pool.add(w.name)
        w.start()
        print "Nuevo proceso: ", w.name
        

if __name__ == '__main__':
    server = Server()
    server.start()
