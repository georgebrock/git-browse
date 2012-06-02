# `git browse`

`git browse` is an interactive version of `git blame` written using Python and
curses. It is inspired by the TextMate Git bundle's interactive blame
interface.

## Installation

1. Clone the git repository:

        git clone git@github.com:georgebrock/git-browse.git

2. Link to the `git-browse` file so that it's somewhere on your path. For
   example, if `~/bin` was on your path you could do this:

        ln -s git-browse/git-browse ~/bin/git-browse

## Usage

    git browse [rev] file

* `rev` is an (optional) revision to start from. It defaults to `HEAD` (i.e.
   the revision you have currently checked out)
* `file` is the name of a file in your Git repository that you want to examine.

This will bring up a browsing interface. Navigate around the file using the
usual keys that should be familiar to anyone who uses Less (or Vim), and use
<kbd>p</kbd> and <kbd>n</kbd> to move the previous or next revisions of the
file.

Exit with <kbd>q</kbd>, or exit and pass the currently selected commit to
`git show` with <kbd>s</kbd>.

Run `git browse --help` to see a full list of commands.

## Disclaimer

This isn't extensively tested and probably contains all kinds of bugs. This
software is provided without warranty, and all that.
