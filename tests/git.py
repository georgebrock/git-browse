from unittest import TestCase
from gitbrowse.git import GitFileHistory

class GitTestCase(TestCase):
    def setUp(self):
        self.file_history = GitFileHistory('example.txt', 'HEAD')

    def test_commits(self):
        self.assertEquals(
            [c.message for c in self.file_history.commits],
            ['Fifth commit', 'Fourth commit', 'Third commit', 'Second commit',
             'First commit'],
            'Commit messages should be correct and ordered',
        )

    def test_navigation(self):
        commits = self.file_history.commits

        self.assertEquals(self.file_history.current_commit, commits[0])
        self.file_history.prev()
        self.assertEquals(self.file_history.current_commit, commits[1])
        self.file_history.prev()
        self.assertEquals(self.file_history.current_commit, commits[2])
        self.file_history.next()
        self.assertEquals(self.file_history.current_commit, commits[1])

    def test_navigation_beyond_end(self):
        commits = self.file_history.commits

        self.assertEquals(self.file_history.current_commit, commits[0])
        self.file_history.next()
        self.assertEquals(self.file_history.current_commit, commits[0])

    def test_navigation_before_start(self):
        commits = self.file_history.commits

        for _ in range(4):
            self.file_history.prev()

        self.assertEquals(self.file_history.current_commit, commits[4])
        self.file_history.prev()
        self.assertEquals(self.file_history.current_commit, commits[4])

    def test_blame(self):
        commits = self.file_history.commits
        for _ in range(5):
            self.file_history.prev()

        def check_blame(lines, expected_commits):
            blame = self.file_history.blame()
            for blame_line, expected_line, expected_commit in \
                zip(blame, lines, expected_commits):
                self.assertEquals(blame_line.line, expected_line)
                self.assertEquals(blame_line.sha, commits[expected_commit].sha)

        check_blame(
            ['first\n', 'second\n', 'third\n', 'fourth\n', 'fifth\n'],
            [4, 4, 4, 4, 4],
        )

        self.file_history.next()
        check_blame(
            ['first\n', 'fourth\n', 'fifth\n'],
            [4, 4, 4],
        )

        self.file_history.next()
        check_blame(
            ['another\n', 'yet another\n', 'first\n', 'fourth\n', 'fifth\n'],
            [2, 2, 4, 4, 4],
        )

        self.file_history.next()
        check_blame(
            ['another\n', '\n', 'yet another\n', 'first\n', 'fourth\n', '\n',
             'fifth\n'],
            [2, 1, 2, 4, 4, 1, 4],
        )

        self.file_history.next()
        check_blame(
            ['another\n', '\n', 'yet another\n', 'first\n', 'fourth\n',
             'fifth\n'],
            [2, 1, 2, 4, 4, 4],
        )

    def test_forward_line_mappings(self):
        commits = self.file_history.commits

        self.assertEquals(
            {0:0, 1:None, 2:None, 3:1, 4:2, 5:3},
            self.file_history.line_mapping(commits[4].sha, commits[3].sha),
        )

        self.assertEquals(
            {0:2, 1:3, 2:4, 3:5},
            self.file_history.line_mapping(commits[3].sha, commits[2].sha),
        )

        self.assertEquals(
            {0:0, 1:2, 2:3, 3:4, 4:6, 5:7},
            self.file_history.line_mapping(commits[2].sha, commits[1].sha),
        )

        self.assertEquals(
            {0:0, 1:1, 2:2, 3:3, 4:4, 5:None, 6:5, 7:6},
            self.file_history.line_mapping(commits[1].sha, commits[0].sha),
        )

    def test_reverse_line_mappings(self):
        commits = self.file_history.commits

        self.assertEquals(
            {0:0, 1:1, 2:2, 3:3, 4:4, 5:6, 6:7},
            self.file_history.line_mapping(commits[0].sha, commits[1].sha),
        )

        self.assertEquals(
            {0:0, 1:None, 2:1, 3:2, 4:3, 5:None, 6:4, 7:5},
            self.file_history.line_mapping(commits[1].sha, commits[2].sha),
        )

        self.assertEquals(
            {0:None, 1:None, 2:0, 3:1, 4:2, 5:3},
            self.file_history.line_mapping(commits[2].sha, commits[3].sha),
        )

        self.assertEquals(
            {0:0, 1:3, 2:4, 3:5},
            self.file_history.line_mapping(commits[3].sha, commits[4].sha),
        )
