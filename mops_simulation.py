from mops_event import MopsEvent
from mops_event import MopsEventType as MType
from mops_router import MopsRouter
from mops_packet import MopsPacket
from mops_traffic import MopsTraffic
from numpy.random import exponential  # argument to this function is 1/lambda
import time
from numpy.random import poisson
from queue import Empty, PriorityQueue
import math
import matplotlib.pyplot as plt
from collections import Counter

class MopsSimulation:
    def __init__(self, routers_number, traffics, capacities,queue_sizes, max_packet_count=None, debug=False):
        self.start_sim = time.time()
        self.max_packet_count = max_packet_count
        self.traffics = traffics
        self.capacities = capacities
        self.event_count = 0
        self.time = 0
        self.debug = debug
        if queue_sizes is None:
            self.routers = [MopsRouter() for _ in range(routers_number)]
        else:
            if len(queue_sizes) != routers_number:
                raise ValueError("Number of queues sizes isn't equal to router number.")
            else:
                self.routers = [MopsRouter(queue_sizes[i]) for i in range(routers_number)]
        self.packets_in_queue = []
        self.event_queue = PriorityQueue(0)
        self.packet_count = 0
        self.start_to_end_delays = {i: [] for i, _ in traffics.items() if i != -1}
        self.stream_packet_loss = Counter()

    def run(self):
        packet = MopsPacket(0, traffics[0].packet_size, 0, len(self.routers), 'POISS')
        e = MopsEvent(time=self.time, event_type=MType.ARRIVAL, packet=packet, router_idx=0)  # make first event
        self.event_queue.put((self.time, e))

        packet = MopsPacket(1, traffics[-1].packet_size, 0, len(self.routers), 'CBR')
        e = MopsEvent(time=self.time, event_type=MType.ARRIVAL, packet=packet, router_idx=0)  # make first event
        self.event_queue.put((self.time + traffics[-1].next_time(), e))

        while not self.packet_count >= self.max_packet_count:
            t, event = self.event_queue.get()
            self.handle_event(event)

        self.print_statistics()

    def print_handle_event_log(self, event):
        if event.type == MType.ARRIVAL:
            print("{}. event {}, packet idx {}, router idx {}, at {}, queue len: {}"
                  .format(self.event_count, "A", event.packet.packet_idx, event.router_idx, self.time,
                          self.routers[0].buffer.qsize()))
        elif event.type == MType.END_SERVICE:
            print("{}. event {}, packet idx {}, router idx {}, at {}, queue len: {}"
                  .format(self.event_count, "E", event.packet.packet_idx, event.router_idx, self.time,
                          self.routers[0].buffer.qsize()))
        print([i.packet_idx for i in self.routers[0].buffer.queue],
              self.routers[0].busy)

    def handle_event(self, event):
        self.time = event.time
        self.event_count += 1

        if event.type == MType.ARRIVAL:
            self.handle_type_arrival(event)
        elif event.type == MType.END_SERVICE:
            self.handle_type_end_service(event)
        if self.debug:
            self.print_handle_event_log(event)

    def handle_type_arrival(self, event):
        event.packet.times[event.router_idx][MType.ARRIVAL] = self.time

        if self.routers[event.router_idx].full():
            self.routers[event.router_idx].packets_lost += 1
            self.stream_packet_loss[event.packet.first_router] += 1

        elif not self.routers[event.router_idx].busy:
            self.put_end_service(event.router_idx, event.packet)
            self.routers[event.router_idx].busy = True
        else:
            self.routers[event.router_idx].add_packet(event.packet)

        if event.router_idx == event.packet.first_router and event.router_idx in traffics.keys():
            self.packet_count += 1
            if event.router_idx == 0:
                if event.packet.traffic_type == 'CBR':
                    new_packet = MopsPacket(self.packet_count, traffics[-1].packet_size, event.router_idx,
                                        len(self.routers), 'CBR')
                    t = self.time + traffics[-1].next_time()
                    e = MopsEvent(t, MType.ARRIVAL, new_packet, event.router_idx)
                else:
                    new_packet = MopsPacket(self.packet_count, traffics[0].packet_size, event.router_idx,
                                            len(self.routers), 'POISS')
                    t = self.time + traffics[0].next_time()
                    e = MopsEvent(t, MType.ARRIVAL, new_packet, event.router_idx)

            else:
                new_packet = MopsPacket(self.packet_count, traffics[event.router_idx].packet_size, event.router_idx,
                                        len(self.routers))
                t = self.time + traffics[event.router_idx].next_time()
                e = MopsEvent(t, MType.ARRIVAL, new_packet, event.router_idx)
            new_packet.times[event.router_idx][MType.ARRIVAL] = t
            self.event_queue.put((t, e))
        self.packets_in_queue.append(self.routers[0].buffer.qsize())

    def handle_type_end_service(self, event):
        self.routers[event.router_idx].delays.append(event.packet.times[event.router_idx][MType.END_SERVICE] -
                                                     event.packet.times[event.router_idx][MType.ARRIVAL])

        if event.router_idx == len(self.routers) - 1:
            self.start_to_end_delays[event.packet.first_router].append(
                event.packet.times[event.router_idx][MType.END_SERVICE] -
                event.packet.times[event.packet.first_router][MType.ARRIVAL]
            )

        if self.routers[event.router_idx].number_of_packets_in_queue() > 0:  # if buffer isn't empty
            packet_temp = self.routers[event.router_idx].remove_packet()
            self.put_end_service(event.router_idx, packet_temp)  # put event start new service
            self.routers[event.router_idx].busy = True
        else:
            self.routers[event.router_idx].busy = False  # set router busy to false

        if event.router_idx != len(self.routers) - 1:  # if this isn't the last router, send packet to the next one
            e = MopsEvent(self.time, event_type=MType.ARRIVAL, packet=event.packet, router_idx=event.router_idx + 1)
            self.handle_event(e)

    def put_end_service(self, router_idx, packet):
        t = self.time + packet.size/capacities[router_idx]
        e = MopsEvent(time=t, event_type=MType.END_SERVICE, packet=packet, router_idx=router_idx)
        packet.times[router_idx][MType.END_SERVICE] = t
        self.routers[router_idx].waiting.append(self.time - packet.times[router_idx][MType.ARRIVAL])
        self.event_queue.put((t, e))

    def print_statistics(self):
        for key, value in self.start_to_end_delays.items():
            print("Statistics for stream {}: ".format(key))
            print("     Min delay: {}".format(min(value)))
            print("     Average: {}".format(sum(value) / len(value)))
            print("     Max delay: {}".format(max(value)))
            print("     Packets lost: {}".format(self.stream_packet_loss[key]))

        for router in self.routers:
            print("Statistics for router {}: ".format(router))
            print("     Min delay: {}".format(min(router.delays)))
            print("     Average: {}".format(sum(router.delays) / len(router.delays)))
            print("     Max delay: {}".format(max(router.delays)))
            print("     Packets lost: {}".format(router.packets_lost))


