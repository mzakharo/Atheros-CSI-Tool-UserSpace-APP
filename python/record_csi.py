import zmq, sys, time
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect ("tcp://breath:6969")
socket.setsockopt(zmq.SUBSCRIBE, b"")

fname = sys.argv[1]
with open(fname, 'wb') as f:
    while True:
        datagram = socket.recv()
        print(time.time(), len(datagram))
        f.write(datagram)
