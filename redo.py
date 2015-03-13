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

#This is a giant work around the completely brain dead subprocess stdin/stdout/communicate behaviour
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
        #usereadline = False #Python docs warn that this could break, I've never seen it but am skeptical
        p = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.subproc = p
        if usereadline:
            fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
            fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            fl = fcntl.fcntl(p.stderr, fcntl.F_GETFL)
            fcntl.fcntl(p.stderr, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        while True:
            stdout = None
            stderr = None
            if usereadline:
                #Check if process has died
                p.poll()
                if p.returncode is not None:
                    thread.exit()
                    #Unreachable
                try: stdout = p.stdout.readline()
                except: None
                try: stderr = p.stderr.readline()
                except: None
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
            if stdout and stdout != "": self.parent.redo_main.log(stdout, tostdout=self.tostdout)
            if stderr and stderr != "": self.parent.redo_main.log(stderr, tostdout=self.tostdout)
            if stdout and self.returnout: self.result.put(stdout) 
            if stderr and self.returnout: self.result.put(stderr) 
                
        def __del__(self):
            #Does this even work? Have never seen it happen
            print "Got the delete signal"
            self.kill_subproc()
            thread.exit()


#Defines a remote host
class Host:
    def __init__(self, redo, name,uname,logging = True):
        self.pidcount    = -1
        self.pid2thread  = {} #maps PIDs to threads
        
        self.name        = name
        self.uname       = uname
        self.redo_main   = redo
        #Populating these should be ported to some general infrastructure at some point
        self.mac         = -1
        self.cpu_count   = -1 
        self.ram_space   = -1
        self.disk_space  = -1
        self.pinned_cpus = -1
        self.free_cpus   = -1
            
        self.logging = logging
    
    def makepid(self):
        self.pidcount += 1
        return "%s-%s" % (self.name,self.pidcount)


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
        self.redo_main.log("Running ssh command \"%s\" with pid %s" % (ssh_cmd,pid), tostdout=tostdout)
        self.redo_main.log("%s" % (ssh_cmd), tostdout=tostdout)
        result = Queue.Queue()
        ssh_thread = CThread(self, ssh_cmd, returnout, result, tostdout)
        self.pid2thread[pid] = ssh_thread
        ssh_thread.start()
 
        #Give the thread a litte time to get going       
        while(ssh_thread.subproc is None):
            None
 
        if(block):
            self.redo_main.log("REDO [%s]: Waiting for thread to th pid %s terminate..." % (self.name,pid))
            ssh_thread.join(timeout)                       
            if ssh_thread.isAlive():
                self.redo_main.log("REDO [%s]: Killing thread running pid \"%s\" after timeout..." % (self.name, pid))
                ssh_thread.kill_subproc()
                self.redo_main.log("REDO [%s]: Waiting for thread to die..." % (self.name))
                ssh_thread.join()
                self.redo_main.log("REDO [%s]: Thread and process is dead" % (self.name))
            else:
                None
                self.redo_main.log("REDO [%s]: Thread with pid %s just terminated" % (self.name,pid))
                
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
        self.log("REDO [MAIN]: Waiting for thread with pid \"%s\" to terminate..." % (pid))
        procthread.join(timeout)                       
        if procthread.isAlive():
            if not kill:
                return None #Timedout, and not going to kill

            self.log("REDO [MAIN]: Killing pid \"%s\" after timeout..." % (pid))
            procthread.kill_subproc()
            self.log("REDO [MAIN]: Waiting for thread running pid \"%s\" to die..." % (pid))
            procthread.join()
            self.log("REDO [MAIN]: Thread and running pid \"%s\" is dead" % (pid))
        
        if procthread.subproc.returncode: 
            self.log("REDO [MAIN]: Process with pid \"%s\" terminated with return code \"%i\" ..." % (pid,procthread.subproc.returncode))
        else:
            self.log("REDO [MAIN]: Process with pid \"%s\" has not yet terminated ..." % (pid))
        
        return procthread.subproc.returncode


    #Stop the remote process by sending a signal
    def kill(self,pid):
        self.redo_main.log("REDO [%s]: Killing thread with pid \"%s\" " % (self.name, pid))
        proc = self.pid2thread[pid]
        proc.kill_subproc()
        self.redo_main.log("REDO [%s]: Waiting for thread to exit.." %(self.name))
        proc.join()
        self.redo_main.log("REDO [%s}: Thread has exited.." %(self.name))
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
        self.redo_main.log("REDO [%s]: Destroying host %s" % (self.name,self.name))
        for pid in self.pid2thread:
            procthread = pid2thread[pid]
            if procthread.isAlive():
                self.redo_main.log("REDO [%s]: Killing thread in destructor..." % (self.name))
                peocthread.kill_subproc() 
                self.redo_main.log("REDO [%s]: Waiting for thread to die..." % (self.name))
                procthread.join()
                self.redo_main.log("REDO [%s]: Thread is dead" % (self.main))
         

#Operate on a list of hosts
class Hosts:
    def __init__(self,hostlist):
        self.hostlist = hostlist

    #Run a command on a remote host return a pid for the command
    #cmd:       Text string of the command to run
    #timeout:   Time in seconds to wait for the command to run, otherwise kill it
    #blocking:  Wait for the the command to finish before continuing. Either wait infinitely, or timeout seconds
    #pincpu:    Pin the command to a single CPU and run it as realtime prioirty
    def run(self, cmd, timeout=None, block=True, pincpu=-1, realtime=False, returnout=True, tostdout=False):
        return map( (lambda host: host.run(cmd,timeout,block,pincpu,realtime,returnout,tostdout)), self.hostlist)
        

    def getoutput(self,pids, block=False, timeout=None):
        return map( (lambda (host,pid): host.getoutput(pid,block,timeout)), zip(self.hostlist,pids))

    #Wait on a command on a remote host finishing
    def wait(self,pids, timeout=None, kill=False):
        return map( (lambda (host,pid): host.wait(pid,timeout,kill)), zip(self.hostlist,pids))

    #Stop the remote process by sending a signal
    def kill(self,pids):
        return map( (lambda (host,pid): host.kill(pid)), zip(self.hostlist,pids))
         
    #Copy data to the remote host with scp
    def copy_to(self,srcs,dsts):
        if type(srcs) is not list:
            srcs = srcs * len(self.hostslist)

        if type(dsts) is not list:
            dsts = srcs * len(self.hostlist)

        return map( (lambda (host,src,dst): host.copy_to(src,dst)), zip(self.hostlist,srcs, dsts))

    #Copy data from the remote host with scp
    def copy_from(self,src,dst):
        if type(srcs) is not list:
            srcs = srcs * len(self.hostslist)

        if type(dsts) is not list:
            dsts = srcs * len(self.hostlist)

        return map( (lambda (host,src,dst): host.copy_from(src,dst)), zip(self.hostlist,srcs, dsts))


    #Use rysnc to minimise copying
    def sync_to(self, src, dst):
        if type(srcs) is not list:
            srcs = srcs * len(self.hostslist)

        if type(dsts) is not list:
            dsts = srcs * len(self.hostlist)

        return map( (lambda (host,src,dst): host.sync_to(src,dst)), zip(self.hostlist,srcs, dsts))


    #Use rsync to minimise copying 
    def sync_from(self,src,dst):
        if type(srcs) is not list:
            srcs = srcs * len(self.hostslist)

        if type(dsts) is not list:
            dsts = srcs * len(self.hostlist)

        return map( (lambda (host,src,dst): host.sync_from(src,dst)), zip(self.hostlist,srcs, dsts))

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
    def __init__(self, hostnames, unames, workdir="/tmp/redo/",logging=True):
        self.pid2thread = {}
        self.pidcount   = 0
        self.logging    = logging
        self.workdir    = workdir

        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir)

        os.chdir(self.workdir)

        #Make a list of empy host structures
        if type(hostnames) != list:
            hostnames = [hostnames]

        if type(unames) == list:            
            self.hostlist = [ Host(self,host,uname) for host,uname in zip(hostnames,unames) ]
        else:
            self.hostlist = [ Host(self,host,unames) for host in hostnames ]

        if logging:
            self.logfilename  = self.workdir + "/redo_%s.log" % (datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f"))
            self.logfile      = open(self.logfilename,"w")


    #Get a range of hosts
    def gethosts(self, start, stop):
        result = []
        first = False

        for host in self.hostlist:
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
                start = self.hostlist[key.start].name
            if type(key.start) is str:
                start = key.start
            if key.start is None:
                start = self.hostlist[0].name

            if type(key.stop) is int:
                idx = key.stop
                if key.stop > len(self.hostlist):
                    idx = len(self.hostlist) -1
                stop = self.hostlist[idx].name
            if type(key.stop) is str:
                stop = key.stop
            if key.stop is None:
                stop = self.hostlist[-1].name


        if type(key) is int:
            start = self.hostlist[key].name
            stop  = self.hostlist[key].name

        if type(key) is str:
            start = key
            stop  = key

        return self.gethosts(start,stop)

    def __len__(self):
        return len(self.hostlist)

    #Run a command on a remote host return a pid for the command
    #cmd:       Text string of the command to run
    #timeout:   Time in seconds to wait for the command to run, otherwise kill it
    #blocking:  Wait for the the command to finish before continuing. Either wait infinitely, or timeout seconds
    #pincpu:    Pin the command to a single CPU and run it as realtime prioirty
    def run(self, cmd, timeout=None,block=True, pincpu=-1, realtime=False, returnout=True, tostdout=False):
        hosts = Hosts(self.hostlist)
        return hosts.run(cmd,timeout,block,pincpu,realtime,returnout,tostdout)
        

    def getoutput(self,pid, block=False, timeout=None):
        hosts = Hosts(self.hostlist)
        return hosts.getoutput(pid,block,timeout)

    #Wait on a command on a remote host finishing
    def wait(self,pids, timeout=None, kill=False):
        hosts = Hosts(self.hostlist)
        return host.wait(pids,timeout,kill)

    #Stop the remote process by sending a signal
    def kill(self,pids):
        hosts = Hosts(self.hostlist)
        return hosts.kill(pids)
         
    #Copy data to the remote host with scp
    def copy_to(self,src,dst):
        hosts = Hosts(self.hostlist)
        return map( (lambda host: host.copy_to(src,dst)), self.hostlist)

    #Copy data from the remote host with scp
    def copy_from(self,srcs,dsts):
        hosts = Hosts(self.hostlist)
        return hosts.copy_from(srcs,dsts)

    #Use rysnc to minimise copying
    def sync_to(self, srcs, dsts):
        hosts = Hosts(self.hostlist)
        return hosts.sync_to(srcs,dsts)

    #Use rsync to minimise copying 
    def sync_from(self,srcs,dsts):
        hosts = Hosts(self.hostlist)
        return hosts.sync_from(srcs,dsts)

    def makepid(self):
        self.pidcount += 1
        return "%s-%s" % ("local",self.pidcount)

    def local_run(self, cmd, timeout=None,block=True, returnout=True, tostdout=False ):
        escaped = cmd.replace("\"","\\\"")
        if timeout > 0 and not block:#Won't work on mac... :-(
            escaped = "timeout %i %s" % (timeout,escaped)
        local_cmd = "%s" %(escaped)  
        pid = self.makepid()
        self.log("REDO [main]: Running command \"%s\" with pid %s" % (local_cmd,pid), tostdout=tostdout)
        self.log("REDO [main]: %s" % (local_cmd), tostdout=tostdout)
        result = Queue.Queue()
        run_thread = CThread(self, local_cmd, returnout, result, tostdout)
        self.pid2thread[pid] = run_thread
        run_thread.start()
 
        #Give the thread a litte time to get going       
        while(run_thread.subproc is None):
            None
 
        if(block):
            #print "Waiting for thread to th pid %s terminate..." % (pid)
            run_thread.join(timeout)                       
            if run_thread.isAlive():
                self.log("REDO [main]: Killing thread after timeout...")
                run_thread.kill_subproc()
                self.log("REDO [main]: Waiting for thread to die...")
                run_thread.join()
                self.log("REDO [main]: Thread and process is dead")
            else:
                None
                self.log("REDO [main]: Thread with pid %s just terminated" % (pid))
                
        return pid

    #(optionaly) Make pretty logs of everything that we do
    def log(self,msg,tostdout=False,tostderr=False, timestamp=True):

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

    def local_getoutput(self,pid, block=False, timeout=None):
        results_q = self.pid2thread[pid].result
        if results_q.empty():
            return None

        return results_q.get(block,timeout)

    def local_isalive(self,pid):
        return self.pid2thread[pid].isAlive()

    #Wait on a command on a remote host finishing
    def local_wait(self, pid, timeout=None, kill=False):
        procthread = self.pid2thread[pid]
        #Wait for the thread to start up if it hasn't
        self.log("REDO [main]: Waiting for thread to th pid %s terminate..." % (pid))
        procthread.join(timeout)                       
        if procthread.isAlive():
            if not kill:
                return None #Timedout, and not going to kill

            self.log("REDO [main]: Killing subprocess after timeout...")
            procthread.kill_subproc()
            self.log("REDO [main]: Waiting for thread to die...")
            procthread.join()
            self.log("REDO [main]: Thread and process is dead")
            
        return procthread.subproc.returncode


    #Stop the remote process by sending a signal
    def local_kill(self,pid):
        self.log("REDO [main]: Killing thread")
        proc = self.pid2thread[pid]
        proc.kill_subproc()
        self.log("REDO [main]: Waiting for thread to exit..")
        proc.join()
        self.log("REDO [main]: Thread has exited..")
        return proc.subproc.returncode
        


