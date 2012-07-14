import os


class GitCommit(object):
    """
    Stores simple information about a single Git commit.
    """
    def __init__(self, sha, author, message):
        self.sha = sha
        self.author = author
        self.message = message


class GitBlameLine(object):
    """
    Stores the blame output for a single line of a file.
    """
    def __init__(self, sha, line, current, original_line, final_line):
        self.sha = sha
        self.line = line
        self.current = current
        self.original_line = original_line
        self.final_line = final_line


class GitFileHistory(object):
    """
    Responsible for following the history of a single file, moving around
    within that history, and giving information about the state of the file
    at a particular revision or the differences between revisions.

    Most operations are relative to the current commit, which can be changed
    with the previous and next mthods and accessed through the current_commit
    property.
    """

    def __init__(self, path, start_commit):
        #TODO Validate path
        #TODO Validate commit

        self.path = path

        p = os.popen('git log %s --follow --pretty="%s" -- %s' % (
            start_commit,
            '%H%n%an%n%s%n',
            self.path,
        ))
        output = p.read().split('\n\n')

        self.commits = [GitCommit(*c.split('\n', 2)) for c in output if c]
        self._index = 0
        self._blame = None

        self._line_mappings = {}

    @property
    def current_commit(self):
        return self.commits[self._index]

    def next(self):
        """
        Moves to the next commit that touched this file, returning False
        if we're already at the last commit that touched the file.
        """
        if self._index <= 0:
            return False

        self._index -= 1
        self._blame = None
        return True

    def prev(self):
        """
        Moves to the previous commit that touched this file, returning False
        if we're already at the first commit that touched the file.
        """
        if self._index >= len(self.commits) - 1:
            return False

        self._index += 1
        self._blame = None
        return True

    def blame(self):
        """
        Returns blame information for this file at the current commit as
        a list of GitBlameLine objects.
        """
        if self._blame:
            return self._blame

        lines = []

        p = os.popen('git blame -p %s %s' % (
            self.path,
            self.current_commit.sha,
        ))

        while True:
            header = p.readline()
            if not header:
                break

            # Header format:
            # commit_sha original_line final_line[ lines_in_group]
            sha, original_line, final_line = header.split(' ')[:3]

            line = p.readline()

            # Skip any addition headers describing the commit
            while not line.startswith('\t'):
                line = p.readline()

            lines.append(GitBlameLine(
                sha=sha,
                line=line[1:],
                current=(sha == self.current_commit.sha),
                original_line=original_line,
                final_line=final_line,
            ))

        self._blame = lines
        return self._blame

    def line_mapping(self, start, finish):
        """
        Returns a dict that represents how lines have moved between versions
        of a file. The keys are the line numbers in the version of the file
        at start, the values are where those lines have ended up in the version
        at finish.

        For example if at start the file is two lines, and at
        finish a new line has been inserted between the two the mapping
        would be:
            {1:1, 2:3}

        Deleted lines are represented by None. For example, if at start the
        file were two lines, and the first had been deleted by finish:
            {1:None, 2:1}
        """

        key = start + '/' + finish
        if key in self._line_mappings:
            return self._line_mappings[key]

        forward, backward = self._build_line_mappings(start, finish)
        self._line_mappings[start + '/' + finish] = forward
        self._line_mappings[finish + '/' + start] = backward

        return forward

    def _build_line_mappings(self, start, finish):
        forward = {}
        backward = {}

        # Get information about blank lines: The git diff porcelain format
        # (which we use for everything else) doesn't distinguish between
        # additions and removals, so this is a very dirty hack to get around
        # the problem.
        p = os.popen('git diff %s %s -- %s | grep -E "^[+-]$"' % (
            start,
            finish,
            self.path,
        ))
        blank_lines = [l.strip() for l in p.readlines()]

        p = os.popen('git diff --word-diff=porcelain %s %s -- %s' % (
            start,
            finish,
            self.path,
        ))

        # The diff output is in sections: A header line (indicating the
        # range of lines this section covers) and then a number of
        # content lines.

        sections = []

        # Skip initial headers: They don't interest us.
        line = ''
        while not line.startswith('@@'):
            line = p.readline()

        while line:
            header_line = line
            content_lines = []

            line = p.readline()
            while line and not line.startswith('@@'):
                content_lines.append(line)
                line = p.readline()

            sections.append((header_line, content_lines, ))


        start_ln = finish_ln = 0
        for header_line, content_lines in sections:
            # The headers line has the format '@@ +a,b -c,d @@[ e]' where
            # a is the first line number shown from start and b is the
            # number of lines shown from start, and c is the first line
            # number show from finish and d is the number of lines show
            # from from finish, and e is Git's guess at the name of the
            # context (and is not always present)

            headers = header_line.strip('@ \n').split(' ')
            headers = map(lambda x: x.strip('+-').split(','), headers)

            start_range = map(int, headers[0])
            finish_range = map(int, headers[1])

            while start_ln < start_range[0] - 1 and \
                  finish_ln < finish_range[0] - 1:
                forward[start_ln] = finish_ln
                backward[finish_ln] = start_ln
                start_ln += 1
                finish_ln += 1

            # Now we're into the diff itself. Individual lines of input
            # are separated by a line containing only a '~', this helps
            # to distinguish between an addition, a removal, and a change.

            line_iter = iter(content_lines)
            try:
                while True:
                    group_size = -1
                    line_delta = 0
                    line = ' '
                    while line != '~':
                        if line.startswith('+'):
                            line_delta += 1
                        elif line.startswith('-'):
                            line_delta -= 1

                        group_size += 1
                        line = line_iter.next().rstrip()

                    if group_size == 0:
                        # Two '~' lines next to each other means a blank
                        # line has been either added or removed. Git
                        # doesn't tell us which. This is all crazy.
                        if blank_lines.pop(0) == '+':
                            line_delta += 1
                        else:
                            line_delta -= 1

                    if line_delta == 1:
                        backward[finish_ln] = None
                        finish_ln += 1
                    elif line_delta == -1:
                        forward[start_ln] = None
                        start_ln += 1
                    else:
                        forward[start_ln] = finish_ln
                        backward[finish_ln] = start_ln
                        start_ln += 1
                        finish_ln += 1
            except StopIteration:
                pass

        # Make sure the mappings stretch the the beginning and end of
        # the files.

        p = os.popen('git show %s:%s' % (start, self.path))
        start_len = len(p.readlines())

        p = os.popen('git show %s:%s' % (finish, self.path))
        finish_len = len(p.readlines())

        while start_ln <= start_len and finish_ln <= finish_len:
            forward[start_ln] = finish_ln
            backward[finish_ln] = start_ln
            start_ln += 1
            finish_ln += 1

        return forward, backward
