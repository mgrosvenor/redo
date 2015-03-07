#Copyright (c) 2015, Matthew P. Grosvenor
#All rights reserved. See LICENSE for more details

import sys
import os
import subprocess
import datetime


#Defines a remote host
class Host:
    def __init__(self, name,uname,logging = True):
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
            self.logfilename  = "/tmp/redo_name"
            self.logfile      = open(self.logfilename,"w")


    #(optionaly) Make pretty logs of everything that we do
    def log(self,msg,stdout=True,stderr=False, timestamp=True):

        timestr = ""
        if timestamp:
            timestr += datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f ")        

        footer = ""
        if msg[-1] != "\n":
            footer = "\n"
            
        msg = "%s%s%s" % (timestr, msg,footer)

        if self.logging:
            self.logfile.write(msg)
        
        if stdout:
            sys.stdout.write(msg)

        if stderr:
            sys.stderr.write(msg)


    #Run a command on a remote host return a pid for the command
    #cmd:       Text string of the command to run
    #timeout:   Time in seconds to wait for the command to run, otherwise kill it
    #blocking:  Wait for the the command to finish before continuing. Either wait infinitely, or timeout seconds
    #pincpu:    Pin the command to a single CPU and run it as realtime prioirty
    def run(self, cmd, timeout=-1,block=True, pincpu=-1, realtime=False ):
        escaped = cmd.replace("\"","\\\"")
        sub_cmd = "ssh %s@%s \"%s\"" %(self.uname,self.name,escaped)
        self.log(sub_cmd)

        pid = os.fork()
        if pid == 0:
            p = subprocess.Popen(sub_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            while True:
               line = p.stdout.readline()
               if not line: break
               self.log(line)

            sys.exit(0) #Should return status code
        else:
            if(block):
                os.waitpid(pid,0)
        
        return -1

    #Wait on a command on a remote host finishing
    def wait(self,pid, timeout):
        return -1 


    #Stop the remote process by sending a signal
    def kill(self,pid, signal=7):
        return -1

    
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

#Operate on a list of hosts
class Hosts:
    def __init__(self,hostlist):
        self.hostlist = hostlist

    #Run a command on a remote host return a pid for the command
    #cmd:       Text string of the command to run
    #timeout:   Time in seconds to wait for the command to run, otherwise kill it
    #blocking:  Wait for the the command to finish before continuing. Either wait infinitely, or timeout seconds
    #pincpu:    Pin the command to a single CPU and run it as realtime prioirty
    def run(self, cmd, timeout=-1,block=False, pincpu=-1, realtime=False ):
        results = []
        for host in self.hostlist:
            result = host.run(cmd,timeout,block,pincpu,realtime)
            results.append(result)
        return results


    #Wait on a command on a remote host finishing
    def wait(self,pid, timeout):
        results = []
        for host in self.hostlist:
            result = host.wait(pid,timeout)
            results.append(result)
        return results


    #Stop the remote process by sending a signal
    def kill(self,pid, signal=7):
        results = []
        for host in self.hostlist:
            result = host.kill(pid,signal)
            results.append(result)
        return results

         
    #Copy data to the remote host with scp
    def copy_to(self,src,dst):
        results = []
        for host in self.hostlist:
            result = host.copy_to(src,dst)
            results.append(result)
        return results


    #Copy data from the remote host with scp
    def copy_from(self,src,dst):
        results = []
        for host in self.hostlist:
            result = host.wait(pid,src,dst)
            results.append(result)
        return results


    #Use rysnc to minimise copying
    def sync_to(self, src, dst):
        results = []
        for host in self.hostlist:
            result = host.sync_to(pid,src,dst)
            results.append(result)
        return results


    #Use rsync to minimise copying 
    def sync_from(self,src,dst):
        return -1

    #Nice string representation    
    def __str__(self):
        return str(self.hostlist)
    def __unicode__(self):
        return unicode(str(self.hostlist))
    def __repr__(self):
        return str(self.hostlist)

    def debug(self):
        results = []
        for host in self.hostlist:
            result = host.debug()
            results.append(result)
        return results        


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
