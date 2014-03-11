import logging
import serial

logger = logging.getLogger('scantron')

class FormDefinition:
    def __init__(self, num_lines, num_cols=48, identifier=None):
        """
        Identifier, if present is a 3-tuple indicating the orientation
        (L or C), the line or column, and the identifier.  The identifier
        is basically a mask indicating which bits are filled in.
        for example, the identifier ('L', 22, '011') means that line 22
        is a form identifier, and on line 22, the 2nd and 3rd columns will
        be black, the 1st will be blank, and the others are undefined.
        Though internally, the software does a mask of 10 bits, with 'X'
        padding out to num_cols.  I suspect thats not quite right, and one
        doesn't actually need the padding.
        """
        self._start = 'FRM=FS %d 0 %d N N N' % (num_lines, num_cols)
        self._def = []
        if identifier is not None:
            # TODO: Pad this maybe with 0s up to position 10, then X
            self._def.append('FRM=ID 1 %s %d %s' % identifier)
        self._end = 'FRM=LS'

    def commands(self):
        return [self._start] + self._def + [self._end]
        
    def fixed_value(self, size=1, value=','):
        """
        A fixed value.  The Scantron will insert this value regardless of
        what it reads.  Typically used for separators or other metadata.
        """
        if not isinstance(value, str):
            raise TypeError("Must be a string")
        if not isinstance(size, int):
            raise TypeError("size is not int")
        if len(value) != size:
            raise ValueError("Mismatch between field size and value")
        self._def.append('FRM=IN %d %s' % (len, value))

    # Given a sheet, oriented with the guide marks on the left-hand side,
    # lines go horizontally (1 at the top, columns go vertically (1 at the left).  
    
    def multiple_choice(self, size, line_start, col_start, orientation,
                        field_size, values):
        # TODO: Is it always specified end of field to beginning?
        #       Can it be reversed?  If so, do you reverse ordering of values?
        """
        Multiple choice.  Starts at line_start, ends at line_start -
        len(values) + 1.  Starts at col_start, ends at  col_start
        """
        # How close are the columns
        # Actual resolution is 1/16" between marks, typical forms
        # "skip" a column for readability
        col_spacing = 2
        if orientation == 'C':
            line_end = line_start - len(values) + size
            col_end = col_start - (field_size * col_spacing) - col_spacing
        else:
            line_end = line_start
            col_end = col_start - len(values) + size
        tmpl = "FRM=MC N N %d 1 %d %d %d %d %s %d %d %s"
        self._defs.append(tmpl % (size, line_start, col_start,
                                  line_end, col_end, orientation,
                                  field_size, len(values) / size,
                                  values))

    def add_random_input(self, size, *values):
        # TODO: is 'size' "select at most", or size of data represented by
        #       a coord
        """
        Arbitrary input.  size is the size of the value returned,
        which is one of the values specified.
        value is a 4-tuple of (size, line, col, value)
        """
        self._def.append("FRM=RI N N %d %s" % (size, ' '.join(
                    [' '.join([str(y) for y in x]) for x in values])))
        
    

class Scantron:
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
                raise ValueError("Scantron failed to accept command")

    def _write_form(self, form_def):
        self._send_command('SRST')
        for c in form_def.commands():
            _send_command(c)

