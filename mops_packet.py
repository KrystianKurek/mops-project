
class MopsPacket:
    def __init__(self, packet_idx, size, first_router, routers_number, traffic_type=None):
        self.packet_idx = packet_idx
        self.size = size
        self.first_router = first_router
        self.traffic_type = traffic_type
        """times is a dictionary that will store:
           key - number of specific router
           value - another dict that will store:
               key - event type
               value - time of specific event
            
            so finally if you want to get time (for example) of packet arrival to second router you should do:
            self.times[2][type.ARRIVAL] 
        """
        self.lost = False
        self.times = {i: dict() for i in range(routers_number)}
