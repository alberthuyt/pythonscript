#!/usr/bin/env python
#
# Reading mcs log file

import os, sys

def ReadMCSLog():
    """
    Open and read MCS log file
    """
    with open(sys.argv[1]) as f:
        for line in f:
            print(line)    

def main():
    """
    start program
    """
    ReadMCSLog()

if __name__ == "__main__":
    main()