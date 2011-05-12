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
    def __init__(self, *args, **kwargs):
        self.mngr = Manager()
        self.keep_running = self.mngr.list()
        self.keep_running.append(True)
        self.max_request_per_child = 5000
        super(Worker, self).__init__(*args, **kwargs)
        
    def run(self):
        self.work(*self._args)
        
    def work(self, socket, pool, queue):
        this = current_process()
        req_completed = 0
        
        while self.keep_running[0] and req_completed < self.max_request_per_child:
            conn,addr = socket.accept()
            pool.make_active(this.name)
            try:
                response(conn)
            except:
                print "Invalid request"
            conn.close()
            pool.make_inactive(this.name)
            req_completed += 1
        
        if not self.keep_running[0]:
            print "%s terminated by parent" % this.pid
        queue.put(this.pid)
        
    def stop(self):
        print "Going to stop %s" % current_process().pid
        self.keep_running[0] = False


class Server(object):
    def __init__(self):
        # self.CONNECTION_OPENED = 'opened'
        # self.CONNECTION_CLOSED = 'closed'
        # self.MAX_REQUESTS_REACHED = 'reached'
        self.bind_to = ('127.0.0.1', 8080)
        self.socket = None
        
        self.start_servers = 2
        self.min_spare_servers = 5
        self.max_spare_servers = 6
        self.max_clients = 250
        self.workers= set()
        self.queue = Queue()
        self.pool = ActivePool()
        
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
                print w.pid, " joined"
                self.workers.remove(w)

        while self.count_spare_servers() < self.min_spare_servers:
            self.spawn()

        kill_workers = self.count_spare_servers() - self.max_spare_servers

        if kill_workers > 0:
            worker_list = list(self.workers)
            for i in range(kill_workers):
                print 'Executing stop on %s' % worker_list[i].pid
                worker_list[i].stop()

            
    def spawn(self):
        w = Worker(args=(self.socket, self.pool, self.queue))
        w.daemon = True
        w.start()
        self.workers.add(w)
        #self.flags[w.pid] = True
        
    def count_spare_servers(self):
        return len(self.workers) - len(self.pool.get_active())

if __name__ == '__main__':
    server = Server()
    server.serve()
