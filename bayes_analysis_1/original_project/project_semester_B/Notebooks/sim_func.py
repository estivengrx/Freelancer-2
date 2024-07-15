import numpy as np
import pandas as pd
import pickle as pkl
import simpy
import os
import matplotlib.pyplot as plt
import sys
import simpy


class Customer:
    def __init__(self, p_id,  arrival_time):
        self.id = p_id
        self.arrival_time = arrival_time

class GGc:

    def __init__(self, inter_dist,  ser_means):

        self.curr_hour = 0
        self.curr_day = 1

        self.ser_means = ser_means
        self.inter_dist = inter_dist
        self.env = simpy.Environment()  # Initializing simpy Environment
        self.customer_counter = {}  # The counter of customer per station - this is for monitoring the simulaiton
        self.last_event_time = {}  # The time the last event took place at station - helps computing service/inter arrivals
        self.num_cust_durations = {}  # To compute the distribution of number of customers at each station
        self.num_cust_sys = {}  # the total number of customers that arrived at each station
        self.last_departure = {}  # the last departure timestamp at each station
        self.server = {}  # This holds the simpy object of a server

        # There object are the simulation result

        self.event_log_customer_id_list = []  # id_number of customer
        self.event_log_num_cust_list = []  # num customers in the station
        self.event_log_type_list = []  # the type of event (arrival or service)
        self.event_log_waiting = []
        self.event_log_time_stamp = []  # the absolute time stamp (i.e., exact date and time)
        self.event_log_env_time = []  # the Simpy enviroment timestamp

        # initilizing the events

        self.customer_counter = 0
        self.last_event_time = 0
        self.num_cust_durations = np.zeros(500)
        self.num_cust_sys = 0
        self.last_departure = 0

        self.event_log_waiting = []
        self.event_log_customer_id_list = []
        self.event_log_num_cust_list = []
        self.event_log_type_list = []
        self.event_log_time_stamp = []
        self.event_log_env_time = []

        self.event_log_env_time_week = []
        self.event_log_env_time_day = []
        self.event_log_env_time_hour = []

        self.num_cust_end_hour = []
        self.day_end_hour = []
        self.hour_end_hour = []


        self.server = simpy.PriorityResource(self.env, capacity=1)

        self.sec_in_week = 7 * 24 * 60 * 60
        self.sec_in_day = 24 * 60 * 60
        self.sec_in_hour = 60 * 60
        self.sec_in_min = 60

    def give_times(self, sim_time):



        week = int(sim_time / self.sec_in_week)
        day = (int(sim_time / self.sec_in_day)) % 7
        hour = int(sim_time / self.sec_in_hour) % 24
        minute = int(sim_time / self.sec_in_min) % 60

        tot =  self.sec_in_week * week +  self.sec_in_day * (day) + hour *  self.sec_in_hour + minute *  self.sec_in_min
        sec = sim_time-tot

        return (week, day + 1, hour, minute, sec)


    def event_log_updates(self,  customer, event_type):

        sim_time = self.env.now

        week, day, hour, minute, sec = self.give_times(sim_time)

        if self.curr_hour != hour:
            self.num_cust_end_hour.append(self.num_cust_sys)
            self.day_end_hour.append(self.curr_day)
            self.hour_end_hour.append(self.curr_hour)

        self.curr_hour = hour
        self.curr_day = day

        self.event_log_customer_id_list.append(customer.id)
        self.event_log_num_cust_list.append(self.num_cust_sys)
        self.event_log_type_list.append(event_type)
        self.event_log_time_stamp.append(self.env.now)
        self.event_log_env_time.append(self.env.now)

        self.event_log_env_time_week.append(week)
        self.event_log_env_time_day.append(day)
        self.event_log_env_time_hour.append(hour)




    def run(self):
        # Initializing extrenal arrival streams at each station

        self.env.process(self.customer_arrivals())
        # activating the simulation - g.sim_end_time_upper_bound is an upper bound of the time the simulation runs
        # This is just a techincal issue to avoid infinte loop. In practice, simulations stops at the end of arrivals.
        self.env.run(until=float(7 * 24 * 60 * 60))

    def service(self, customer):

        # Requesting service
        with self.server.request(priority=1) as req:
            yield req

            _, day, hour, _, _ = self.give_times(self.env.now)



            service_time = np.random.exponential(self.ser_means[day-1, hour])

            self.event_log_updates(customer, 'Enter_service')
            yield self.env.timeout(service_time)

            self.num_cust_sys -= 1  # updating num of customers
            self.last_departure = self.env.now  # Updating the last departure

            # Create a function of filling the event log
            self.event_log_updates(customer, 'Departure')

            # The time elapsed since the last event
            tot_time = self.env.now - self.last_event_time
            # For computing the
            self.num_cust_durations[int(self.num_cust_sys)] += tot_time

            self.last_event_time = self.env.now  # updating the last event in this station

    def customer_arrivals(self):

        # Here we simulate external arrivals

        while True:


            # getting the current inter-arrival according to the true inter-arrival
            # in future code - inter-arrivals would be random govern by some distribution

            # print(self.give_times(self.env.now))
            inter_arrival = np.random.exponential(self.inter_dist)

            yield self.env.timeout(inter_arrival)  # holding the simulation for inter-arrival

            # Extracting the cusotmer id
            curr_customer = self.customer_counter

             # updating the number of arrivals in the network
            self.customer_counter += 1  # updating the number of cusotmers in the station

            arrival_time = self.env.now  # saving the Simpy customer arrival time
            # initialing a Customer object, it holds the follwoing: id, priority, arrival_time, date_time_arrival_time
            customer = Customer(curr_customer,  arrival_time)

            # Updating simulation results

            self.event_log_updates(customer, 'Arrival')

            # The time elapsed since the last event
            tot_time = self.env.now - self.last_event_time

            # for monitoring steady-state
            self.num_cust_durations[int(self.num_cust_sys)] += tot_time

            self.last_event_time = self.env.now  # updating the last event in this station
            self.num_cust_sys += 1  # updating number of customers
            self.env.process(self.service(customer))  # Sending the customer to service

def Sim_func(ser_means):

    end_hour_df_tot = pd.DataFrame()

    inter_dist = 12

    for ind in range(10):

        ggc = GGc(inter_dist,  ser_means)  # This object holds all the details require for simulating
        ggc.run()

        # Converting the log lists into a single dataframe
        event_log = {}

        event_log = pd.DataFrame({
            'customer_id': ggc.event_log_customer_id_list,
            'num_cust': ggc.event_log_num_cust_list,
            'event': ggc.event_log_type_list,
            'time_stamp': ggc.event_log_time_stamp,
            'env_time': ggc.event_log_env_time,
                'day': ggc.event_log_env_time_day,
            'hour':ggc.event_log_env_time_hour
        })

        if ind == 0:

            end_hour_df = pd.DataFrame({
                'day': ggc.day_end_hour,
                'hour': ggc.hour_end_hour,
                'num_cust_end_hour': ggc.num_cust_end_hour
            })

            end_hour_df_tot = end_hour_df
        else:
            end_hour_df_tot['num_cust'+ str(ind)] = ggc.num_cust_end_hour

    # Computing num customers in the system distribution - not in the dataframe
    pkl.dump(end_hour_df_tot, open('end_hour.pkl', 'wb'))
    curr_path = 'event_log.pkl'
    pkl.dump((event_log, inter_dist), open(curr_path, 'wb'))


    return end_hour_df_tot



if __name__ == '__main__':


    pass
