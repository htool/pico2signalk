#!/usr/bin/env python3
#
# This code and reverse engineering by Erik Bosman / @brainsmoke
#
# Many thanks to him for an afternoon of high quality reverse engineering
# 

import sys

def calc_rev_crc16(s, poly=0x1189, start=0x0000):
    crc = start
    for c in s:
        for i in range(8):
            c_msb   = (c   >>  7)&1
            crc_msb = (crc >> 15)&1

            c       = (c   <<  1)&0xff
            crc     = (crc <<  1)&0xffff

            if c_msb ^ crc_msb:
                crc ^= poly
    return crc

def calc_rev_crc16_table(s, table, start=0x0000):
    crc = start
    for c in s:
        crc = ((crc << 8)&0xffff) ^ table[c ^ (crc >> 8)]

    return crc

def calc_table(poly):
    return tuple( calc_rev_crc16([i], poly) for i in range(256))

if False:
    table = calc_table(0x1189)

    print ( calc_rev_crc16(b"123456789abcdef", 0x1189) )
    print ( calc_rev_crc16_table(b"123456789abcdef", table) )

