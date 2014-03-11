#!/usr/bin/python

import sys
import os
import serial
import re

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
    cmds.append(start_form(21))
    cmds.append(form_id('L', 21, '01'))
    cmds.append(input_field('I'))
    cmds.append(input_field())
    cmds.append(multi_choice(1, 20, 15, 11, 9, 'C', 4, 10, "0123456789"))
    cmds.append(input_field())
    cmds.append(multi_choice(1, 20, 6, 11, 2, 'C', 3, 10, "0123456789"))
    cmds.append(input_field())
    cmds.append(random_input(1, "1 12 25 1", "1 12 23 2", "1 12 21 3",
                             "1 11 25 4", "1 11 23 5", "1 11 21 6"))
    for i in range(10, 0, -1):
        cmds.append(input_field())
        cmds.append(multi_choice(2, i, 22, i, 2, 'L', 1, 11, "1009080706050403020100"))
    cmds.append(end_form())

    for c in cmds:
        print c
        rv= send_command(c)
        if rv == chr(7):
            sys.exit(1)

def read_form():
    port.write(command('READ 0 Y'))
    str = ''
    while True:
        c = port.read()
        if c == chr(13):
            break
        str += c
    return str

print "Load form? "
ans = sys.stdin.readline()
if 'y' in ans:
    load_form()

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
        bad = [i for i, x in enumerate(data.split(','), -2) if x == '??']
        print >>sys.stderr, "Error on line(s)", bad
        print >>sys.stderr, "Fix and press Enter"
        sys.stdin.readline()
        continue
    if not valid_id.match(fields[1]):
        print >>sys.stderr, "BAD ID NUMBER", fields[1]
        print >>sys.stderr, "Fix and try again.  Press Enter."
        sys.stdin.readline()
        continue
    if '  ' in fields[4:-1]:
        print >>sys.stderr, "MISSING A RATING"
        print >>sys.stderr, "Fix and try again.  Press Enter."
        sys.stdin.readline()
        continue
    f.write(data + "\r\n")
    
f.close()
