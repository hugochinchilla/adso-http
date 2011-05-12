#! /usr/bin/env python
# coding: utf-8

import socket
import os
import time

from Queue import Empty
from multiprocessing import Process, Manager, Semaphore, Queue, current_process

from httpd import respuesta as response


class ActivePool(object):
    def __init__(self):
        self.mgr = Manager()
        self.active = self.mgr.list()
        self.sem = Semaphore(1)
        
    def get_active(self):
        with self.sem:
            return self.active
        
    def make_active(self, name):
        with self.sem:
            #print "%s comes in" % name
            self.active.append(name)
            
    def make_inactive(self, name):
        with self.sem:
            #print "%s comes out" % name
            self.active.remove(name)
            
    def __str__(self):
        with self.sem:
            return str(self.active)
            
class Worker(Process):
    def init(self, *args, **kwargs):
        super(Process, self).__init__(*args, **kwargs)
        self.keep_running = True

        
    def stop(self):
        print self.keep_running
        self.keep_running = False
        print self.keep_running
        print "Going to stop"


class Server(object):
    def __init__(self):
        # self.CONNECTION_OPENED = 'opened'
        # self.CONNECTION_CLOSED = 'closed'
        # self.MAX_REQUESTS_REACHED = 'reached'
        self.bind_to = ('127.0.0.1', 8080)
        self.socket = None
        
        self.mngr = Manager()
        self.start_servers = 2
        self.min_spare_servers = 5
        self.max_spare_servers = 12
        self.max_clients = 250
        self.max_request_per_child = 1000
        self.workers= set()
        self.queue = Queue()
        self.pool = ActivePool()
        self.sem = Semaphore(1)
        self.flags = self.mngr.dict()
        self.keep_running = True
        
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
        
    def worker_process(self, pool, sem, queue, flags):
        this = current_process()
        req_completed = 0
        
        while flags[this.pid] and req_completed < self.max_request_per_child:
            conn,addr = self.socket.accept()
            pool.make_active(this.name)
            try:
                response(conn)
            except:
                print "Invalid request"
            conn.close()
            pool.make_inactive(this.name)
            req_completed += 1
        
        if not flags[this.pid]:
            print "%s terminated by parent" % this.pid
        queue.put(this.pid)
        
    def manage_pool(self):
        try:
            pid = self.queue.get(True, 1)
        except Empty:
            # we want to force the code below to be executed
            # at least once every second
            pass
        
        for w in self.workers.copy():
            if not w.is_alive():
                w.join()
                self.workers.remove(w)

        while self.count_spare_servers() < self.min_spare_servers:
            self.spawn()

        kill_workers = self.count_spare_servers() - self.max_spare_servers
        print (self.count_spare_servers(), kill_workers)

        if kill_workers > 0:
            worker_list = [w for w in self.workers]
            for i in range(kill_workers):
                pid = worker_list[i].pid
                print "terminate order givven to %s" % pid
                self.flags[pid] = False

            
    def spawn(self):
        w = Process(target=self.worker_process, args=(self.pool, self.sem, self.queue, self.flags))
        w.daemon = True
        w.start()
        self.workers.add(w)
        self.flags[w.pid] = True
        
    def count_spare_servers(self):
        return len(self.workers) - len(self.pool.get_active())

if __name__ == '__main__':
    server = Server()
    server.serve()
