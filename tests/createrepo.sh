#!/bin/bash

cd $( dirname $BASH_SOURCE[0] )

mkdir repo
cd repo
git init > /dev/null

cat > example.txt << EOF
first
second
third
fourth
fifth
EOF

git add example.txt
git commit -m 'First commit' > /dev/null

cat > example.txt << EOF
first
fourth
fifth
EOF

git commit -am 'Second commit' > /dev/null

cat > example.txt << EOF
another
yet another
first
fourth
fifth
EOF

git commit -am 'Third commit' > /dev/null

cat > example.txt << EOF
another

yet another
first
fourth

fifth
EOF

git commit -am 'Fourth commit' > /dev/null

cat > example.txt << EOF
another

yet another
first
fourth
fifth
EOF

git commit -am 'Fifth commit' > /dev/null
