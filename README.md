# `git browse`

`git browse` is an interactive version of `git blame` written using Python and
curses. It is inspired by the TextMate Git bundle's interactive blame
interface.

## Installation

1. Clone the Git repository:

        git clone git://github.com/georgebrock/git-browse.git

2. Link to the `git-browse` file so that it's somewhere on your path. For
   example, if `~/bin` was on your path you could do this:

        ln -s /home/me/git-browse/git-browse ~/bin/git-browse

## Usage

    git browse [rev] file

* `rev` is an (optional) revision to start from. It defaults to `HEAD` (i.e.
   the revision you have currently checked out)
* `file` is the name of a file in your Git repository that you want to examine.

This will bring up a browsing interface. Navigate around the file using the
usual keys that should be familiar to anyone who uses Less, and use
<kbd>[</kbd> and <kbd>]</kbd> to move the previous or next revisions of the
file.

Exit with <kbd>q</kbd>, or exit and pass the currently selected commit to
`git show` with <kbd>s</kbd>.

Run `git browse -h` to see a full list of commands.

## Features

* The focused line is maintained when moving between revisions, even when
  lines have been added or removed before the focused line.
* Use less- and vim-style searching (<kbd>/</kbd> to search forwards,
  <kbd>?</kbd> to search backwards, <kbd>n</kbd> and <kbd>N</kbd> to jump to
  the next and previous matches).
* Jump to a line by typing the line number and pressing <kbd>return</kbd>.

## Disclaimer

This isn't extensively tested and probably contains all kinds of bugs. This
software is provided without warranty, and all that.
