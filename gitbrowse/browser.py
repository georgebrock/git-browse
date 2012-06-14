import curses
import os

from gitbrowse.ui import ModalTextbox, ModalScrollingInterface
from gitbrowse.git import GitFileHistory


class GitBrowser(ModalScrollingInterface):
    """
    Provides the user interface for the git browse tool.
    """

    exit_keys = ModalScrollingInterface.exit_keys + (ord('s'), )
    modes = {
        '/': 'search',
        '?': 'reverse_search',
    }

    def __init__(self, path, commit):
        super(GitBrowser, self).__init__()
        self.file_history = GitFileHistory(path, commit)
        self.search_term = None
        self.reverse_search = False

    def content(self):
        return self.file_history.blame()

    def draw_content_line(self, line, row, window, highlight):
        if highlight:
            commit_color = self.INV_YELLOW
            code_color = self.INV_GREEN if line.current else self.INV_WHITE
            search_result_color = 0
        else:
            commit_color = self.YELLOW
            code_color = self.GREEN if line.current else 0
            search_result_color = self.INV_WHITE

        window.addstr(row, 0, line.sha[:7], commit_color)
        window.addstr(row, 7, '+ ' if line.current else '  ', code_color)

        cols = curses.COLS - 9
        padded_line = line.line[:cols].rstrip().ljust(cols, ' ')
        window.addstr(row, 9, padded_line, code_color)

        if self.search_term:
            search_start = 0
            try:
                while True:
                    index = line.line.index(self.search_term, search_start)
                    search_start = index + len(self.search_term)
                    window.addstr(row, 9+index, self.search_term,
                                  search_result_color)
            except ValueError:
                pass

    def finalise(self, exit_key):
        if exit_key == ord('s'):
            current_sha = self.file_history.current_commit.sha
            os.execvp('git', ('git', 'show', current_sha))

    def handle_input(self, mode, data):
        if mode == 'search' or mode == 'reverse_search':
            self.search_term = data
            self.reverse_search = (mode == 'reverse_search')
            self.next_search_match()
            self._draw()

    def get_status(self):
        return '%s @ %s by %s: %s' % (
            self.file_history.path,
            self.file_history.current_commit.sha[:7],
            self.file_history.current_commit.author,
            self.file_history.current_commit.message,
        )

    def _move_commit(self, method_name):
        start = self.file_history.current_commit.sha

        method = getattr(self.file_history, method_name)
        if not method():
            curses.beep()
            return

        finish = self.file_history.current_commit.sha

        mapping = self.file_history.line_mapping(start, finish)
        new_highlight_line = mapping.get(self.highlight_line)
        if new_highlight_line is not None:
            self.highlight_line = new_highlight_line
        else:
            # The highlight_line setter validates the value, so it makes
            # sense to set it to the same value here to make sure that it's
            # not out of range for the newly loaded revision of the file.
            self.highlight_line = self.highlight_line

    @ModalScrollingInterface.key_bindings(']')
    def next_commit(self, times=1):
        for i in range(0,times):
            self._move_commit('next')

    @ModalScrollingInterface.key_bindings('[')
    def prev_commit(self, times=1):
        for i in range(0,times):
            self._move_commit('prev')

    def _next_search_match(self, times=1):
        if not self.search_term:
            curses.beep()
            return

        moved = False
        for n in range(0,times):
            possible_matches = self.content()[self.highlight_line + 1:]
            for i, line in enumerate(possible_matches):
                if self.search_term in line.line:
                    self.highlight_line += i + 1
                    moved = True
                    break

        if not moved:
            curses.beep()

    def _prev_search_match(self, times=1):
        if not self.search_term:
            curses.beep()
            return

        moved = False
        for n in range(0,times):
            possible_matches = self.content()[:self.highlight_line]
            for i, line in enumerate(reversed(possible_matches)):
                if self.search_term in line.line:
                    self.highlight_line -= i + 1
                    moved = True
                    break

        if not moved:
            curses.beep()

    @ModalScrollingInterface.key_bindings('n')
    def next_search_match(self, times=1):
        if self.reverse_search:
            self._prev_search_match(times)
        else:
            self._next_search_match(times)

    @ModalScrollingInterface.key_bindings('N')
    def prev_search_match(self, times=1):
        if self.reverse_search:
            self._next_search_match(times)
        else:
            self._prev_search_match(times)
