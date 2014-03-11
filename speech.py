#!/usr/bin/python

import sys
import os
import serial
import re
import time

valid_id = re.compile('\d{2}0[1-9]');

port = serial.Serial(port='/dev/tty.usbserial',
                     dsrdtr=True)



def command(cmd):
    return chr(27) + cmd + chr(13)

def send_command(cmd):
    port.write(command(cmd))
    rv = ''
    while True:
        c = port.read()
        if c == chr(13):
            break
        else:
            rv += c
    return rv

def start_form(lines):
    return "FRM=FS %d 0 48 N N N" % (lines,)

def end_form():
    return "FRM=LS"

def multi_choice(value, line, col, line_end, col_end, line_or_col,
                 field_size, numvals, answers):
    return "FRM=MC N N %d 1 %d %d %d %d %s %d %d %s" % (value,
                                                        line, col,
                                                        line_end, col_end,
                                                        line_or_col,
                                                        field_size,
                                                        numvals,
                                                        answers)

def input_field(fixedval=','):
    return "FRM=IN 1 " + fixedval

def form_id(line_or_col, linenum, charmask):
    return "FRM=ID 1 %s %s %s" % (line_or_col, linenum, charmask)

def random_input(fieldlen, *vals):
    return "FRM=RI N N %d %s" % (fieldlen, " ".join(vals))

def load_form():
    cmds = ['SRST']
    cmds.append(start_form(22))
    cmds.append(form_id('L', 22, '011'))
    cmds.append(input_field('S'))
    cmds.append(input_field())
    cmds.append(multi_choice(1, 21, 15, 12, 9, 'C', 4, 10, "0123456789"))
    cmds.append(input_field())
    cmds.append(multi_choice(1, 21, 6, 12, 2, 'C', 3, 10, "0123456789"))
    cmds.append(input_field())
    cmds.append(random_input(1, "1 13 25 1", "1 13 23 2", "1 13 21 3",
                             "1 12 25 4", "1 12 23 5", "1 12 21 6"))
    for i in range(11, 1, -1):
        cmds.append(input_field())
        cmds.append(multi_choice(2, i, 22, i, 2, 'L', 1, 11, "1009080706050403020100"))
    cmds.append(input_field())
    cmds.append(random_input(3, "1 1 22 -10", "1 1 16 -07", "1 1 8 -03",
                             "1 1 2 000"))
    cmds.append(end_form())
    for c in cmds:
        print c
        rv = send_command(c)
        if rv == chr(7):
            sys.exit(1)
        time.sleep(0.5)
    

def read_form():
    port.write(command('READ 0 Y'))
    str = ''
    while True:
        c = port.read()
        if c == chr(13):
            break
        str += c
    return str

#load_form()
f = open('scandata', 'a')
while True:
    print "Reading form..."
    data = read_form()
    print data
    if data == '!':
        print >>sys.stderr, "DONE"
        break
    fields = data.split(',')
    if '?' in data:
        print >>sys.stderr, "UNREADABLE LINE"
        sys.stdin.readline()
        continue
    if not valid_id.match(fields[1]):
        print >>sys.stderr, "BAD ID NUMBER", id
        print >>sys.stderr, "Fix and try again.  Press Enter."
        sys.stdin.readline()
        continue
    if ' ' in fields[4:-1]:
        print >>sys.stderr, "MISSING A RATING"
        print >>sys.stderr, "Fix and try again.  Press Enter."
        sys.stdin.readline()
        continue
    if fields[-1] == '   ':
        data = data.rstrip()
        print >>sys.stderr, "Adding missing time penalty"
        data += '000'
    f.write(data + "\r\n")
    
f.close()