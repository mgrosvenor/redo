# Remote Do #
## Introducing Remote-Do##
Sometimes you need to script things to run on a collection of remote hosts. 
These things might be simple like installing packages, or complicated like starting up clients and servers on specific hosts, while configuring monitoring and capture systems on other hosts. 
It's not always obvious what the right thing to is. 
Most of the time, it get's kludged together using some spaghetti BASH/python/perl/sed scripts. 
But then you realize that you need to log all of the output to make sure that everything is running properly. 
And you need to script some non-trival iteration over parameters, or exit conditions. 
Bring out more BASH and more pythong/perl/sed/grep/cut/awk/uniq scripts. 
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
Redo can operate on a sinlge host, all hosts, or a selection of hosts, indexed by either host name or numberical index. eg
```
test1 = redo[0]
test1 = redo["test1"]
test1_2_3 = redo[0:3]
test1_2_3 = redo["test1":test3"] 
test2_3 = redo["test2":"test3"]
test_all = redo[:] 
```
### Run remote functions ###
Redo has a number of useful remote functions  
#### run() ####
Runs the given command on the remote box
```
run(cmd,timeout=None, block=True, pincpu=-1,realtime=False, returnout=True, tostdout=False)
```
- ***cmd*** is a shell (usually BASH) command line to run on the remote host(s)
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










