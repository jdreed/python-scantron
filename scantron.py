"""
Python module for communicating with Scantron devices
"""
import logging
import serial

logger = logging.getLogger('scantron')

class ScantronError(Exception):
    pass

class EndOfBatchException(Exception):
    pass

class FormDefinition:
    """
    A scantron form definition.

    NOTE: Given a form, oriented such that the guide marks are on the
    left side, lines are horizontal, counted down from 1 at the top.
    Columns are vertical (Y-axis), counted from 1 at the left.  (The
    guide marks are "column 0.").  Guide marks indicate the number of
    lines, including any that are form identifiers.
    """
    def __init__(self, num_lines, num_cols=48, identifier=None):
        """
        Initialize a form with the number of lines and columns
        Typically, the number of columns is 48 for a US Letter sized
        form.
        """
        self._num_cols = num_cols
        # TODO: What is the 0?  What do the various 'N's signify?
        self.commands = ['FRM=FS %d 0 %d N N N' % (num_lines, num_cols),
                         'FRM=LS']

    def add_identifer(orientation, position, mask):
        """
        Add a form identifier.
        orientation - one of 'L' or 'C'
        position - the line or column number
        mask - a representation of the identifier line, in binary
               with '1' indicating a mark and 0 indicating no mark

        Example: the identifier ('L', '22', '011') means that on line
        22, there is a form identifier, where the first column is empty,
        the 2nd and 3rd columns have a mark in them.

        If a form lacking this identifier is read, the scanner will
        reject the form (if equipped with a reject bin).
        """
        if not FormDefinition._check_orientation(orientation):
            raise ValueError("Invalid orientation value: " . orientation)
        # Possibly unneeded, but other software does this.
        mask = mask.ljust(10, '0').ljust(self._num_cols, 'X')
        identifier = 'FRM=ID 1 %s %d %s' % (orientation,
                                            position,
                                            mask)
        # Typically the form identifier is sent after the definition,
        # TODO: Can it be anywhere in the definition?
        self.commands.insert(1, identifier)

    def add_fixed_value(self, size=1, value=','):
        """
        A fixed value.  The Scantron will insert this value in its output
        regardless of what it reads from the form.  Typically used for
        field separators when parsing the data.
        """
        if not isinstance(value, str):
            raise TypeError("Fixed value must be a string")
        if not isinstance(size, int):
            raise TypeError("Size of fixed value must be an int")
        if len(value) != size:
            raise ValueError("Mismatch between field size and value")
        self.commands.insert(-1, 'FRM=IN %d %s' % (len, value))

    def multiple_choice(self, size, line_start, col_start, orientation,
                        field_size, values, col_spacing=2):
        # TODO: Is it always specified end of field to beginning?
        #       Can it be reversed?  If so, do you reverse ordering of values?
        """
        Add a multiple choice field.
        size - the size of the data returned in each row or column
               (e.g. 1 = 1 character)
        line_start - The line at which the multiple choice question starts
        col_start - The column where the multiple choice question starts.
        orientation - 'L' or 'C' (are the different possible values on the
                      form in a column, or all on the same line)
        field_size - how many lines or columns the field is composed of
                     i.e. how many values to concatenate into the field
        values - a string or iterable containing the values
        col_spacing - how close are the columns.  The actual resoution
                      is about 1/16" between marks.  Typically forms
                      "skip" a column to avoid bleedover or stray marks.
        """
        if not FormDefinition._check_orientation(orientation):
            raise ValueError("Invalid orientation value: " . orientation)
        if orientation == 'C':
            line_end = line_start - len(values) + size
            col_end = col_start - (field_size * col_spacing) + col_spacing
        else:
            line_end = line_start - field_size + line_start
            col_end = col_start - len(values) + size
        tmpl = "FRM=MC N N %d 1 %d %d %d %d %s %d %d %s"
        self.commands.insert(-1, tmpl % (size, line_start, col_start,
                                         line_end, col_end, orientation,
                                         field_size, len(values) / size,
                                         str(values)))

    def add_random_input(self, size, *values):
        """
        Arbitrary input.
        size - size of value returned
        values - an iterable of one or more 4-tuples of
                 (size, line, col, value), where "size"
                 is the number of characters, and "value"
                 is the value to return if the point at line,col
                 is filled in.
        """
        # TODO: is 'size' "select at most", or size of data represented by
        #       a coord
        self.commands.insert(-1, "FRM=RI N N %d %s" % (size, ' '.join(
                    [' '.join([str(y) for y in x]) for x in values])))

    @staticmethod
    def _check_orientation(orientation):
        return orientation in ('L', 'C')


class Scantron:
    END_OF_BATCH = '!'

    def __init__(self, device, **kwargs):
        if 'dsrdtr' not in kwargs:
            kwargs['dsrdtr'] = True
        self.port = serial.Serial(port=device, **kwargs)

    def _send_command(self, command):
        self.port.write('%s%s%s' % (chr(27),
                                    command,
                                    chr(13)))
        rv = ''
        while True:
            c = port.read()
            if c == chr(13):
                break
            else:
                rv += c
        if len(rv):
            # BEL
            if rv == chr(7):
                raise ScantronError("Scantron failed to accept command")

    def _reset(self):
        """
        Reset the scanner, in preparation for a new form
        definition.
        """
        self._send_command('SRST')

    def set_threshold(darkness, contrast):
        """
        Set the threshold values for the scanner.
        darkness - how dark something must be to register as a mark
                   a higher value requires darker marks
        contrast - the difference between marks and non-marks or erasures
                   a higher value requires greater contrast
        Both values must be between 0 and 99, inclusive
        """
        if darkness not in range(0, 100):
            raise ValueError('darkness value must be 0-99')
        if contrast not in range(0, 100):
            raise ValueError('contrast value must be 0-99')
        self._send_command('THR=%d %d' % (darkness, contrast))

    def write_form_definition(self, form_def):
        """
        Send a FormDefinition to the scanner.
        """
        if not isinstance(form_def, FormDefinition):
            raise ValueError("Must pass a FormDefinition instance")
        self._reset()
        for c in form_def.commands:
            self._send_command(c)

    def read_form(self):
        """
        Read a single form.
        """
        return self._send_command('READ 0 Y')
