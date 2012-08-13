import sys
import curses
from curses.textpad import Textbox
from curses import ascii


class KeyBindings(dict):
    """
    A dict of key bindings, that can also be used as a decorator to assign
    certain bindings to a function, e.g.

        kb = KeyBindings()

        @kb('a', 17)
        def foo():
            pass

        kb[ord('a')] == 'foo'
        kb[17] == 'foo'
    """
    def __init__(self, *args, **kwargs):
        super(KeyBindings, self).__init__(*args, **kwargs)

    def __call__(self, *keys):
        def decorator(func):
            for k in keys:
                code = ord(k) if type(k) is str else k
                self[code] = func.__name__
            return func
        return decorator


class ModalScrollingInterface(object):
    """
    An abstract superclass for curses-based Less-like interfaces that have
    a main window of content that can be scrolled, followed by a command
    line where the user can enter different commands.

    In normal (command) mode the user can enter numbers on the command line,
    and all other keys are treated as commands. Less-like navigation commands
    are provided. Define your own commands like this:

        class MyInterface(ModalScrollingInterface):
            @ModalScrollingInterface.key_bindings('a')
            def do_something(self, count):
                pass

        # If the user presses 'a', do_something(None) will be called.
        # If the user enters '123' then presses 'a', do_something(123) will be
        # called.

    You can define input modes, in which the user can enter text after pressing
    a certain trigger key, like this:

        class MyInterface(ModalScrollingInterface):
            modes = {'/': 'search'}

            def handle_input(self, mode, data):
                if mode == 'search':
                    self.do_search(data)

        # If the user presses '/', then types 'foo', then presses RETURN,
        # handle_input('search', 'foo') will be called.
        # If the user presses '/', then types 'foo', then presses ESCAPE,
        # the input will be ignored.
    """

    key_bindings = KeyBindings()
    exit_keys = (ord('q'), ord('Q'))

    def __init__(self):
        self.scroll_line = 0
        self._highlight_line = 0

    @property
    def highlight_line(self):
        """
        The highlight line is the index of the selected line in the content.
        """
        return self._highlight_line

    @highlight_line.setter
    def highlight_line(self, value):
        # Ensure highlighted line in sane
        max_highlight = len(self.file_history.blame()) - 1
        if value < 0:
            value = 0
        elif value > max_highlight:
            value = max_highlight

        delta = value - self._highlight_line
        self._highlight_line = value

        # Ensure highlighted line is visible
        if value > self.scroll_line + curses.LINES - 3:
            max_scroll_line = self._max_scroll_line()
            self.scroll_line = min(self.scroll_line + delta, max_scroll_line)
        elif self.highlight_line < self.scroll_line:
            self.scroll_line = self.highlight_line

    def textbox_command(self, textbox, c, prefix):
        if c in self.get_exit_keys():
            self._teardown_curses()
            self.finalise(c)
            sys.exit(0)
        elif c in self.key_bindings:
            method = getattr(self, self.key_bindings[c])
            method(prefix)
            self._draw()
        else:
            curses.beep()

    def textbox_mode_changed(self, textbox, mode):
        self._draw()

    def textbox_input(self, textbox, mode, data):
        if mode == textbox.DEFAULT_MODE:
            if not data:
                self.down()
            else:
                line = int(data) - 1
                max_highlight = self.content_length() - 1

                if line < 0:
                    line = 0
                elif line > max_highlight:
                    line = max_highlight

                self.highlight_line = line
        else:
            self.handle_input(mode, data)

        self._draw()

    def run(self):
        """
        Starts the curses interface. This method won't return. The app will
        run in a loop until the user presses one of the exit_keys. If you
        want to do something else, override the finalise method.
        """

        self._setup_curses()
        self._draw()

        try:
            self.command_input.edit(recurse=True)
        except KeyboardInterrupt:
            self._teardown_curses()
            return
        except:
            self._teardown_curses()
            raise

    def _setup_curses(self):
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(1)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        self.GREEN = curses.color_pair(1)
        self.YELLOW = curses.color_pair(2)
        self.INV_WHITE = curses.color_pair(3)
        self.INV_GREEN = curses.color_pair(4)
        self.INV_YELLOW = curses.color_pair(5)

        w = curses.COLS
        h = curses.LINES

        self.content_win = self.screen.subwin(h-1, w, 0, 0)
        self.status_win  = self.screen.subwin(1, w,   h-2, 0)
        self.mode_win    = self.screen.subwin(1, 2,   h-1, 0)
        self.command_win = self.screen.subwin(1, w-1, h-1, 1)

        self.command_input = ModalTextbox(self.command_win, delegate=self)
        for trigger, name in self.get_modes().items():
            self.command_input.add_mode(name, trigger)

    def _teardown_curses(self):
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()

    def _draw(self):
        self.content_win.clear()
        start = self.scroll_line
        stop = self.scroll_line + curses.LINES - 2
        for row, line in enumerate(self.content()[start:stop]):
            highlight = (row + start == self.highlight_line)
            self.draw_content_line(line, row, self.content_win, highlight)

        self.status_win.clear()
        self.status_win.addstr(0, 0, self.get_status()[:curses.COLS-1])

        mode_char = ':'
        for trigger, name in self.get_modes().items():
            if name == self.command_input.mode:
                mode_char = trigger
        self.mode_win.addstr(0, 0, mode_char)

        self.content_win.noutrefresh()
        self.status_win.noutrefresh()
        self.mode_win.noutrefresh()
        self.command_win.noutrefresh()
        curses.doupdate()

    def content(self):
        """
        Override this method to provide content. It should return a list of
        lines.
        """
        return []

    def content_length(self):
        """
        The length (number of lines) of the content.
        """
        return len(self.content())

    def draw_content_line(self, line, row, window, highlight):
        """
        Draws the given line of content, at the given row on the given window.
        Override this if you want to do complex custom drawing, or if you're
        content method doesn't return a simple list of strings.
        """
        color = self.INV_WHITE if highlight else 0
        window.addstr(row, 0, line, color)

    def get_exit_keys(self):
        """
        Returns a tuple of key codes that should cause the interface to
        exit. The default implementation is to return self.exit_keys. If
        your subclass needs a simple, static list of keys you should just
        set the exit_keys attribute on your class. Otherwise, override this
        method.
        """
        return self.exit_keys

    def get_modes(self):
        """
        Returns a dict of trigger keys and mode names (e.g. {'/': 'search'}).
        The default implementation is to return self.modes. If your subclass
        needs a static dict of modes you should just set the modes attribute
        on your class. Otherwise, override this method.
        """
        try:
            return self.modes
        except AttributeError:
            return {}

    def finalise(self, exit_key):
        """
        Called when the user presses one of the exit keys and the curses
        interface has been shut down, just before the app exits. If you want
        some special behaviour when the user exits you should override this
        method.
        """
        pass

    def handle_input(self, mode, data):
        """
        Handles input given by the user in a particular mode. You should
        override this method and define behaviour for each of the modes you
        have definied.
        """
        pass

    def get_status(self):
        """
        Returns the status line shown at the bottom of the window, above the
        command line ane below the content.
        """
        return None

    @key_bindings('j', 'e', curses.KEY_DOWN)
    def down(self, lines=1):
        max_highlight = self.content_length() - 1
        if self.highlight_line >= max_highlight:
            curses.beep()
            return

        self.highlight_line += lines

    @key_bindings('d')
    def half_page_down(self, times=1):
        half_page = (curses.LINES - 2) / 2
        self.down(half_page * times)

    @key_bindings('f', ' ', 'z', curses.KEY_NPAGE)
    def page_down(self, times=1):
        page = curses.LINES - 2
        self.down(page * times)

    @key_bindings('k', 'y', curses.KEY_UP)
    def up(self, lines=1):
        if self.highlight_line <= 0:
            curses.beep()
            return

        self.highlight_line -= lines

    @key_bindings('u')
    def half_page_up(self, times=1):
        half_page = (curses.LINES - 2) / 2
        self.up(half_page * times)

    @key_bindings('b', 'w', curses.KEY_PPAGE)
    def page_up(self, times=1):
        page = curses.LINES - 2
        self.up(page * times)

    @key_bindings('g', '<', curses.KEY_HOME)
    def home(self, times=None):
        self.scroll_line = 0
        self.highlight_line = 0

    @key_bindings('G', '>', curses.KEY_END)
    def end(self, times=None):
        self.scroll_line = self._max_scroll_line()
        self.highlight_line = self.content_length() - 1

    def _max_scroll_line(self):
        return self.content_length() - curses.LINES + 2


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
        data_mode = self.mode

        self.win.erase()
        self.mode = self.DEFAULT_MODE
        self.delegate.textbox_input(self, data_mode, data.strip())

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
