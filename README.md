# Remote Do #
## Introducing Remote-Do##
Sometimes you need to script things to run on a collection of remote hosts. 
These things might be simple like installing packages, or complicated like starting up clients and servers on specific hosts, while configuring monitoring and capture systems on other hosts. 
It's not always obvious what the right thing to is. 
Most of the time, it get's kludged together using some spaghetti scripts.
There has to be a better way. 
Now there is, it's called "Remote Do" or redo for short. 

Remote do is a python library that takes the headaches out of setting up and running remote systems. 
It has a super simple syntax and a number of convenient functions for getting the job done. 
Here's a taster of remote do in action. 

```
redo = redo.Redo(["test1.com", "test2.com", "test3.com"],"adminuser") 
pids = redo.run("find ~/my_data/", timeout=10)
results = redo.getoutput(pids)
```

Redo has many convenience functions and many features coming. If you just need do remote stuff, redo is for you. 

## Features ##
### Construction ###
Instantiate Redo with a single host, list of hosts, single user or list of users. eg
```
redo = redo.Redo("test1", "admin"] 
redo = redo.Redo(["test1","test2"], "admin")
redo = redo.Redo(["test1","test2"], ["admin1","admin2"])
```

### Select hosts ###
Redo can operate on a sinlge host, all hosts, or a selection of hosts, indexed by either host name or numerical index. eg
```
test1 = redo[0]
test1 = redo["test1"]
test1_2_3 = redo[0:2]
test1_2_3 = redo["test1":test3"] 
test2_3 = redo["test2":"test3"]
test_all = redo[:] 
```
### Run remote functions ###
Redo has a number of useful remote functionsL
- ***run()*** runs a command or list of commands on a remote box returning a list of PIDs
- ***wait()*** waits for a PID or list of PIDs to finish, returning the status code of each
- ***kill()*** stops the execution of a PID of list of PIDs. 
- ***getoutput()*** get the outputs produced by the PID or list of PIDs
- ***cd()*** change the working directory to the new one given
- ***copy_to()*** copy (scp) the file or list of files to the path or list of paths to the remote boxes
- ***copy_from()*** copy (scp) the file or list of files to the path or list of paths from the remote boxes
- ***sync_to()*** copy (rsync) the file or list of files to the path or list of paths to the remote boxes
- ***scyn_from()*** copy (rsync) the file or list of files to the path or list of paths from the remote boxes

### Run local functions ###
As part of setting up and doing remote things, you probably will want to do some local things to. 
Redo includes the following local functions to help this. 
- ***run_local()*** runs a command or list of commands on the local box returning a list of PIDs
- ***wait_local()*** waits for a PID to finish, returning the status code
- ***kill_local()*** stops the execution of a PID 
- ***getoutput_local()*** get the output produced by the PID
- ***cd_local()*** change the working directory to the new one given


## Detailed Documentation ##

#### run() ####
Runs the given command or list of commands on the remote box
```
run(cmds,timeout=None, block=True, pincpu=-1,realtime=False, returnout=True, tostdout=False)
```
- ***cmds*** is either a list of or single shell (usually BASH) command line to run on the remote host(s)
- ***timeout*** is the time in seconds that we should wait for the remote command to finish before killing it  
- ***block*** should redo block waiting for the command to finish, or should it run these in the background. 
- ***pincpu*** ***NOT YET IMPLEMENTED*** allows the remote command to be pinned to a specific CPU and removed all    other processes from that CPU   
- ***realtime*** ***NOT YET IMPLEMENTED*** runs the remote process as a realtime scheduled application with highest - CPU prioirty   
- ***returnout*** should the remote process retun its output to the controller progrem, or just ignore it.   
- ***tostdout*** should the output from the remote process be sent to standard out.    

run() returns a list of of proces identifiers (PIDs) which can be used with the following commands 


#### wait() ####
For for the processes given PIDs to complete running. Optionally kill them if they haven't finished
```
wait(pids,timeout,kill)
```
- ***pids*** is a list of process IDs as returned by run()
- ***timeout*** is a time in seconds to wait for the process to terminate. If it is None then wait will wait forever
- ***kill*** if true and timeout is not None, this will kill the process with the given PIDs after the timeout

wait() will return the exit code of the SSH session used to run the remote process None if the process has failed to terminate

#### kill() ####
Kills all processes with the given pids. Is equivalent to wait without a timeout. 
```
kill(pids)
```
- ***pids*** is a list of process IDs as returned by run()

kill() will return the exit code of the SSH session used to run the remote process. 


#### getoutput() ####
Gets the outputs from the PIDs listed.
```
getoutput(pids,block=False,timeout=None)
```
- ***pids*** is the list of process IDs as returned by run()
- ***block*** should getoutputs wait for output or return immediately if there is none
- ***tiemout*** how long to wait for output if there isn't any yet

