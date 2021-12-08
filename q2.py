import random
from tkinter import *
import threading
import names
import time
from queue import Queue
import numpy as np

# This class is so that we can put threading.Lock to the queue
class QueueClass(Queue) :
    def __init__(self,maxSize,name) :
        Queue.__init__(self,maxsize=maxSize)
        self.Lock = threading.Lock() # for put queue function and increase self.Number
        self.LockGet = threading.Lock() # for popping the queue
        self.LockTime = threading.Lock() # for increasing time
        self.Name = name # name of this queue
        self.Time = 0 # waiting time in the queue
        self.Number = 0 # number (for check in queue)

simTime = 0
simEnd = 30
serverAmount = 3
rejected = QueueClass(1000000,'Rejected') # for passenger who fail to board flight
exit = QueueClass(1000000,'Exit') # for passenger who pass check in
DoorQ = QueueClass(10000,'DOORQ')
threads = [] # all threads

OverallWaitingTime = 0 # total waiting time for all passengers
OverallWaitingTimeLock = threading.Lock()
CheckInServersQ = [] # list for check in queue
CheckInServers = [] # list for check in server

class CheckInServer(threading.Thread):
    BUSY = 0
    FREE = 1
    def __init__(self,queue,ID):
        threading.Thread.__init__(self)
        self.Status = CheckInServer.FREE
        self.Customer = None
        self.Name = names.get_full_name()
        self.Q = queue
        self.ID = ID

    def run(self):
        global simTime, simEnd

        while simTime < simEnd :
            if self.Status == CheckInServer.FREE:
                self.CheckGetCustomer()
            if self.Status == CheckInServer.BUSY and self.Customer != None:
                self.Status = CheckInServer.FREE

                if not self.Customer.Passport:
                    time.sleep(random.randint(0, 3))
                    self.Customer.pos = Passenger.CHECKIN_REJECTED
                    # add to rejected list
                    rejected.Lock.acquire()
                    rejected.put(self.Customer)
                    rejected.Lock.release()
                    # increasing the number served by the server
                    self.Q.Lock.acquire()
                    self.Q.Number += 1
                    self.Q.Lock.release()
                else:
                    time.sleep(random.randint(0, 2))
                    self.Customer.pos = Passenger.CHECKIN_DONE
                    # add to done list
                    exit.Lock.acquire()
                    exit.put(self.Customer)
                    exit.Lock.release()
                    # increasing the number served by the server
                    self.Q.Lock.acquire()
                    self.Q.Number += 1
                    self.Q.Lock.release()
            time.sleep(1)

    # function to get customer from queue
    def CheckGetCustomer(self):
        self.Q.LockGet.acquire()
        if not self.Q.empty():
            self.Customer = self.Q.get()
            self.Status = CheckInServer.BUSY
        else:
            self.Customer = None
        self.Q.LockGet.release()

class Passenger(threading.Thread):
    DOORQ_IN_QUEUE = 0
    CHECKIN_IN_QUEUE = 1
    CHECKIN_REJECTED = 3
    CHECKIN_DONE = 4
    
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.Ticket = np.random.choice([True,False],1,p=[0.98,1-0.98])
        self.Passport = np.random.choice([True,False],1,p=[0.98,1-0.98])
        self.Name = name
        self.pos = Passenger.DOORQ_IN_QUEUE
        self.Luggage = np.random.choice([True,False],1,p=[0.75,0.25])
        self.Q = None
        print(f'Passenger {self.Name} created.')
    
    def run(self):
        global simTime, simEnd, CheckInServers, rejected, OverallWaitingTime, DoorQ

        while simTime < simEnd:
            # if passenger in queue, increate waiting time for queue and overall
            if self.pos == Passenger.CHECKIN_IN_QUEUE:
                OverallWaitingTimeLock.acquire()
                OverallWaitingTime += 1
                OverallWaitingTimeLock.release()
                self.Q.LockTime.acquire()
                self.Q.Time += 1
                self.Q.LockTime.release()

            if self.pos == Passenger.DOORQ_IN_QUEUE:
                qsize = []
                Break = False
                for i in CheckInServersQ:
                    if not i.full():
                        if i.empty():
                            self.Q = i
                            self.Q.Lock.acquire()
                            self.Q.put(self)
                            self.Q.Lock.release()
                            self.pos = Passenger.CHECKIN_IN_QUEUE
                            Break = True
                            print(f'{self.Name} went into {self.Q.Name}')
                            break
                        else:
                            Break = False
                            qsize.append(i.qsize())
                if not Break:
                    minVal = min(qsize)
                    minIndex = qsize.index(minVal)
                    self.Q = CheckInServersQ[minIndex]
                    self.Q.Lock.acquire()
                    self.Q.put(self)
                    self.Q.Lock.release()
                    self.pos = Passenger.CHECKIN_IN_QUEUE
                    print(f'{self.Name} went into {self.Q.Name}')
                
            # if rejected                 
            if  self.pos == Passenger.CHECKIN_REJECTED:
                print(f'Passenger {self.Name} rejected')
                break
            # if done checkin  
            if self.pos == Passenger.CHECKIN_DONE:
                print(f'Passenger {self.Name} has done Check-in. Going to next procedure.')
                break
            time.sleep(1)


# creating servers and server queue
for i in range(serverAmount):
    CheckInQ = QueueClass(10000,f'Q{i+1}')
    # Assigning queue to server
    CheckInServersQ.append(CheckInQ)
    server = CheckInServer(CheckInServersQ[i],i)
    CheckInServers.append(server)
    CheckInServers[i].start()
    threads.append(server)
print('Servers Created.... Starting Simulation...')
time.sleep(1)

while simTime < simEnd:
    if simTime+1 % 10 >=5: # if 5 minutes before flight time (peak hours)
        NewPassengerAmount = random.randint(3,7)
    else: # if not close to flight time (non peak hours)
        NewPassengerAmount = random.randint(1,4)

    for i in range(NewPassengerAmount):
        
        Name = names.get_full_name()
        # create new passenger with the classes
        newPass = Passenger(Name)
        newPass.start() # start
        DoorQ.put(newPass) # get the passenger into the list for initial queue
        threads.append(newPass) # thread list to wait for all thread finish

    time.sleep(1) # 1 minute delay
    simTime += 1

# thread list to wait for all thread finish
for x in threads:
    x.join()

# output
print('\nOUTPUT:')
print(f'{DoorQ.qsize()} people went in.')
for i in range(len(CheckInServersQ)):
    print(f'Queue {i+1}')
    print(f'    People still in queue: {CheckInServersQ[i].qsize()}')
    print(f'    Served number: {CheckInServersQ[i].Number}')
    print(f'    Overall Waiting Time for this queue: {CheckInServersQ[i].Time} Minutes.')
print(f'Overall waiting time for all queue: {OverallWaitingTime} Minutes.')
print(f'{rejected.qsize()} people has been rejected')
print(f'{exit.qsize()} people have done check-in process and proceed to the next stage')