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
import pyqtgraph as pg
# need this to load ui file from QT Creator
import PyQt4.uic as uic

from read_csi import unpack_csi_struct
import io
import zmq.green as zmq
import gevent

from scipy.signal import butter, lfilter

def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y


# Filter requirements.
order = 6
fs = 10.0       # sample rate, Hz
cutoff = 0.5      # desired cutoff frequency of the filter, Hz

class Path():
    def __init__(self):
        self.hamp = np.zeros((20,56))
        self.hamp2 = np.zeros((30,56))
        self.sads = np.zeros(56)
        self.b, self.a = butter_lowpass(cutoff, fs, order=order)

    def calc(self, rxs):
        self.amplitude = self.norm(np.abs(rxs))

        self.hamp[1:] = self.hamp[:-1]
        self.hamp[0] =self.amplitude 

        new = []
        for i in range(56):
            y = lfilter(self.b, self.a, self.hamp[:,i])
            new.append(y[-1])

        nnew = np.array(new)
        self.hamp2[1:] = self.hamp2[:-1]
        self.hamp2[0] =nnew

        val = np.mean(self.hamp2, axis=0)
        sad = np.mean(np.abs(nnew-val))
        self.sads[:-1] = self.sads[1:]
        self.sads[-1] = sad
    def norm(self, amplitude):
        min = np.min(amplitude)
        return ((amplitude - min) /
                (np.max(amplitude) - min)) * 100 

class ZMQ_listener():

    def __init__(self, carrier, amplitudes, sock, form):
        self.carrier      =   carrier
        self.sock = sock
        self.form = form
        for i in range(56):
            carrier.append(i)
        self.form.carrier = carrier
        self.path = []
        for i in range(6):
            self.path.append(Path())

    def datagramReceived(self):
        while True:
            datagram = self.sock.recv()
            f = io.BytesIO(datagram)
            csi_inf = unpack_csi_struct(f)
            if(csi_inf.csi != 0):
                self.calc(csi_inf)

    def calc(self, csi_inf):
        
        csi = np.array(csi_inf.csi)
        print(csi.shape)
        k = 0
        for i in range(2):
            for j in range(3):
                rxs = csi[:,i,j]
                self.path[k].calc(rxs)
                self.form.form1[k] = self.path[k].sads
                k+=1
        self.form.phase = self.path[1].amplitude

class UI(QtGui.QWidget):
    def __init__(self, app, parent=None):
        super(UI, self).__init__(parent)
        self.app = app

        # get and show object and layout
        uic.loadUi('window.ui', self)

        self.setWindowTitle("Visualize CSI")

        self.carrier = []
        self.form1 = np.zeros((6,56))
        self.phase = np.zeros(56)
        amp = self.box_amp
        amp.setBackground('w')
        amp.setWindowTitle('Amplitude')
        amp.setLabel('bottom', 'Carrier', units='')
        amp.setLabel('left', 'Amplitude', units='')
        amp.setYRange(0, 10, padding=0)
        amp.setXRange(0, 56, padding=0)

        self.penAmps = []
        self.colors = [ (100,100,0), (0,100,0), (100,0,100), (0,0,100),
                (100,0,0), (0,100,100)]
        for i in range(6):
            self.penAmps.append(amp.plot(pen={'color': self.colors[i], 'width':
                3}))
        
        phase = self.box_phase
        phase.setBackground('w')
        phase.setWindowTitle('Phase')
        phase.setLabel('bottom', 'Carrier', units='')
        phase.setLabel('left', 'Phase', units='')
        phase.setYRange(0, 200, padding=0)
        phase.setXRange(0, 56, padding=0)
        self.penPhase = phase.plot(pen={'color': (0, 100, 0), 'width': 3})

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(20)
        self.amp = amp
        self.box_phase = phase

    @QtCore.pyqtSlot()
    def update_plots(self):
        i = 0
        for amp in self.penAmps:
            amp.setData(self.carrier, self.form1[i])
            i+=1
        self.penPhase.setData(self.carrier, self.phase)
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

    app = QtGui.QApplication([])
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect ("tcp://192.168.1.136:6969")
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    form = UI(app=app)
    form.show()
    
    e=ZMQ_listener([], [], sock=socket, form=form)

    gevent.joinall([gevent.spawn(e.datagramReceived), gevent.spawn(mainloop, app)])
    #if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    #    QtGui.QApplication.instance().exec_()



