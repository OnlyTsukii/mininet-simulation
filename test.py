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
 h1-eth0        h1-eth1
    |              |
    ----------------
           |
           h1
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
    topo.addLink(h1, s0)
    topo.addLink(h1, s0)

    net = Mininet(topo=topo, waitConnected=True, link=TCLink)

    host0 = net.get("h0")
    host0.setIP('10.0.0.3/24', intf='h0-eth0')
    runCmd(host0, 'sudo sysctl net.ipv4.ip_forward=1')

    host1 = net.get("h1")
    runCmd(host1, 'sudo sysctl net.ipv4.ip_forward=1')
    host1.setIP('10.0.0.1/24', intf='h1-eth0')
    host1.setIP('10.0.0.2/24', intf='h1-eth1')

    runCmd(host1, f'ip route add 10.0.0.0/24 dev h1-eth0 table {H1_TABLE_1}')
    runCmd(host1, f'ip route add 10.0.0.0/24 dev h1-eth1 table {H1_TABLE_2}')

    # runCmd(host1, f'ip route add default dev h1-eth0 table gateway1')
    # runCmd(host1, f'ip route add default dev h1-eth1 table gateway2')

    runCmd(host1, f'ip rule add from 10.0.0.1 table {H1_TABLE_1}')
    runCmd(host1, f'ip rule add from 10.0.0.2 table {H1_TABLE_2}')

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
