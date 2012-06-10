import curses
from curses.textpad import Textbox
from curses import ascii

class ModalTextbox(Textbox, object):
    """
    A Textbox that emulates the modal behaviour of an application like Less
    or Vim. In default (command) mode key presses aren't echoed, except
    for digits which can be used in conjunction with commands.

    In an input mode (entered by pressing a key in command mode) keys are
    echoed until the user presses return or escape.

    All commands from command mode, and input from other modes, is passed to
    a delegate object for processing. The delegate should have the following
    methods:

        textbox_mode_changed(textbox, mode)     Called when the mode changes.

        textbox_input(textbox, mode, data)      Called when the user has
                                                finished entering data in an
                                                input mode.

        textbox_command(textbox, key, prefix)   Called when the user presses a
                                                key in command mode. The prefix
                                                is the number the user may have
                                                entered before pressing the
                                                key.
    """

    DEFAULT_MODE = '__command__'
    EDIT_KEYS = (ascii.SOH, ascii.STX, ascii.BS, ascii.EOT, ascii.ENQ,
                 ascii.ACK, ascii.BEL, ascii.NL, ascii.VT, ascii.FF,
                 ascii.SO, ascii.SI, ascii.DLE, ascii.DEL,
                 curses.KEY_BACKSPACE, curses.KEY_RIGHT, curses.KEY_LEFT)

    def __init__(self, win, delegate, insert_mode=False):
        super(ModalTextbox, self).__init__(win, insert_mode)
        self.delegate = delegate
        self.modes = {}
        self.mode = self.DEFAULT_MODE

    def add_mode(self, name, trigger):
        """
        Defines a new mode. The trigger should be either a one character
        string (e.g. '?') or a curses or ascii key code (one of the
        curses.KEY_* or curses.ascii.* constants), and defines which key
        the user must press to enter this new mode.
        """
        if name == self.DEFAULT_MODE:
            raise ValueError('That mode name is reserved')

        trigger_key = ord(trigger) if type(trigger) is str else trigger
        self.modes[trigger_key] = name

    def set_mode(self, mode):
        """
        Change the mode. The mode must be either ModalTextbox.DEFAULT_MODE or
        one of the mode name previously passed to add_mode.
        """
        if mode != self.DEFAULT_MODE and mode not in self.modes.values():
            raise ValueError('Unknown mode')

        self.clear()
        self.mode = mode
        self.delegate.textbox_mode_changed(self, mode)

    def edit(self, recurse=True):
        """
        Waits for the user to enter text, until they press a key that
        terminates the editing session (usually return or escape).

        The collected text is passed to the delegate's textbox_input method
        along with the current mode.

        If recurse is set, then the edit method will infinitely recurse. If
        you use this option then you should make sure that there is some way
        to exit your program (e.g. the delegate's textbox_input or
        textbox_command method calls sys.exit in some circumstances)
        """
        data = super(ModalTextbox, self).edit(validate=self._process_key)
        self.win.erase()
        self.mode = self.DEFAULT_MODE
        self.delegate.textbox_input(self, self.mode, data)

        if recurse:
            self.edit(recurse)

    def clear(self):
        """
        Clears the input.
        """
        while len(self.gather()) > 0:
            self.do_command(ascii.BS)

    def _transform_input_key(self, key):
        # Our superclass doesn't support backspace, so we transform
        # it into a ^h
        if key == ascii.DEL:
            return ascii.BS
        else:
            return key

    def _process_key(self, key):
        if self.mode == self.DEFAULT_MODE:
            if ord('0') <= key <= ord('9') or key in self.EDIT_KEYS:
                return self._transform_input_key(key)
            elif key in self.modes:
                self.set_mode(self.modes[key])
                return None
            else:
                prefix = int(self.gather() or 1)
                self.clear()
                self.delegate.textbox_command(self, key, prefix)
                return None
        elif key == ascii.ESC:
            self.set_mode(self.DEFAULT_MODE)
            return None
        else:
            return self._transform_input_key(key)
