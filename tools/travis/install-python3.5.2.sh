#!/bin/bash

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
pyenv install 3.5.2
pyenv rehash
pyenv shell 3.5.2
pyenv versions
VIRTUALENV_PATH=`which virtualenv`
~/.pyenv/versions/3.5.2/bin/python $VIRTUALENV_PATH virtualenv352
source virtualenv352/bin/activate
python --version
