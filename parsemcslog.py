#!/usr/bin/env python
#
# Reading mcs log file

import os, sys
import re

def CheckArg():
    if len(sys.argv) != 2:
        return True

def ReadMCSLog():
    """
    Open and read MCS log file
    """

    if CheckArg():
        sys.exit("you need to intput fullpath to log file as argument")

    w = "^ERROR|^FATAL|^WARNING"
    with open(sys.argv[1]) as f:
        for line in f:
            if re.search("{}".format(w), line): 
                print(line)    

def main():
    """
    start program
    """
    ReadMCSLog()

if __name__ == "__main__":
    main()