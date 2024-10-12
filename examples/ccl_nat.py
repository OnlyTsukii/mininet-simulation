import time
import threading

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink  
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.util import irange
from mininet.nodelib import NAT

"""
               h0
               |
               s0
               |
        ----------------
        |              |
       nat1           nat2
        |              |
        s1             s2
        |              |
   --------------------------
   |    |              |    |  
   | h1-eth0        h1-eth1 |
   |    |              |    |
   |    ----------------    |
   |           |            |
   |           h1           | 
   --------------------------
   
"""

H1_TABLE_1 = 'gateway1'
H1_TABLE_2 = 'gateway2'
NAT1_TABLE = 'gateway3'
NAT2_TABLE = 'gateway4'

def getTC(id, intf, rate, delay, loss=None) -> str:
    cmd = f"tc qdisc replace dev {intf} root handle {id}: netem delay {delay} rate {rate}"
    if loss:
        cmd += f" loss {loss}"
    return cmd

def runCmd(host, cmd):
    result = host.cmd(cmd)
    print(f"Command output from {host.name}:")
    print(result)

def createNetwork():
    topo = Topo()

    h0 = topo.addHost('h0')

    s0 = topo.addSwitch('s0')
    topo.addLink(h0, s0)

    h1 = topo.addHost('h1')
    
    for i in irange(1, 2):
        inetIntf = 'nat%d-eth0' % i
        localIntf = 'nat%d-eth1' % i
        localIP = '192.168.%d.1' % i
        localSubnet = '192.168.%d.0/24' % i
        natParams = { 'ip' : '%s/24' % localIP }
        nat = topo.addHost('nat%d' % i, cls=NAT, subnet=localSubnet,
                            inetIntf=inetIntf, localIntf=localIntf)
        switch =topo.addSwitch('s%d' % i)
       
        topo.addLink(nat, s0, intfName1=inetIntf)
        topo.addLink(nat, switch, intfName1=localIntf, params1=natParams)
      
        topo.addLink(h1, switch)

    net = Mininet(topo=topo, waitConnected=True, link=TCLink)

    host1 = net.get("h1")
    runCmd(host1, 'sudo sysctl net.ipv4.ip_forward=1')
       
    for i in irange(1, 2):
        hostIPs = '192.168.%d.100/24' % i
        hostIP = '192.168.%d.100' % i
        hostIntf = 'h1-eth%d' % int(i-1)
        hostGateway = '192.168.%d.1' % i
        hostSubnet = '192.168.%d.0/24' % i
        hostTableName = 'gateway%d' % i

        host1.setIP(hostIPs, intf=hostIntf)

        runCmd(host1, f'route add default gw {hostGateway}')
        runCmd(host1, f'ip route add 10.0.0.0/24 via {hostGateway} dev {hostIntf} table {hostTableName}')
        runCmd(host1, f'ip rule add from {hostIP} table {hostTableName}')

    net.start()

    runCmd(host1, "tc qdisc replace dev h1-eth0 root handle 1: netem delay 1ms rate 30mbit")
    runCmd(host1, "tc qdisc replace dev h1-eth1 root handle 2: netem delay 100ms rate 30mbit")

    runCmd(host1, "tc qdisc show dev h1-eth0")
    runCmd(host1, "tc qdisc show dev h1-eth1")

    host0 = net.getNodeByName('h0')
    runCmd(host0, "tc qdisc add dev h0-eth0 root handle 3: netem rate 30mbit")

    thread1 = threading.Thread(target=runCmd, args=(host0, '/home/ccl/mpquic-go/server'))
    thread2 = threading.Thread(target=runCmd, args=(host1, '/home/ccl/mpquic-go/client'))

    thread1.start()
    time.sleep(3)
    thread2.start()

    thread1.join()
    thread2.join()

    # CLI(net)

    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    createNetwork()
