import threading
import time
import random
import math
import numpy as np

simTime = 0
simEnd = 5

food_list = ['Mee goreng mamak', 'Apam balik', 'Nasi kerabu','Ayam percik', 'Nasi lemak', 
             'Roti john', 'Rendang', 'Kuih', 'Nasi kandar', 'Laksa', 
             'Popia basah', 'Bubur', 'Roti jala', 'Cendawan goreng', 'Sambal udang']

class Restaurant(threading.Thread):
    IS_OPEN = 0
    IS_FULL = 1
    def __init__(self,foods,capacity,grid,loc):
        super().__init__()
        self.foods = foods
        self.capacity = capacity
        self.waitingTime = [0,threading.Lock()]
        self.seats = [None for i in range(math.ceil(capacity/2))]
        self.seatsLock = threading.Lock()
        self.status = Restaurant.IS_OPEN
        self.staff = 0
        self.totalStuff = 0
        self.sales = 0
        self.grid = grid
        self.loc = loc
        self.grid.arr[loc[0]][loc[1]] = []
        self.newCustomer = None
    
    def run(self):
        global simTime, simEnd
        while simTime < simEnd:
            self.seatsLock.acquire()
            if all(seat is not None for seat in self.seats): # if there's no open seat
                self.status = Restaurant.IS_FULL
            else: # got seat
                self.status = Restaurant.IS_OPEN
                x = self.loc[0]
                y = self.loc[1]
                self.grid.locks[x][y].acquire()
                if isinstance(self.grid.arr[x][y][0],Customer):
                    self.newCustomer = self.grid.getFromQueue(x,y)
                    self.grid.removeFromQueue(x,y)
                    while True:
                        newSeat = random.randint(0,math.ceil(self.capacity/2)-1)
                        if not isinstance(newSeat,Customer):
                            self.seats[newSeat] = self.newCustomer
                            self.newCustomer.status = self.newCustomer.eatWay
                            self.newCustomer = None
                self.grid.locks[x][y].release()
            self.seatsLock.release()

            for i in self.seats:
                if isinstance(i,Customer):
                    if i.status is Customer.IS_DONE:
                        index = self.seats.index(i)
                        self.seats[index] = None
                        self.sales += 1
            if self.sales%5 == 0:
                self.staff += 1
            time.sleep(1)

class Staff(threading.Thread):
    def __init__(self,loc,grid,restaurant):
        super().__init__()
        self.customers = []
        self.loc = loc
        self.grid = grid
        self.restaurant = restaurant
    
    def run(self):
        global simTime, simEnd
        while simTime < simEnd:
            people = 0
            for i in range(3):
                for j in range(3):
                    nx = self.loc[0] + i - 1
                    ny = self.loc[1] + j - 1

                    if nx < 0 or ny < 0:
                        continue
                    if nx >= self.grid.width or ny >= self.grid.height:
                        continue
                    if nx == self.loc[0] and ny == self.loc[1]:
                        continue
                    self.grid.locks[nx][ny].acquire()
                    potentialCustomer = self.grid.get(nx,ny)
                    if potentialCustomer != None:
                        if any(favFood is [food for food in self.restaurant.foods] for favFood in potentialCustomer.favFood) and potentialCustomer.status == Customer.IS_EXIST:
                            potentialCustomer.haveFavFood = True
                            potentialCustomer.status = Customer.IS_THINKING
                            potentialCustomer.staff = self
                            time.sleep(2)
                            self.grid.locks[nx][ny].release()                            
                            people += 1
                    
            while people == 0:
                Break = False
                x = random.randint(0,self.grid.width+1)
                y = random.randint(0,self.grid.height+1)

                self.grid.locks[x][y].acquire()
                if isinstance(self.grid.getFromQueue(self.grid.arr[x][y]),Staff) or isinstance(self.grid.getFromQueue(self.grid.arr[x][y]),Customer) or isinstance(self.grid.getFromQueue(self.grid.arr[x][y]), Restaurant):
                    self.grid.locks[x][y].release()
                    continue
                else:
                    self.grid.arr[x][y] = self
                    self.loc =[x,y]
                    self.grid.locks[x][y].release()

                for i in range(3):
                    for j in range(3):
                        nx = x + i - 1
                        ny = y + j - 1

                        if nx < 0 or ny < 0:
                            continue
                        if nx >= self.grid.width or ny >= self.grid.height:
                            continue
                        if nx == self.loc[0] and ny == self.loc[1]:
                            continue
                        self.grid.locks[nx][ny].acquire()
                        potentialCustomer = self.grid.get(nx,ny)
                        if potentialCustomer != None:
                            people += 1
                            Break = True
                        self.grid.locks[nx][ny].release()
                        if Break: break
                    if Break: break
        time.sleep(1)

