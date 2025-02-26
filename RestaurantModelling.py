import simpy as sp
import random as rd
import pandas as pd

SIMULATION_TIME = 100
FOOD_STOCK_LIMIT = 50
MAX_QUEUE_SIZE = 5
ARRIVAL_INTERVAL = 2

class Customer(object):
    def __init__(self, env, num, restaurant):
        self.env = env
        self.num = num
        self.restaurant = restaurant
        self.result_time = 0

    def serv_and_eat(self):
        request = self.restaurant.tables.request()
        yield request
        arrival_time = self.env.now
        print("Customer", self.num, "has been seated at time", round(self.env.now, 1))

        menu_item = yield self.restaurant.menu.get()
        menu_name, cooking_duration = menu_item[0], menu_item[1]
        print("Customer", self.num, "orders", menu_name)

        if self.restaurant.food_container.level < 1:
            print("Food Stock is empty! Customer", self.num, "leaves.")
            self.restaurant.tables.release(request)
            yield self.restaurant.menu.put(menu_item)
            return

        kitchen_request = self.restaurant.kitchen.request()
        yield kitchen_request
        print("Kitchen starts cooking for customer", self.num, "at time", round(self.env.now, 1))
        yield self.env.timeout(cooking_duration)
        print("Meal of customer", self.num, "is ready at time", round(self.env.now, 1))
        self.restaurant.kitchen.release(kitchen_request)

        waiter_request = self.restaurant.waiters.request()
        yield waiter_request
        yield self.env.timeout(1)
        self.restaurant.waiters.release(waiter_request)

        print("Waiter delivers food to customer", self.num, "at time", round(self.env.now, 1))

        yield self.restaurant.food_container.get(1)
        print("Customer", self.num, "has been served at time", round(self.env.now, 1))

        yield self.env.timeout(5)
        print("Customer", self.num, "finishes eating at time", round(self.env.now, 1))

        self.restaurant.tables.release(request)
        yield self.restaurant.menu.put(menu_item)

        self.result_time = self.env.now - arrival_time
        print("Customer", self.num, "spent a total of", round(self.result_time, 1), "time in the restaurant.")

        if self.restaurant.food_container.level < FOOD_STOCK_LIMIT:
            yield self.env.process(self.restaurant.restock_food())

class Restaurant(object):
    def __init__(self, env, num_tables, table_capacity, kitchen_capacity, num_waiters, menu_data):
        self.env = env
        self.tables = sp.Resource(env, capacity=num_tables)
        self.kitchen = sp.Resource(env, capacity=kitchen_capacity)
        self.waiters = sp.Resource(env, capacity=num_waiters)
        self.food_container = sp.Container(env, init=100, capacity=200)
        self.queue = sp.Store(env, capacity=MAX_QUEUE_SIZE)
        self.menu = sp.Store(env)
        self.initialize_menu(menu_data)

    def initialize_menu(self, menu_data):
        menu_df = pd.read_csv(menu_data)
        menu_items = menu_df.values.tolist()
        for item in menu_items:
            menu_name = "Menu " + str(item[0])
            cooking_duration = int(item[7])
            self.menu.put((menu_name, cooking_duration))

    def restock_food(self):
        print("Restocking food at time", round(self.env.now, 1))
        yield self.env.timeout(10)
        yield self.food_container.put(50)
        print("Restocked food at time", round(self.env.now, 1))

def customer_arrivals(env, restaurant):
    customer_num = 0
    while True:
        customer_num += 1
        if len(restaurant.queue.items) >= MAX_QUEUE_SIZE:
            print("Queue at the door is full. Customer", customer_num, "leaves.")
            yield env.timeout(1)
            continue
        customer = Customer(env, customer_num, restaurant)
        env.process(customer.serv_and_eat())
        yield env.timeout(rd.expovariate(1/ARRIVAL_INTERVAL))

env = sp.Environment()
menu_data = "IndianFoodDatasetCSV.csv"
restaurant = Restaurant(env, num_tables=5, table_capacity=4, kitchen_capacity=2, num_waiters=2, menu_data=menu_data)
env.process(restaurant.restock_food())
env.process(customer_arrivals(env, restaurant))

env.run(until=SIMULATION_TIME)
