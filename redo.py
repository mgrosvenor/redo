#Copyright (c) 2015, Matthew P. Grosvenor
#All rights reserved. See LICENSE for more details

import sys
import os
import subprocess
import datetime
import thread
import threading
import Queue
import fcntl
import select
import time

#This is a giant work arount the completely brain dead subprocess stdin/stdout/communicate behaviour
class CThread (threading.Thread):
    def __init__(self, parent, cmd, returnout, result, tostdout):
        threading.Thread.__init__(self)
        self.parent     = parent
        self.result     = result
        self.cmd        = cmd
        self.returnout  = returnout
        self.tostdout   = tostdout
        self.daemon     = False
        self.subproc    = None

    def kill_subproc(self):
        #print "Safe kill subprocess.."
        p = self.subproc
        p.poll()
        if p.returncode is None:
            #print "Process is alive, try kill.."
            p.kill()
            #print "Waiting for cleanup.."           

            #Give the process some time to clean up            
            timestep = 0.1 #seconds
            timeout  = 10 #seconds
            i = 0
            while(p.returncode is None and i < (timeout/timestep)):
                (pid, err_code) = os.waitpid(p.pid, os.WNOHANG) 
                time.sleep(timestep)
                i += 1
            
            if p.returncode is None:
                #print "OK, terminating.."
                p.terminate() #see https://www.youtube.com/watch?v=Up1hGZhvjzs
                p.wait()                 

        #print "Subprocess is (should be?) dead.."
        return p.returncode

    def run(self):
        usereadline = True #Python docs warn that this could break, I've never seen it but am skeptical
        p = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.subproc = p
        if usereadline:
            fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
            fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            fl = fcntl.fcntl(p.stderr, fcntl.F_GETFL)
            fcntl.fcntl(p.stderr, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        while True:
            if usereadline:
                if p.returncode is not None:
                    thread.exit()

                stdout = ""
                stderr = ""
                try: stdout = p.stdout.readline()
                except: continue
                try: stderr = p.stderr.readline()
                except: continue
            else:   
                try:
                    (stdout,stderr) = p.communicate()
                    if stdout == None or stderr == None:
                        #Does this ever happen?? 
                        print "Communicate process is dead..."
                        self.kill_subproc()
                        thread.exit()
                except: #Communicate throws an exception if the subprocess dies
                    self.kill_subproc()
                    thread.exit()

            #Ouput our illgotten gains
            self.parent.log(stdout, tostdout=self.tostdout)
            self.parent.log(stderr, tostdout=self.tostdout)
            if self.returnout: self.result.put(stdout) 
            if self.returnout: self.result.put(stderr) 
                
        def __del__(self):
            #Does this even work? Have never seen it happen
            print "Got the delete signal"
            self.kill_subproc()
            thread.exit()


#Defines a remote host
class Host:
    def __init__(self, name,uname,logging = True):
        self.pidcount    = -1
        self.pid2thread  = {} #maps PIDs to threads
        
        self.name        = name
        self.uname       = uname
        #Populating these should be ported to some general infrastructure at some point
        self.mac         = -1
        self.cpu_count   = -1 
        self.ram_space   = -1
        self.disk_space  = -1
        self.pinned_cpus = -1
        self.free_cpus   = -1
            
        self.logging = logging
        if logging:
            self.logfilename  = "/tmp/redo_%s.log" % self.name
            self.logfile      = open(self.logfilename,"w")

    def makepid(self):
        self.pidcount += 1
        return "%s-%s" % (self.name,self.pidcount)

    #(optionaly) Make pretty logs of everything that we do
    def log(self,msg,tostdout=True,tostderr=False, timestamp=True):

        timestr = ""
        if timestamp:
            timestr += datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f ")        

        footer = ""
        if len(msg) > 0 and msg[-1] != "\n":
            footer = "\n"
            
        msg = "%s%s%s" % (timestr, msg,footer)

        if self.logging:
            self.logfile.write(msg)
        
        if tostdout:
            sys.stdout.write(msg)

        if tostderr:
            sys.stderr.write(msg)


    #Run a command on a remote host return a pid for the command
    #cmd:       Text string of the command to run
    #timeout:   Time in seconds to wait for the command to run, otherwise kill it
    #blocking:  Wait for the the command to finish before continuing. Either wait infinitely, or timeout seconds
    #pincpu:    Pin the command to a single CPU and run it as realtime prioirty
    def run(self, cmd, timeout=None,block=True, pincpu=-1, realtime=False, returnout=True, tostdout=False ):
        escaped = cmd.replace("\"","\\\"")
        if timeout > 0 and not block:
            escaped = "timeout %i %s" % (timeout,escaped)
        ssh_cmd = "ssh %s@%s \"%s\"" %(self.uname,self.name,escaped)  
        pid = self.makepid()
        self.log("Running ssh command \"%s\" with pid %s" % (ssh_cmd,pid), tostdout=tostdout)
        result = Queue.Queue()
        ssh_thread = CThread(self, ssh_cmd, returnout, result, tostdout)
        self.pid2thread[pid] = ssh_thread
        ssh_thread.start()
 
        #Give the thread a litte time to get going       
        while(ssh_thread.subproc is None):
            None
 
        if(block):
            #print "Waiting for thread to th pid %s terminate..." % (pid)
            ssh_thread.join(timeout)                       
            if ssh_thread.isAlive():
                print "Killing thread after timeout..."
                ssh_thread.kill_subproc()
                print "Waiting for thread to die..."
                ssh_thread.join()
                print "Thread and process is dead"
            else:
                None
                print "Thread with pid %s just terminated" % (pid)
                
        return pid

    def getoutput(self,pid, block=False, timeout=None):
        results_q = self.pid2thread[pid].result
        if results_q.empty():
            return None

        return results_q.get(block,timeout)

    def isalive(self,pid):
        return self.pid2thread[pid].isAlive()

    #Wait on a command on a remote host finishing
    def wait(self, pid, timeout=None, kill=False):
        procthread = self.pid2thread[pid]
        #Wait for the thread to start up if it hasn't
        print "Waiting for thread to th pid %s terminate..." % (pid)
        procthread.join(timeout)                       
        if procthread.isAlive():
            if not kill:
                return None #Timedout, and not going to kill

            print "Killing subprocess after timeout..."
            procthread.kill_subproc()
            print "Waiting for thread to die..."
            procthread.join()
            print "Thread and process is dead"
            
        return procthread.subproc.returncode


    #Stop the remote process by sending a signal
    def kill(self,pid):
        print "Killing thread"
        proc = self.pid2thread[pid]
        proc.kill_subproc()
        print "Waiting for thread to exit.."
        proc.join()
        print "Thread has exited.."
        return proc.subproc.returncode
        

    
    #Copy data to the remote host with scp
    def copy_to(self,src,dst):
        return -1


    #Copy data from the remote host with scp
    def copy_from(self,src,dst):
        return -1


    #Use rysnc to minimise copying
    def sync_to(self, src, dst):
        return -1


    #Use rsync to minimise copying 
    def sync_from(self,src,dst):
        return -1

    #Nice string representation    
    def __str__(self):
        return "'%s'" % self.name
    def __unicode__(self):
        return unicode("'%s'" % self.name)
    def __repr__(self):
        return "'%s'" % self.name

    def debug(self):
        print "DEBUG"

    def __del__(self):
        print "Destroying host %s" % self.name
        for pid in self.pid2thread:
            procthread = pid2thread[pid]
            if procthread.isAlive():
                print "Killing thread in destructor..."
                peocthread.kill_subproc() 
                print "Waiting for thread to die..."
                procthread.join()
                print "Thread is dead"
         

#Operate on a list of hosts
class Hosts:
    def __init__(self,hostlist):
        self.hostlist = hostlist

    #Run a command on a remote host return a pid for the command
    #cmd:       Text string of the command to run
    #timeout:   Time in seconds to wait for the command to run, otherwise kill it
    #blocking:  Wait for the the command to finish before continuing. Either wait infinitely, or timeout seconds
    #pincpu:    Pin the command to a single CPU and run it as realtime prioirty
    def run(self, cmd, timeout=-1,block=True, pincpu=-1, realtime=False, returnout=True, tostdout=False):
        return map( (lambda host: host.run(cmd,timeout,block,pincpu,realtime,returnout,tostdout)), self.hostlist)
        

    def getoutput(self,pid, block=False, timeout=None):
        return map( (lambda host: host.getoutput(pid,block,timeout)), self.hostlist)

    #Wait on a command on a remote host finishing
    def wait(self,pid, timeout=None, kill=False):
        return map( (lambda host: host.wait(pid,timeout,kill)), self.hostlist)

    #Stop the remote process by sending a signal
    def kill(self,pid):
        return map( (lambda host: host.kill(pid)), self.hostlist)
         
    #Copy data to the remote host with scp
    def copy_to(self,src,dst):
        return map( (lambda host: host.copy_to(src,dst)), self.hostlist)

    #Copy data from the remote host with scp
    def copy_from(self,src,dst):
        return map( (lambda host: host.copy_from(pid,src,dst)), self.hostlist)

    #Use rysnc to minimise copying
    def sync_to(self, src, dst):
        return map( (lambda host: host.sync_to(pid,src,dst)), self.hostlist)

    #Use rsync to minimise copying 
    def sync_from(self,src,dst):
        return map( (lambda host: host.sync_from(pid,src,dst)), self.hostlist)

    #Nice string representation    
    def __str__(self):
        return str(self.hostlist)
    def __unicode__(self):
        return unicode(str(self.hostlist))
    def __repr__(self):
        return str(self.hostlist)

    def debug(self):
        return map( (lambda host: host.debug()), self.hostlist)

class Redo:
    def __init__(self, hostnames, unames):
        #Make a list of empy host structures
        if type(hostnames) != list:
            hostnames = [hostnames]

        if type(unames) == list:            
            self.hosts = [ Host(host,uname) for host,uname in zip(hostnames,unames) ]
        else:
            self.hosts = [ Host(host,unames) for host in hostnames ]

    #Get a range of hosts
    def gethosts(self, start, stop):
        result = []
        first = False

        for host in self.hosts:
            if host.name == start:
                first = True
                if start == stop:
                    return host

            if first:
                result.append(host)
            
            if host.name == stop:
                break

        return Hosts(result)
    

    #Allows us to use slice notation with both integer and string indexes. Neat, but tricky
    def __getitem__(self,key):
        start = None
        stop = None

        if type(key) is slice:
            if type(key.start) is int:
                start = self.hosts[key.start].name
            if type(key.start) is str:
                start = key.start
            if key.start is None:
                start = self.hosts[0].name

            if type(key.stop) is int:
                idx = key.stop
                if key.stop > len(self.hosts):
                    idx = len(self.hosts) -1
                stop = self.hosts[idx].name
            if type(key.stop) is str:
                stop = key.stop
            if key.stop is None:
                stop = self.hosts[-1].name


        if type(key) is int:
            start = self.hosts[key].name
            stop  = self.hosts[key].name

        if type(key) is str:
            start = key
            stop  = key

        return self.gethosts(start,stop)

    def __len__(self):
        return len(self.hosts)

    #Run a command on a remote host return a pid for the command
    #cmd:       Text string of the command to run
    #timeout:   Time in seconds to wait for the command to run, otherwise kill it
    #blocking:  Wait for the the command to finish before continuing. Either wait infinitely, or timeout seconds
    #pincpu:    Pin the command to a single CPU and run it as realtime prioirty
    def run(self, cmd, timeout=-1,block=True, pincpu=-1, realtime=False, returnout=True, tostdout=False):
        return map( (lambda host: host.run(cmd,timeout,block,pincpu,realtime,returnout,tostdout)), self.hosts)
        

    def getoutput(self,pid, block=False, timeout=None):
        return map( (lambda host: host.getoutput(pid,block,timeout)), self.hosts)

    #Wait on a command on a remote host finishing
    def wait(self,pid, timeout=None, kill=False):
        return map( (lambda host: host.wait(pid,timeout,kill)), self.hosts)

    #Stop the remote process by sending a signal
    def kill(self,pid):
        return map( (lambda host: host.kill(pid)), self.hosts)
         
    #Copy data to the remote host with scp
    def copy_to(self,src,dst):
        return map( (lambda host: host.copy_to(src,dst)), self.hosts)

    #Copy data from the remote host with scp
    def copy_from(self,src,dst):
        return map( (lambda host: host.copy_from(pid,src,dst)), self.hosts)

    #Use rysnc to minimise copying
    def sync_to(self, src, dst):
        return map( (lambda host: host.sync_to(pid,src,dst)), self.hosts)

    #Use rsync to minimise copying 
    def sync_from(self,src,dst):
        return map( (lambda host: host.sync_from(pid,src,dst)), self.hosts)