getoutput() will return a list of strings as output from the remote applications. 

#### copy_to() ####
Copy a file or list of files to the remote host file or list of files using SCP.

```
copy_to(self,srcs,dsts,block=True,timeout=None,returnout=True,tostdout=False)
```

- ***srcs*** The source file/files to be coppied to the remote hosts
- ***dsts*** The destination file/files on the remote hosts
- ***block*** should redo block waiting for the copy to finish, or should it run these in the background. 
- ***timeout*** is the time in seconds that we should wait for the copy to finish before killing it  
- ***returnout*** should the copy retun its output to the controller progrem, or just ignore it.   
- ***tostdout*** should the copy output be sent to standard out.    

copy_to returns a list of of proces identifiers (PIDs) as with run() which can be used with wait()/kill() etc. 

#### copy_from() ####
Copy a file or list of files from the remote host to a file or list of files using SCP.

```
copy_from(self,srcs,dsts,block=True,timeout=None,returnout=True,tostdout=False)
```

- ***srcs*** The source file/files to be coppied from the remote hosts
- ***dsts*** The destination file/files on the local host
- ***block*** should redo block waiting for the copy to finish, or should it run these in the background. 
- ***timeout*** is the time in seconds that we should wait for the copy to finish before killing it  
- ***returnout*** should the copy retun its output to the controller progrem, or just ignore it.   
- ***tostdout*** should the copy output be sent to standard out.    

copy_from returns a list of of proces identifiers (PIDs) as with run() which can be used with wait()/kill() etc. 


#### sync_to() ####
Copy a file or list of files to the remote host file or list of files using rync.

```
sync_to(self,srcs,dsts,block=True,timeout=None,returnout=True,tostdout=False)
```

- ***srcs*** The source file/files to be coppied to the remote hosts
- ***dsts*** The destination file/files on the remote hosts
- ***block*** should redo block waiting for the copy to finish, or should it run these in the background. 
- ***timeout*** is the time in seconds that we should wait for the copy to finish before killing it  
- ***returnout*** should the copy retun its output to the controller progrem, or just ignore it.   
- ***tostdout*** should the copy output be sent to standard out.    

sync_to returns a list of of proces identifiers (PIDs) as with run() which can be used with wait()/kill() etc. 

#### sync_from() ####
Copy a file or list of files from the remote host to a file or list of files using sync.

```
sync_from(self,srcs,dsts,block=True,timeout=None,returnout=True,tostdout=False)
```

- ***srcs*** The source file/files to be coppied from the remote hosts
- ***dsts*** The destination file/files on the local host
- ***block*** should redo block waiting for the copy to finish, or should it run these in the background. 
- ***timeout*** is the time in seconds that we should wait for the copy to finish before killing it  
- ***returnout*** should the copy retun its output to the controller progrem, or just ignore it.   
- ***tostdout*** should the copy output be sent to standard out.    

sync_from returns a list of of proces identifiers (PIDs) as with run() which can be used with wait()/kill() etc. 



#### local_run() ####
Runs the given command on the local box
```
local_run(cmd,timeout=None, block=True, returnout=True, tostdout=False)
```
- ***cmd*** is a shell (usually BASH) command line to run on the remote host(s)
- ***timeout*** is the time in seconds that we should wait for the remote command to finish before killing it  
- ***block*** should redo block waiting for the command to finish, or should it run these in the background. 
- ***returnout*** should the remote process retun its output to the controller progrem, or just ignore it.   
- ***tostdout*** should the output from the remote process be sent to standard out.    

run() returns a list of of proces identifiers (PIDs) which can be used with the following commands 


#### local_wait() ####
For for the processes given PIDs to complete running. Optionally kill them if they haven't finished
```
local_wait(pids,timeout,kill)
```
- ***pids*** is a list of process IDs as returned by run()
- ***timeout*** is a time in seconds to wait for the process to terminate. If it is None then wait will wait forever
- ***kill*** if true and timeout is not None, this will kill the process with the given PIDs after the timeout

wait() will return the exit code of the process, None if the process has failed to terminate

#### local_kill() ####
Kills all processes with the given pids. Is equivalent to local_wait() with a timeout of 0.
```
local_kill(pids)
```
- ***pids*** is a list of process IDs as returned by local_run()

local_kill() will return the exit code of the process. 

### log() ####
```
log(msg,tostdout=True, tostderr=False,timestamp=True)
```
- ***msg*** a string containing the message to be logged
- ***tostdout*** should the log also output to standard out as it logs
- ***tostderr*** should the log also output to stderr as it logs
- ***timestamp*** should the log include a timestamp from when it was created?