if __name__ == '__main__':
    print('1. Default simulation.')
    print('2. Custom simulation. ')
    choice = int(input('Enter choice: '))
    if choice == 1:
        pass
    elif choice == 2:
        routers_number = int(input('How many routers?: '))
        queue_sizes = [int(input('Queue size in '+str(i)+' router [0 for inf]: ')) for i in range(routers_number)]
        routers_with_additional_stream = input('Routers with additional stream: ')
        routers_with_additional_stream = [int(s) for s in routers_with_additional_stream.split() if s.isdigit()]
        routers_with_additional_stream = [i for i in routers_with_additional_stream if i < routers_number and i != 0]

        traffics = {}
        peak_rate = float(input('CBR peak rate in 0 router: '))
        packet_size = int(input('CBR packet size in 0 router: '))
        traffics[-1] = MopsTraffic(peak_rate=peak_rate, packet_size=packet_size)
        lambd = float(input('POISS lambda in 0 router: '))
        packet_size = int(input('POISS packet size in 0 router: '))
        traffics[0] = MopsTraffic(lambd=lambd, packet_size=packet_size)

        for router in routers_with_additional_stream:
            traffic = int(input('Router ' + str(router) + ' traffic [1. CBR, 2. POISS]: '))
            if traffic == 1:
                peak_rate = float(input('Peak rate: '))
                packet_size = int(input('Packet size: '))
                traffics[router] = MopsTraffic(peak_rate=peak_rate, packet_size=packet_size)
            elif traffic == 2:
                lambd = float(input('Lambda: '))
                packet_size = int(input('Packet size: '))
                traffics[router] = MopsTraffic(lambd=lambd, packet_size=packet_size)
        capacities = [float(input('Link capacity between '+str(i) + ' and '+str(i+1) + ' routers'))
                      for i in range(routers_number)]

        max_packet_count = int(input('How many packets?: '))
        s = MopsSimulation(routers_number, traffics, capacities, queue_sizes, max_packet_count, debug=not True)
        s.run()


