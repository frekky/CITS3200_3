#!/bin/bash

cd "$(dirname $0)"
source ./pyenv/bin/activate

DEST_DIR=dist

echo "Generating output in $(pwd)/$DEST_DIR/"
rm -rf $DEST_DIR
mkdir -p $DEST_DIR/src

./manage.py collectstatic --noinput

# Copy files to dist dir
rsync -ru --del --exclude '__pycache__/' --exclude '*.pyc' --exclude "app/settings*.py" --exclude '*.sqlite3' \
 app database static manage.py LICENSE README.md requirements.txt "$DEST_DIR/src"

rsync -ru --del --exclude '__pycache__/' --exclude '*.pyc' --exclude "app/settings*.py" --exclude '*.sqlite3' \
 staticfiles LICENSE README.md requirements.txt "$DEST_DIR"