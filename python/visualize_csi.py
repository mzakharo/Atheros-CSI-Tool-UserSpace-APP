#!/usr/bin/python -i
# @file visualize_csi.py
#
# @brief Simple visualization based on udp packet data
#
# uses: pyqtgraph, pyqt
#
# Copyright 2016 NovelSense UG
# Authors: Niklas Saenger, Markus Scholz
#
# NOTICE: All information contained herein is, and remains the
# property of NovelSense UG and its suppliers, if any.  The
# intellectual and technical concepts contained herein are
# proprietary to NovelSense UG and its suppliers, and are protected
# by trade secret or copyright law. Dissemination of this
# information or reproduction of this material is strictly forbidden
# unless prior written permission is obtained from NovelSense UG.
# ------------------------------------------------------------------------------------------
import sys
import os
from socket import *
import struct
from struct import unpack, pack
from time import clock, time, sleep


import argparse
import collections
import numpy as np
import copy

from decimal import Decimal
from collections import deque

from pyqtgraph.Qt import QtGui, QtCore
from PyQt4 import QtNetwork
import pyqtgraph as pg
# need this to load ui file from QT Creator
import PyQt4.uic as uic

from read_csi import unpack_csi_struct
import io
import zmq.green as zmq
import gevent

#https://www.rapidtables.com/web/color/RGB_Color.html#color-table
COLORS = (
            ((128,0,0), #maroon
            (255,99,71), #tomato
            (255,160,122),), # light salmon
            ((0,100,0), #dark green
            (34,139,34), #forest green
            (0,255,0),), #lime
            ((0,0,128), #navy
            (0,0,255), #blue
            (0,191,255),)) #deep sky blue


class ZMQ_listener():

    def __init__(self, sock, form):
        self.sock = sock
        self.form = form

    def datagramReceived(self):
        while True:
            datagram = self.sock.recv()
            f = io.BytesIO(datagram)
            csi_inf = unpack_csi_struct(f)
            if(csi_inf.csi is not None):
                self.calc(csi_inf)

    def calc(self, csi_inf):
        csi = csi_inf.csi
        amps = np.empty(csi.shape)
        phases = np.empty(csi.shape)

        for nr in range(csi.shape[0]):
            for nc in range(csi.shape[1]):
                p = csi[nr, nc, :]

                amplitude = np.abs(p)
                mx = np.max(amplitude)
                #mn = np.min(amplitude)
                #self.form.amplitude = (amplitude - mn) / (mx - mn)
                amps[nr, nc, :] = amplitude / mx

                phase = np.angle(p)
                phase = np.unwrap(phase)
                mn = np.min(phase)
                mx = np.max(phase)
                phases[nr, nc, :] = (phase - mn) / (mx - mn)

        self.form.amps = amps
        self.form.phases = phases
        carrier = np.arange(csi.shape[2], dtype=int)
        self.form.carrier = carrier

class UI(QtGui.QWidget):
    def __init__(self, app, parent=None):
        super(UI, self).__init__(parent)
        self.app = app

        ui = os.path.join(os.path.dirname(__file__), 'window.ui')
        # get and show object and layout
        uic.loadUi(ui, self)

        self.carrier = None

        self.setWindowTitle("Visualize CSI")

        amp = self.box_amp
        amp.setBackground('w')
        amp.setWindowTitle('Amplitude')
        amp.setLabel('bottom', 'Carrier', units='')
        amp.setLabel('left', 'Amplitude', units='')
        amp.setYRange(0, 3, padding=0)
        amp.setXRange(0, 114, padding=0)
        self.amp = amp
        self.penAmp = {}  # amp.plot(pen={'color': (0, 100, 0), 'width': 3})

        phase = self.box_phase
        phase.setBackground('w')
        phase.setWindowTitle('Phase')
        phase.setLabel('bottom', 'Carrier', units='')
        phase.setLabel('left', 'Phase', units='')
        phase.setYRange(0, 3, padding=0)
        phase.setXRange(0, 114, padding=0)
        self.phase = phase
        self.penPhase = {} # phase.plot(pen={'color': (0, 100, 0), 'width': 3})

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(20)

    @QtCore.pyqtSlot()
    def update_plots(self):
        if self.carrier is not None:
            for nr in range(self.amps.shape[0]):
                for nc in range(self.amps.shape[1]):
                    key = (nr, nc)
                    amp = self.amps[nr, nc, :]
                    phase = self.phases[nr, nc, :]
                    if key not in self.penAmp:
                        self.penAmp[key] = self.amp.plot(pen={'color': COLORS[nr][nc], 'width': 3})
                    self.penAmp[key].setData(self.carrier, amp + (nr))

                    if key not in self.penPhase:
                        self.penPhase[key] = self.phase.plot(pen={'color': COLORS[nr][nc], 'width': 3})
                    self.penPhase[key].setData(self.carrier, phase + (nr))
            self.process_events()  ## force complete redraw for every plot

    def process_events(self):
        self.app.processEvents()

def mainloop(app):
    while True:
        app.processEvents()
        while app.hasPendingEvents():
            app.processEvents()
            gevent.sleep(.1)
        gevent.sleep(.1) # don't appear to get here but cooperate again

## Start Qt event loop unless running in interactive mode.
if (__name__ == '__main__'):
    import sys

    app = QtGui.QApplication([])
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect ("tcp://breath:6969")
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    form = UI(app=app)
    form.show()
    
    e=ZMQ_listener(sock=socket, form=form)

    gevent.joinall([gevent.spawn(e.datagramReceived), gevent.spawn(mainloop, app)])
    #if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    #    QtGui.QApplication.instance().exec_()



