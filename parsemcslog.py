#!/usr/bin/env python
#
# Reading mcs log file

import os, sys
import re
import argparse

def CheckArg():
    # if len(sys.argv) != 2:
    #     return True

    parser = argparse.ArgumentParser(description='Process args')
    parser.add_argument('-f', '--file', required=True, action='store', help='parse log file')   
    args = parser.parse_args() 
    return args

def ReadMCSLog():
    """
    Open and read MCS log file
    """
    CheckArg()

    # if CheckArg():
    #     sys.exit("you need to intput fullpath to log file as argument")

    w = "^ERROR|^FATAL|^WARNING"
    with open(sys.argv[1]) as f:
        for line in f:
            if re.search("{}".format(w), line): 
                print(line)    

def main():
    """
    start program
    """
    args = CheckArg()
    ReadMCSLog()

if __name__ == "__main__":
    main()