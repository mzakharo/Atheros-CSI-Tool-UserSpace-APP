#!/usr/bin/python -i
# @file client.py
#
# @brief Function to read binary files
#
#
# Copyright 2017 NovelSense UG
# Authors: Niklas Saenger
#
# NOTICE: All information contained herein is, and remains the
# property of NovelSense UG and its suppliers, if any.  The
# intellectual and technical concepts contained herein are
# proprietary to NovelSense UG and its suppliers, and are protected
# by trade secret or copyright law. Dissemination of this
# information or reproduction of this material is strictly forbidden
# unless prior written permission is obtained from NovelSense UG.
# ------------------------------------------------------------------------------------------

import io
import struct
import logging
from math import atan2,atan
import numpy as np
from numba import njit
import time 

BITS_PER_BYTE = 8
BITS_PER_SYMBOL = 10
bitmask = (1 << BITS_PER_SYMBOL) - 1
DEBUG = 1
class csi_struct: 
    pass


def unpack_csi_struct(f, endianess='>'): # Big-Endian as Default Value
        csi_inf = csi_struct()
        #csi_inf.field_len   = struct.unpack(endianess + 'H', f.read(2))[0] #Block Length     1Byte
        csi_inf.timestamp   = struct.unpack(endianess + 'Q' ,f.read(8))[0] #TimeStamp      8Byte
        csi_inf.timestamp /= 1e3
        csi_inf.csi_len     = struct.unpack(endianess + 'H' ,f.read(2))[0] #csi_len        2Byte
        csi_inf.channel     = struct.unpack(endianess + 'H' ,f.read(2))[0] #tx             2Byte
        csi_inf.err_info    = struct.unpack(endianess + 'B' ,f.read(1))[0] #err_info       1Byte
        csi_inf.noise_floor = struct.unpack(endianess + 'b' ,f.read(1))[0] #noisefloor     1Byte
        csi_inf.rate        = struct.unpack(endianess + 'B' ,f.read(1))[0] #rate           1Byte
        csi_inf.bw          = struct.unpack(endianess + 'B' ,f.read(1))[0] #bandWidth      1Byte
        csi_inf.num_tones   = struct.unpack(endianess + 'B' ,f.read(1))[0] #num_tones      1Byte
        csi_inf.nr          = struct.unpack(endianess + 'B' ,f.read(1))[0] #nr             1Byte
        csi_inf.nc          = struct.unpack(endianess + 'B' ,f.read(1))[0] #nc             1Byte
        csi_inf.rssi        = struct.unpack(endianess + 'B' ,f.read(1))[0] #rssi           1Byte
        csi_inf.rssi1       = struct.unpack(endianess + 'B' ,f.read(1))[0] #rssi1          1Byte
        csi_inf.rssi2       = struct.unpack(endianess + 'B' ,f.read(1))[0] #rssi2          1Byte
        csi_inf.rssi3       = struct.unpack(endianess + 'B' ,f.read(1))[0] #rssi3          1Byte
        csi_inf.payload_len = struct.unpack(endianess + 'H' ,f.read(2))[0] #payload_len    2Byte Total: 27Byte + csi_len + payload_len
        #print(csi_inf.timestamp, time.time(), csi_inf.csi_len, csi_inf.payload_len, csi_inf.nr, csi_inf.nc, csi_inf.num_tones)
        if(csi_inf.csi_len > 0 and csi_inf.nc > 0):
            csi_buf     = f.read(csi_inf.csi_len) #csi        csi_len
            csi_inf.csi = read_csi(csi_buf, csi_inf.num_tones, csi_inf.nc, csi_inf.nr)
        else:
            csi_inf.csi = None
        if(csi_inf.payload_len > 0):
            csi_inf.payload_buf = f.read(csi_inf.payload_len) #payload_len    payload_len
        else:
            csi_inf.payload_buf = None
        
        return csi_inf

@njit(cache=True)
def read_csi(buf, num_tones, nc, nr):
    csi = np.zeros((nr, nc, num_tones), dtype=np.complex128)
    bits_left = 16
    cur_data  = buf[0]
    cur_data += buf[1] << BITS_PER_BYTE
    idx= 2
    for i in range(0, num_tones):
        for nc_idx in range(0, nc):
            for nr_idx in range(0, nr):
                if((bits_left - BITS_PER_SYMBOL) < 0):
                    new_bits = buf[idx]
                    idx += 1
                    new_bits += buf[idx] << BITS_PER_BYTE
                    idx += 1

                    #print(new_bits)
                    cur_data += new_bits << bits_left
                    bits_left += 16

                _imag = cur_data & bitmask
                imag = signbit_convert(_imag, BITS_PER_SYMBOL)

                bits_left -= BITS_PER_SYMBOL
                cur_data = cur_data >> BITS_PER_SYMBOL

                if((bits_left - BITS_PER_SYMBOL) < 0):
                    new_bits = buf[idx]
                    idx+= 1
                    new_bits_left = 8
                    if idx < len(buf):
                        new_bits += buf[idx] << BITS_PER_BYTE
                        idx += 1
                        new_bits_left += 8
                    #print(new_bits)
                    cur_data += new_bits << bits_left
                    bits_left += new_bits_left

                _real = cur_data & bitmask
                real = signbit_convert(_real, BITS_PER_SYMBOL)

                bits_left -= BITS_PER_SYMBOL
                cur_data = cur_data >> BITS_PER_SYMBOL
                csi[nr_idx, nc_idx, i] = complex(real, imag)
    return csi

@njit(cache=True)
def signbit_convert(data, maxbit):
    if(data & (1 << (maxbit -1))):
        data -= (1 << maxbit)
    return data

def calc_frequency(basefrequency, c, num_tones):
    per_side = num_tones / 2
    step = 0.3125
    if(c < per_side): #Carrier is on left side of centerfrequency
        freq = basefrequency - (per_side - c) * step
    else:
        freq = basefrequency + (c + 1 - per_side) * step
    return freq

def calc_phase_angle(iq, unwrap=0):
    imag = iq.imag
    real = iq.real
    if(unwrap==1):
        return atan2(imag,real)
    return atan2(imag, real)
