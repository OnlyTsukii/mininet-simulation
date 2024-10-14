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
              nat1           
               |             
               s1             
               |                    
            h1-eth0      
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
    
    inetIntf = 'nat1-eth0' 
    localIntf = 'nat1-eth1'
    localIP = '192.168.1.1'
    localSubnet = '192.168.1.0/24' 
    natParams = { 'ip' : '%s/24' % localIP }
    nat = topo.addHost('nat1', cls=NAT, subnet=localSubnet,
                        inetIntf=inetIntf, localIntf=localIntf)
    switch =topo.addSwitch('s1')
    
    topo.addLink(nat, s0, intfName1=inetIntf)
    topo.addLink(nat, switch, intfName1=localIntf, params1=natParams)
    
    topo.addLink(h1, switch)

    net = Mininet(topo=topo, waitConnected=True, link=TCLink)

    host1 = net.get("h1")
    runCmd(host1, 'sysctl net.ipv4.ip_forward=1')
       
    hostIPs = '192.168.1.100/24'
    hostIP = '192.168.1.100' 
    hostIntf = 'h1-eth0' 
    hostGateway = '192.168.1.1'
    hostTableName = 'gateway1'

    host1.setIP(hostIPs, intf=hostIntf)

    runCmd(host1, f'route add default gw {hostGateway}')
    runCmd(host1, f'ip route add 10.0.0.0/24 via {hostGateway} dev {hostIntf} table {hostTableName}')
    runCmd(host1, f'ip rule add from {hostIP} table {hostTableName}')

    net.start()

    runCmd(host1, "tc qdisc replace dev h1-eth0 root handle 1: netem delay 100ms rate 10mbit")

    runCmd(host1, "tc qdisc show dev h1-eth0")

    host0 = net.getNodeByName('h0')
    runCmd(host0, "tc qdisc add dev h0-eth0 root handle 3: netem rate 10mbit")

    thread1 = threading.Thread(target=runCmd, args=(host0, '/home/ccl/quic-go/server'))
    thread2 = threading.Thread(target=runCmd, args=(host1, '/home/ccl/quic-go/client'))

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
