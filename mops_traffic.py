from numpy.random import exponential


class MopsTraffic:
    def __init__(self, lambd=None, peak_rate=None, packet_size=None):
        self.packet_size = packet_size
        if lambd is None:
            self.next_time_CBR = packet_size/peak_rate
            self.next_time = self.return_CBR_time
        elif peak_rate is None:
            self.lambd = lambd
            self.next_time = self.return_POISS_time
        else:
            raise AttributeError("Both lambda and CBR parameters are None")

    def return_CBR_time(self):
        return self.next_time_CBR

    def return_POISS_time(self):
        return exponential(1/self.lambd)
