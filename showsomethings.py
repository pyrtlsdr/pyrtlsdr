#   Temporary test just for travis-ci to print environment things to stdout
#   Delete me when done

import sys, os

print('\n'.join(['sys.path:', str(sys.path), '']))

print('cwd: ', os.getcwd())

print('ls(cwd): ', os.listdir(os.getcwd()))
