#!/usr/bin/python

import sys
import os
import serial
import re

valid_id = re.compile('\d{2}0[1-9] \d{2}   ');

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

def random_input(fieldlen, vals):
    return "FRM=RI N N %d %s" % (fieldlen, " ".join(vals))


def read_form():
    port.write(command('READ 0 Y'))
    str = ''
    while True:
        c = port.read()
        if c == chr(13):
            break
        str += c
    return str

f = open('scandata', 'a')
while True:
    print "Reading form..."
    data = read_form()
    if data == '!':
        print >>sys.stderr, "DONE"
        break
    if '?' in data:
        bad = [i for i, x in enumerate(data.split(','), -1) if x == '?']
        if len(bad) > 2:
            print >>sys.stderr, "Errors on lines: ", bad
            print >>sys.stderr, "Fix them and hit Enter."
            sys.stdin.readline()
            continue
        else:
            print >>sys.stderr, "Some unreadable answers ignored"
            data = data.replace('?', ' ')

    id = data.split(',')[1]
    if not valid_id.match(id):
        print >>sys.stderr, "BAD ID NUMBER OR TEST NUMBER", id
        print >>sys.stderr, "Fix and try again.  Press Enter."
        sys.stdin.readline()
        continue
    f.write(data + "\r\n")
    
f.close()
