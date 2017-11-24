import time
import traceback
from random import randint
import hashlib

# TODO: relocate net packages
from swarmnet import Ring, log
from udptl import UDPTL, DEFAULT_PORT, parse_address
from netaddr import IPNetwork


def test_single_node():
    # hostid = socket.gethostbyaddr(socket.gethostname())[0]
    # hostid = socket.getfqdn()

    import platform

    # import ipgetter
    # ip = ipgetter.myip()
    # print 'My public IP address is:', ip


    # # default = ifcfg.default_interface()
    # # pprint(default)

    # for interface in ifcfg.interfaces().values():
        # if interface['inet'] == ip:
            # print "Your has WAN address!! :)"
            # break
    # else:
        # print "You are behind a NAT"

    port = DEFAULT_PORT
    address = ('', port)
    node = UDPTL(address)
    node.start()

    unid = '%s|%s' % (platform.node(), platform.platform())
    nid = hashlib.sha1(unid).hexdigest()
    print nid, unid
    log.info('%s %s', nid, unid)
    ring = Ring(nid, node)

    KNOWN_ADDRESS = ('room1408.tk', port)
    KNOWN_ADDRESS = ('94.177.253.187', port)
    ring.add_node(KNOWN_ADDRESS)

    try:
        while True:
            print '(quit to exit) '
            print '>',
            cmd = raw_input()
            if cmd == 'quit':
                break

            if cmd.startswith('ping'):
                command, address = cmd.split()
                msg = ring.new_message(command)
                address = parse_address(address)
                ring.send(msg, address)

    except KeyboardInterrupt:
        pass
    except Exception, why:
        traceback.print_exc()
        print why

    print "Exiting."
    node.stop()

    foo = 1


if __name__ == '__main__':
    test_single_node()