class Customer(threading.Thread):
    IS_EXIST = 0
    IS_WAITING_IN_QUEUE = 1
    IS_EATING_ENJOYING = 2
    IS_EATING = 3
    IS_DONE = 4
    HAVE_CHOSEN = 5
    IS_THINKING = 6

    def __init__(self,favFood,loc,grid):
        super().__init__()
        self.favFood = favFood
        self.waitingTime = 0
        self.loc = loc
        self.status = Customer.IS_EXIST
        self.grid = grid
        self.seats = None
        self.haveFavFood = None
        self.randomRestaurant = False
        self.eatWay = random.choice([Customer.IS_EATING,Customer.IS_EATING_ENJOYING])
        self.staff = None
        self.acceptProb = 0
    
    def run(self):
        global simTime, simEnd
        while simTime < simEnd:
            if self.status == Customer.IS_EATING or Customer.IS_EATING_ENJOYING:
                time.sleep(random.randint(1,6))
                self.status = Customer.IS_DONE
                    
            if self.status == Customer.IS_WAITING_IN_QUEUE:
                self.waitingTime += 1
            
            if self.status == Customer.IS_THINKING:
                time.sleep(random.randint(0,2))
                queueNumber = len(self.grid.arr[self.staff.restaurant.loc[0]][self.staff.restaurant.loc[1]])

                self.acceptProb = queueNumber/100
                if self.haveFavFood:
                    self.acceptProb +=0.6
                dec = np.random.choice([Customer.IS_THINKING,Customer.HAVE_CHOSEN],1,[self.acceptProb, 1 - self.acceptProb])
                dec = dec[0]

                if dec == Customer.IS_THINKING:
                    self.status = Customer.IS_EXIST
                    self.haveFavFood = False
                    lookLoc = []
                    while True:
                        for i in range(3):
                            for j in range(3):
                                nx = self.loc[0] + i - 1
                                ny = self.loc[1] + j - 1
                                lookLoc.append([nx,ny])

                        newLoc = random.choice(lookLoc)

                        self.grid.locks[nx][nx].acquire()
                        if isinstance(self.grid.arr[nx][nx],Staff) or isinstance(self.grid.arr[nx][nx],Customer):
                            self.grid.locks[nx][nx].release()
                            continue
                        else:
                            self.grid.arr[nx][nx] = self
                            self.loc =[nx,nx]
                            self.grid.locks[nx][nx].release()
                            break
                else:
                    self.status = Customer.HAVE_CHOSEN

            time.sleep(1)

class Grid:
    def __init__(self, dim):
        self.width = dim
        self.height = dim
        self.arr = [[ None for i in range(dim)] for j in range(dim)]
        self.locks = [[None for i in range(dim)] for j in range(dim)]
        
        for j in range(dim):
            for i in range(dim):
                self.locks[j][i] = threading.Lock()

    def addToQueue(self, entity, x, y):
        self.arr[x][y].append(entity)
        
    def getFromQueue(self, x, y):
        return self.arr[y][x][0]
        
    def removeFromQueue(self, x, y):
        self.arr[y][x].remove(self.arr[y][x][0])

    def add(self, entity, x, y):
        self.arr[x][y] = entity
        
    def get(self, x, y):
        return self.arr[x][y]
        
    def remove(self, x, y):
        self.arr[x][y] = None

bazaar = Grid(50)
restaurants = []
for i in range(3):
    while True:
        loc = [round(random.randint()*50),round(random.randint()*50)]
        if not(isinstance(bazaar.getFromQueue(loc[0],loc[1]), Restaurant)):
            break
    restaurant = Restaurant(random.choices(food_list,k=3),random.randint(10,21),bazaar,loc)
    restaurants.append(restaurant)
    restaurant.start()

while simTime < simEnd:
    for i in range(3):
        while True:
            loc = [round(random.randint()*50),round(random.randint()*50)]
            if not(isinstance(bazaar.getFromQueue(loc[0],loc[1]), Restaurant) or isinstance(bazaar.getFromQueue(loc[0],loc[1]), Customer) or isinstance(bazaar.getFromQueue(loc[0],loc[1]), Staff)):
                break
        newStaff = restaurants[i].staff - restaurants[i].totalStuff
        for i in range(newStaff):
            staff = Staff(loc,bazaar,restaurants[i])
        restaurants[i].totalStuff = restaurants[i].staff + newStaff 
    
    newCustomerAmount = random.randint(0,5)
    for i in range(newCustomerAmount):
        while True:
            loc = [round(random.randint()*50),round(random.randint()*50)]
            if not(isinstance(bazaar.getFromQueue(loc[0],loc[1]), Restaurant) or isinstance(bazaar.getFromQueue(loc[0],loc[1]), Customer) or isinstance(bazaar.getFromQueue(loc[0],loc[1]), Staff)):
                break
        customer = Customer(random.choices(food_list,k=3),loc, bazaar)

    time.sleep(1)
