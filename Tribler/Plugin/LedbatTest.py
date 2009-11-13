import sys

from Tribler.Plugin.UploadCongestionControl.constants import *
from Tribler.Plugin.UploadCongestionControl.ledbat import *
from Tribler.Plugin.UploadCongestionControl.tcp import *

USE_BACKGROUND_PROCESS_STUFF = 0

if (USE_BACKGROUND_PROCESS_STUFF == 1):
    from Tribler.Plugin.BackgroundProcess import *
import random

#TEST_DESTINATION = "127.0.0.1"
#TEST_DESTINATION = "pygmee.tribler.org"
TEST_DESTINATION = "p2p-next-09.grid.pub.ro"

NUM_LISTEN_UDP_SOCKS = 10

class TrafficShaper:
    def __init__(self, maxRate = 100000000.0):
        self.spike1 = 0
        self.timeSpike1 = 0.0
        self.spike2 = 0
        self.timeSpike2 = 0.0
        self.maxRate = maxRate
        self.minRate = 1200.0
    
    def shapeTraffic(self, tstart, currentRate):
        tnow = time.time()
        if (tnow - tstart >= 29.9 and tnow - tstart <= 32.1 and self.spike1 == 0):
            self.spike1 = 1
            self.timeSpike1 = tnow
            return max([self.minRate, 0.01 * currentRate])
        elif (self.spike1 == 1 and tnow - self.timeSpike1 > 2.0):
            self.spike1 = 2
            return self.maxRate
        elif (self.spike1 == 1 and tnow - self.timeSpike1 <= 2.0):
            return max([self.minRate, 0.01 * currentRate])
        elif (self.spike1 == 2):
            if (tnow - tstart >= 91.9 and tnow - tstart <= 94.1 and self.spike2 == 0):
                self.spike2 = 1
                self.timeSpike2 = tnow
                return self.maxRate
            elif (self.spike2 == 1 and tnow - self.timeSpike2 > 2.0):
                self.spike2 = 2
                return max([self.minRate, 0.01 * currentRate])
            elif (self.spike2 == 1 and tnow - self.timeSpike2 <= 2.0):
                return self.maxRate
            elif (self.spike2 == 2):
                return max([self.minRate, 0.01 * currentRate])
            elif (tnow - tstart <= 62.0):
                return self.maxRate
            else:
                return max([self.minRate, 0.01 * currentRate])
        else:
            return self.maxRate

def testSender(mypermid, tcpPort = DEFAULT_TCP_BACKGROUND_TRAFFIC_PORT, minLedbatPort = DEFAULT_SOURCE_LEDBAT_UDP_PORT, maxLedbatPort = DEFAULT_SOURCE_LEDBAT_UDP_PORT + 1 * NUM_LISTEN_UDP_SOCKS - 1):
    #print "Sender test"

    numTCP = 1
    numTCPConns = 1

    numLedbat = 1
    numLedbatUDPConns = 1

    plotter = Plotter(1.0, mypermid)
    trafficShaper = TrafficShaper()

    if (USE_BACKGROUND_PROCESS_STUFF == 1):
        LEDBAT_TEST_RUNNING_LOCK.acquire()
        LEDBAT_TEST_RUNNING = 1
        LEDBAT_TEST_RUNNING_LOCK.release()

    deadline = time.time() + 133.0

    lbtg = []
    for i in range(numTCP):
        btg = BackgroundTrafficGenerator(serverIP = TEST_DESTINATION, duration = 1300.0, deadline = deadline, chunkSize = 500, numChunks = 1000000, transferRate = 5000000.0 + i, TCPConns = numTCPConns, id = "TCP_" + str(i) + "_BW", trafficShaper = trafficShaper, plotter = plotter)
        lbtg.append(btg)

    for btg in lbtg:
        btg.start()
    
    plotter.start()

    ludp = []
    for i in range(numLedbat):
        ledbat_udp = Ledbat(id = "Ledbat_" + str(i), numUDPSocks = numLedbatUDPConns, plotter = plotter)
        ledbat_udp.destPort = random.randint(minLedbatPort, maxLedbatPort)
        print "Port=", ledbat_udp.destPort, "(min=", minLedbatPort, "; max=", maxLedbatPort, ")"
        ludp.append(ledbat_udp)

    time.sleep(4.0)

    for xudp in ludp:
        xudp.start()
        time.sleep(0.06)
    
    numPackets = 1000000000
    i = 0

    packetSize = 1024 #random.randint(4096, 16384)
    packet = ""
    for j in range(packetSize):
        packet = packet + str(random.randint(1,9))

    while (i < numPackets and time.time() < deadline):
        i += 1
        for xudp in ludp:
            xudp.sendPacket(packet, xudp.id, TEST_DESTINATION, xudp.destPort, 1)
        if (i % 1000 == 0):
            print >>sys.stderr,"Sent", i, "packets; Time left=", deadline - time.time(), "sec"
    
    #print "Finished sending all the packets"
    
    for xudp in ludp:
        xudp.stopRunning()
    
    plotter.stopRunning()

    if (USE_BACKGROUND_PROCESS_STUFF == 1):
        LEDBAT_TEST_RUNNING_LOCK.acquire()
        LEDBAT_TEST_RUNNING = 0
        LEDBAT_TEST_RUNNING_LOCK.release()

    for xudp in ludp:
        xudp.join()
    
    #print "Joined Ledbat+CC threads"

    for btg in lbtg:
        btg.join()
    
    #print "Joined TCP threads"

    plotter.join()
    #print "Joined Plotter thread"

def testReceiver(ledbatStartingPort, tcpPort):
    print "Receiver test"
    btr = BackgroundTrafficReceiver(port = tcpPort)
    btr.start()
    ledbat = Ledbat(id = "recv", startingUDPPort = ledbatStartingPort, numUDPSocks = NUM_LISTEN_UDP_SOCKS)
    ledbat.start()
    time.sleep(12000000.0)
    ledbat.stopRunning()
    btr.stopRunning()
    ledbat.join()
    btr.join()

if __name__=="__main__":
    if (len(sys.argv) == 1 or sys.argv[1] == "send"):
        testSender("permid-009")
    elif (len(sys.argv) > 1 and sys.argv[1] == "recv"):
        if (len(sys.argv) > 3):
            testReceiver(int(sys.argv[2]), int(sys.argv[3]))
        elif (len(sys.argv) > 2):
            testReceiver(int(sys.argv[2]), DEFAULT_TCP_BACKGROUND_TRAFFIC_PORT)
        else:
            testReceiver(DEFAULT_SOURCE_LEDBAT_UDP_PORT, DEFAULT_TCP_BACKGROUND_TRAFFIC_PORT)
