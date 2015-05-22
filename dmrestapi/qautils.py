'''
$Id: //BRS/user_branches/nguyek4/jpython/testdpma/dpmaapi/qautils.py#1 $
'''

from __future__ import with_statement
from Queue import Queue, Empty
from contextlib import closing
from decimal import *
from httplib import HTTPConnection, OK
# from pylts.dpn import subproc
from random import *
from stat import *
from subprocess import Popen, PIPE, STDOUT
from urllib2 import quote
import cStringIO
import hashlib
import imp
import os
import sys
import string
import re
import glob
import threading
import copy
import time
import socket
import os.path
import socket
import time
import getpass
import math
import fnmatch
import stat
import codecs


try:
    bool = True
except:
    True = 1
    False = 0
    
if sys.platform == "win32":
    ''' 
    These imports require either pywin32 to be installed:
    http://sourceforge.net/projects/pywin32/
    
    or to install ActivePython which includes pywin32 as part of its installation:
    http://www.activestate.com/activepython
    '''
#    import win32api 
#    import win32net  
    import win32file 


options = {}
options_help = {}

# use these ssh/scp commands throughout - due to host keys constantly changing in the lab
ssh_key = "~/.ssh/dpnid"
ssh_opts = "-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
ssh_cmd = "/usr/bin/ssh -x %s -i %s" % (ssh_opts, ssh_key)
scp_cmd = "/usr/bin/scp -p %s -i %s" % (ssh_opts, ssh_key)

def system_expecting(cmd, expectedcode, verbose=False):
    f = os.popen(cmd)
    data = f.read()
    code = f.close()
    if code != None and code != expectedcode:
        raise "runexpecting for '%s' got return code %d" % (cmd, code)
    return data

class LocationPair:
    def __init__(self, srcpath, destpath):
        pattern = '/'
        if os.name == "nt":
            pattern = r'[a-zA-Z]:\\'
            
        if not re.match(pattern, srcpath): srcpath = os.path.join(os.getcwd(), srcpath)
        if not re.match(pattern, destpath): destpath = os.path.join(os.getcwd(), destpath)
            
        self.srcstem = srcpath
        self.deststem = destpath
        self.extralevels = []        

        pattern = ".*" + os.sep + "$"
        if not re.match(pattern, srcpath): self.srcstem = self.srcstem + "/"
        if not re.match(pattern, destpath): self.deststem = self.deststem + "/"


    def cdsrc(self):
        os.chdir(self.srcstem)
        for d in self.extralevels:
            os.chdir(d)

    def cddest(self):
        os.chdir(self.deststem)
        for d in self.extralevels:
            os.chdir(d)

    def srcpath(self):
        result = string.join(self.extralevels, os.sep)
        result = self.srcstem + result # stems already have trailing slash
        return result

    def destpath(self):
        result = string.join(self.extralevels, os.sep)
        result = self.deststem + result # stems already have trailing slash
        return result

    def descend(self, subdir):
        self.cdsrc()
        if not os.path.isdir(subdir):
            pass # throw exception
        self.cddest()
        if not os.path.isdir(subdir):
            pass # throw exception
        self.extralevels.append(subdir)

    def ascend(self):
        self.extralevels.pop()

    def createdestloc(self, dirname, statresult):
        self.cdsrc()
        if not os.path.isdir(dirname):
            pass # throw exception
        self.cddest()
        os.mkdir(dirname, statresult.st_mode)
        # chmod, etc so statresult stuff is right
        result = copy.deepcopy(self)
        result.descend(dirname)
        return result
        
    def copyfile2dest(self, fname, force=False):
        self.cdsrc()
        if not force:
            sr = os.lstat(fname)
            if sr.st_nlink > 1:
                return (sr.st_nlink, sr.st_ino.__repr__())
        tmpname = "tmp." + random_string(8)
        cmd = "cp -d --preserve=all %s %s%s" % (fname, self.deststem, tmpname)
        # print "running '%s'" % cmd
        os.system(cmd)
        os.chdir(self.deststem)
        for d in self.extralevels:
            cmd = "mv %s %s/" % (tmpname, d)
            # print "running '%s'" % cmd
            os.system(cmd)
            os.chdir(d)
        cmd = "mv %s %s 2>/dev/null" % (tmpname, fname)
        # print "running '%s'" % cmd
        result = os.system(cmd)
        if result != 0:
            print "%s: Returned %d" % (cmd, result)

        return (1, 0)

    def filesequal(self, n1, n2):
        self.cdsrc()
        n1md5 = hashlib.md5()
        n1f = open(n1, "rb")
        line = n1f.read(4096)
        while len(line):
            n1md5.update(line)
            line = n1f.read(4096)
    
        self.cddest()
        n2md5 = hashlib.md5()
        n2f = open(n2, "rb")
        line = n2f.read(4096)
        while len(line):
            n2md5.update(line)
            line = n2f.read(4096)

        #print "filesequal: calculated two md5 sums: %s, %s" % (n1md5.hexdigest(), n2md5.hexdigest())
        return n1md5.hexdigest() == n2md5.hexdigest()

# END LocationPair

def http_post_php(data, php_script, webserver="", full_url=0):
    output = ""
   
    # Use just hostname rather than FQDN to work in both IPv4/IPv6
    # This will still need to be a config parameter soon
    if not webserver:
        webserver = get_qa_url(short_hostname=True)
    if type(data) == type(u''):
        data = data.encode('iso-8859-1')
    
    # try to get addrinfo first
    a_list = socket.getaddrinfo(webserver, 80, 0, socket.SOCK_STREAM)

    sock = None
    # now try to connect by looping through list of addresses
    for a_family, s_type, proto, cname, s_address in a_list:
        try:
            # create socket for family/proto
            sock = socket.socket(a_family, s_type, proto)
            # now connect to webserver
            sock.connect(s_address)
        except Exception, e:
            print "Exception in socket :", e
            # if exception close socket
            if sock:
                sock.close()
            print "ERROR: Could not connect to webserver: " + webserver
            return
        else:
            #print "INFO: Connected to webserver: " + webserver, s_address
            break

    if not full_url:
        qaurl = "http://%s/server_test/%s" % (webserver, php_script)
    else:
        qaurl = "http://%s/%s" (webserver, php_script)
        
    sock.send("POST %s HTTP/1.0\n" % qaurl)
    sock.send("Accept: */*\n")
    sock.send("User-Agent: qalts\n")
    sock.send("Content-Type: application/x-www-form-urlencoded\n")
    sock.send("Content-length: %d\n\n" % len(data))
    sock.send(data)
    
    while 1:
        response = sock.recv(8192)
        if not response: break
        output = response
    
    sock.close() 
    return output

#def http_post_php(data,php_script,webserver="",full_url=False):
    # Use just hostname rather than FQDN to work in both IPv4/IPv6
    # This will still need to be a config parameter soon
   # if not webserver:
      #  webserver = get_qa_url(short_hostname=True)
    #if type(data) == type(u''):
    #    data = data.encode('iso-8859-1')
    #headers = {"Accept": "*/*",
               #"User-Agent": "qalts",
               #"Content-Type": "application/x-www-form-urlencoded",
#               "Content-length": str(len(data)), # Not needed, auto calculated in conn.request
              # }
    #path = "/" if full_url else "/server_test/"
   # path += php_script
    
    #with closing(HTTPConnection(webserver,80)) as conn:
        #conn.request("POST", path, quote(data), headers)
        #response = conn.getresponse()
       # if response.status != OK: # HTTP STATUS OK = 200
           # msg = "ERROR: Could not POST to webserver: %d %s"
            #msg %= (response.status, response.reason)
            #raise Exception(msg)
        #return response.read()

def http_post(data, cgi_cmd, webserver="", full_url=0):
    # Use just hostname rather than FQDN to work in both IPv4/IPv6
    # This will still need to be a config parameter soon
    if not webserver:  
        webserver = "qahome"
    if type(data) == type(u''):
        data = data.encode('iso-8859-1')
    
    # try to get addrinfo first
    a_list = socket.getaddrinfo(webserver, 80, 0, socket.SOCK_STREAM)

    sock = None
    # now try to connect by looping through list of addresses
    for a_family, s_type, proto, cname, s_address in a_list:
        try:
            # create socket for family/proto
            sock = socket.socket(a_family, s_type, proto)
            # now connect to webserver
            sock.connect(s_address)
        except Exception, e:
            print "Exception in socket :", e
            # if exception close socket
            if sock:
                sock.close()
            print "ERROR: Could not connect to webserver: " + webserver
            return
        else:
            print "INFO: Connected to webserver: " + webserver, s_address
            break

    if not full_url:
        qaurl = "http://%s/cgi-bin/%s" % (webserver, cgi_cmd)
    else:
        qaurl = "http://%s/%s" % (webserver, cgi_cmd)
        
    sock.send("POST %s HTTP/1.0\n" % qaurl)
    sock.send("Accept: */*\n")
    sock.send("User-Agent: qalts\n")
    sock.send("Content-Type: application/x-www-form-urlencoded\n")
    sock.send("Content-Length: %d\n\n" % len(data))
    sock.send(data)
    while 1:
        response = sock.recv(8192)
        if not response: break
        output = response
    sock.close()
    # print "+=" * 40
    # print "qautils::http_post to '%s' returned CGI output:\n" % qaurl + output
    # print "+=" * 40
    # We want to return the number from the last line of the output
    output_list = re.split(r'Content-.*\n', output)
    result_id = output_list.pop()
    return result_id

#
#
# To be safe in terms of deadlock avoidance, use threads to read our test script output
#
#class readerthread(threading.Thread):
#    def __init__(self, file):
#        self.file = file
#        threading.Thread.__init__(self)
#    def run(self):
#        self.lines = self.file.readlines()
#        self.file.close()
#    def contents(self):
#        return string.join(self.lines, '')
#
#
# Don't combine stdout and stderr since some tests (like restore to stdout) may
# rely on treading them separately.
# input is a dictionary with stdout lines as the key and the value being the input to be used (ie 'y', 'n', '1', '4')
#def run(command, input={}):
#    if input == {}:
#        if type(command) == type(u''): # unicode
#            command = command.encode('iso-8859-1')
#        #r, w, e = popen2.popen3(command);
#        run_command = Popen(command, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE, close_fds=True)
#        r, w, e = run_command.stdout, run_command.stdin, run_command.stderr
#        threads = []
#        for file in (r, e):
#            thread = readerthread(file)
#            thread.start()
#            threads.append(thread)
#        output = ""
#        for thread in threads:
#            thread.join()
#            output = output + thread.contents()                
#        return output
#    
#    else:
#        if type(command) == type(u''): # unicode
#            command = command.encode('iso-8859-1')
#        #r, w, e = popen2.popen3(command);
#        run_command = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE, close_fds=True)
#        r, w, e = run_command.stdout, run_command.stdin, run_command.stderr
#        threads = []
#        for file in (r, e):
#            thread = readerthread(file)
#            thread.start()
#            threads.append(thread)
#        output = ""
#        for thread in threads:
#            thread.join()
#            output = output + thread.contents()
#            
#        # check the output lines for indications of input required
#        lines = output.split("\n")
#        for line in lines:
#            if input.has_key(line.rstrip()):
#                w.write(input[line.rstrip()])
#                
#        #w.close()
#        #r.close()
#        #e.close()
#        return output
#    
#    """else:
#        if type(command) == type(u''): # unicode
#            command = command.encode('iso-8859-1')
#        #p = subproc.Subprocess(command, 1)    #1 for opening stderr pipe
#        r, w, e = popen2.popen3(command);
#        #lines = []
#        output = ""
#        for line in r:
#            print "DEBUG: " + line
#            output += line
#            if input.has_key(line.rstrip()):    # if any of these lines are indicative of a prompt
#                w.write(input[line.rstrip()])
#                print "DEBUG WRITE: " + input[line.rstrip()]
#        return output
#       """ 

class NonBlockingFile(threading.Thread):
    '''
        Requires that the file object is opened with the option to be 
        linebuffered with bufsize=1 in either Popen(...) or open(...)
    '''
    def __init__(self, file_obj):
        threading.Thread.__init__(self)
        self.daemon = True
        self.file = file_obj
        self._q = Queue()
        self.start()
    def run(self):
        for line in iter(self.file.readline, ''):
            self._q.put(line)
        self.file.close()
    def __iter__(self):
        return self
    def is_empty(self):
        return self._q.empty()
    def next(self): #@ReservedAssignment
        try:
            return self._q.get_nowait()
        except Empty:
            raise StopIteration

def read_and_write(read, write, output, input_values=None):
    lines = list(read)
    if isinstance(input_values, dict):
        for line in lines:
            if input_values.has_key(line.rstrip()):
                write.write(input_values[line.rstrip()])
                write.flush()
    elif isinstance(input_values, list):
        for line in lines:
            for regex, response in input_values:
                if re.search(regex, line):
                    write.write(response)
                    write.flush()
                    break
    return output + "".join(lines)

def run(command, input_values=None):
    """ This function runs the command given in a subprocess and optionally sends input to the
    subprocess using the input_values parameter.
    The input_values paramter may either be a dictionary of output strings to response strings or a list of tuples.
    The list of tuples takes tuples were the first part is a regular expression string and the second part is a response string.
    When the regular expression matches by search one of the output strings, then the response is piped to the command.
    This function may only match against full lines which have been terminated by a newline character.
    Output that is not newline terminated will not be places into the queue for reading and responding.
    """
    runDict = {'shell': True, 'bufsize': 1, 'close_fds': True,
               'stdin': PIPE, 'stdout': PIPE, 'stderr': PIPE
               }
    if type(command) == type(u''): # unicode
        command = command.encode('iso-8859-1')
    run_command = Popen(command, **runDict)
    r, e = map(NonBlockingFile, [run_command.stdout, run_command.stderr])
    write = run_command.stdin
    output = ""
    while True:
        time.sleep(0.25)
        output = read_and_write(r, write, output, input_values)
        output = read_and_write(e, write, output, input_values)
        if run_command.poll() != None and not r.isAlive() and not e.isAlive():
            if r.is_empty() and e.is_empty():
                break
    return output


#
# In order to run single tests and suites of tests we want to be able to do both:
# lts.py suite.test.py (runs ./suite/test.py)        and
# lts.py suite.*       (runs all *.py files in ./suite/)
#
"""
    my $command = shift;
    my($test, @args) = split(' ', $command);
    my($suite, $test) = split(/\./, $test);
    my $logging = $ENV{LTSLOGGING};
    my $verbose = $ENV{LTSVERBOSE};
    my $results = $ENV{LTSRESULTS};
    my $stderrout = $ENV{LTSSTDERROUT};
    $command = "perl ./tests/$suite/$test " . join(' ', @args);
    my $run_id  = get_run_id($workingdir);
    my $logfile = "$workingdir/$run_id.out";
    my $redirect = ($stderrout)? "": "2>&1";
    #unless (fork) {exec("$command $redirect > $logfile");}
    #wait;
    system("$command $redirect > $logfile");
    system("cat $logfile") if ($verbose & 1);
    print substr(`date +%Y/%m/%d-%T.0`,0,-1)." logfile = $logfile\n" if ($verbose & 3);
""" 
def lts_run(command, curdir=None):
    args = command.split()
    #print "In lts_run: args =", args
    test = args.pop(0)
    #print "In lts_run: test = " + test + "\n"
    suite, test = string.split(test, '.', 1)

    #print "suite: %s, test: %s" % (suite, test)
    if curdir is None:
        curdir = os.getcwd()

    testfiles = [os.path.join(curdir, suite, test)]

    if (re.match(r'.*\*.*', test)):
        globstring = os.path.join(curdir, suite, test)
        print "globstring: " + globstring + "\n"
        testfiles = glob.glob(globstring)
        print testfiles
        print "\n"
        #sys.exit()

    results = []
    for test in testfiles:
        if not os.path.isfile(test):
            # try .py
            test += ".py"
        command = test + ' ' + string.join(args, ' ')
        command = re.sub('Program Files', 'Progra~1', command)
        #run_id  = get_run_id($workingdir);
        print ("Running command '" + command + "'")
        results.append(os.system('%s' % command))
        #return os.system('%s' % command)
    
    # logfile = "run_%d.out" % os.getpid()
    # os.system("%s > %s" % (command, logfile))
    # os.system("type %s" % logfile)
    # os.remove(logfile)

    return results


def format_time(seconds=0):
    if not seconds:
        seconds = time.time()
    return time.strftime("%y-%m-%d %H:%M:%S", time.localtime(seconds))

def to_list(multi_line_string):
    list = re.split(multi_line_string, r'\n')
    for line in list:
        if re.match(r'#', line):
            list.remove(line)
    return list

def get_hostname(short=0):
#    if os.name == 'nt':
#        data = win32net.NetServerGetInfo(None, 100)
#        return data['name']
#    else:
#        hostname = socket.gethostname()
#        if short:
#            elem = hostname.split('.')
#            hostname = elem[0]
#        return hostname
    '''The operating system test is no longer needed in new versions of python'''
    hostname = socket.gethostname()
    if short:
        elem = hostname.split('.')
        hostname = elem[0]
     
    for e in sys.argv[1:]:
        if "/hostname=" in e:
            elem = e.split("=")
            hostname = elem[1]
            print "using remote hostname : " + hostname
            
    return hostname
def get_hostip(host=None):
    return socket.gethostbyname(socket.gethostname());
def get_username():
#    if os.name == 'nt':
#        return win32api.GetUserName()
#    else:
#        return getpass.getuser()
    '''The operating system test is no longer needed in new versions of python'''
    return getpass.getuser()

def is_networker():
    line = Popen("rpm -qa | grep ave-scripts", shell=True, stdout=PIPE).stdout.read()
    if line:
        return 1
    else:
        return 0

def get_dpn_version():
    
    line = Popen("rpm -qa | egrep 'dpnserver|ave-scripts'", shell=True, stdout=PIPE).stdout.read()
    
    for e in sys.argv[1:]:
        if "/hostname=" in e:
            elem = e.split("=")
            hostname = elem[1]
            line = Popen(ssh_cmd + " admin@" + hostname + " rpm -qa | egrep 'dpnserver|ave-scripts'", shell=True, stdout=PIPE).stdout.read()               
                
    if line:    
        #version = re.search("dpnserver-(\S+)", line).group(1)
        version = re.search("(\S+)-(\S+\.\S+\.\S+\-\S+)", line).group(2)
        version = version.replace("-", ".")
    else:
        version = "Version_Not_Found"
            
    return version
    
def get_avtar_version():
    #print "get version ....................."
    if os.name == "nt":
        cmd = "C:\\Progra~1\\Avs\\bin\\avtar.exe"
    else:
        
        unixOs = os.popen("uname")
        unixOsOutput = unixOs.read()
        unixOs.close()
        v1 = re.match('Linux', unixOsOutput)
        v2 = re.match('Darwin', unixOsOutput)

        if v1 or v2:
            cmd = "/usr/local/avamar/bin/avtar"
        else:
            cmd = "/opt/AVMRclnt/bin/avtar" 
    cmd = cmd + " --version"
    result = os.popen(cmd)
    output = result.read()
    result.close()
    #print output
    v = re.match('\s+version:\s+([\d\.\-]+)\s+', output)
    if v:
    #print v.group(1)
        return v.group(1)
    else:
        cmd2 = "gsan --version"
        result = os.popen(cmd2)
        output = result.read()
        result.close()
        v2 = re.match('\s+version:\s+([\d\.\-]+)\s+', output)
        if v2:
            return v2.group(1)
        else:
            return "N/A"    

def open_session(command_count=0):
    return time.time()
    data = "cmdcount=%d&" % command_count
    output = http_post(data, "open_session.cgi")
    s = re.search(r'(\d+)', output)
    if (s == None):
        #print "http_post to open_session.cgi returned:\n" + output
        return -1
    return s.group(1)

def post_results(params):
    if not logging: #@UndefinedVariable TODO: find where logging exists
        return  0 
    if not params["test_name"]:
        return -1
    if not params["result"]:
        return -2
    if not params["client"]:
        return -3
    if not params["dpn"]:
        return -4
    if not params["username"]:
        return -5
    
    # TODO: Where are all these variables declared?
    if len(command) > 200: #@UndefinedVariable
        command = command[:200] #@UndefinedVariable @UnusedVariable
    if len(message) > 200: #@UndefinedVariable
        message = message[:200] #@UndefinedVariable @UnusedVariable

    data = "session_id=" + params["session_id"] + "&"
    data = data + "test_name=" + params["test_name"] + "&"
    data = data + "command_id=" + params["command_id"] + "&"
    data = data + "result=" + params["result"] + "&"
    data = data + "client=" + params["client"] + "&"
    data = data + "dpn=" + params["dpn"] + "&"
    data = data + "username=" + params["username"] + "&"
    data = data + "duration=" + params["duration"] + "&"
    data = data + "new=" + params["new"] + "&"
    data = data + "bytecount=" + params["bytecount"] + "&"
    data = data + "command=" + params["command"] + "&"
    data = data + "message=" + params["message"] + "&"
    data = data + "ver=" + params["ver"] + "&"

    # print "post_results data = " + data + "\n"
    output = http_post(data, "post_results.cgi")
    s = re.search(r'(-\d+|\d+)', output)
    return s.group(1)

def add_memo(memo, result_id=0):
    if result_id < 1:
        print "Cannot add memo when result id has not been set"
        return 0

    if len(memo) > 131072:
        memo = memo[:131072]
    
    data = "result_id=%d&memo=%s&" % (result_id, memo)
#    output = http_post(data, "add_memo.cgi")
    return 1


def exclude(list, exclusions):
    for exclusion in exclusions:
        exre = re.compile(r'\s' + exclusion + '\s');
        list = exre.sub("", list)

#
# os.stat() -> (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime)
#                0     1    2    3      4    5     6     7      8      9
#
def fileinfo(name):
    try:
        sr = os.lstat(name)
        # FIX, perl let us check block size and count... do we need to?
        #return string.join((sr[0], sr[4], sr[5], sr[6]), ':')
        return '%d:%d:%d:%d' % (sr.st_mode, sr.st_uid, sr.st_gid, sr.st_size)
    except:
        print "File set might be actively modified by a different process..."
        pass

def filetimevisitor(filetimes, thisdir, nameshere):
    for name in nameshere:
        fullpath = os.path.join(thisdir, name)
        if not os.path.isfile(fullpath):
            continue
        #print "visit thisdir='%s' name='%s'" % (thisdir, name)
        savedir = os.getcwd()
        os.chdir(thisdir)
        sr = os.stat(name) #fullpath)
        os.chdir(savedir)
        filetimes[fullpath] = {'atime': sr.st_atime,
                               'mtime': sr.st_mtime,
                               'ctime': sr.st_ctime}


def get_file_times(root=os.curdir):
    matches = []
    ftimes = {}
    os.path.walk(root, filetimevisitor, ftimes)
    return ftimes


def findfilesvisitor((matches, pattern), thisdir, nameshere):
    for name in nameshere:
        if fnmatch.fnmatch(name, pattern):
            fullpath = os.path.join(thisdir, name)
            matches.append(fullpath)

def findfiles(pattern, root=os.curdir):
    matches = []
    os.path.walk(root, findfilesvisitor, (matches, pattern))
    matches.sort()
    return matches

def get_relative_path(orig_path, root_path):
    if orig_path == root_path:
        return "TREE_ROOT"
    if os.name == 'nt':
        if orig_path.find(root_path) == -1:
            return None
        if orig_path.find(root_path) != 0:
            return None
        l = len(root_path) + 1
        return orig_path[l:]

    s = re.search(r'%s/(.*)' % root_path, orig_path)
    if s:
        return s.group(1)
    return None

def treewalk(root=os.curdir, depthfirst=True):
    if depthfirst:
        index = -1
    else:
        index = 0
    dirstack = [root]
    while dirstack:
        # Pop a path from the stack and try to get
        # a directory listing for the path.
        path = dirstack.pop(index)
        # Try to list the the contents in the path
        # if the path is a directory, otherwise go
        # on traversing to the next directory
        try:
            names = os.listdir(path)
        except os.error:
            return
        # Start generating absolute path names
        for name in names:
            yield os.path.join(path, name)
        dirs = []
        # Start determining which paths lead to
        # any other subdirectories and extend
        # the stack with those directories
        for name in names:
            curpath = os.path.join(path, name)
            if os.path.isdir(curpath):
                dirs.append(curpath)
        if depthfirst:
            dirs.reverse()
        dirstack.extend(dirs)

# Generator method that generates paths for the current
# directory.  Nonrecursive in order to conserve memory,
# due to very large directories, which will limit the
# amount of recursion.
def flatwalk(root=os.curdir):
    try:
        paths = os.listdir(root)
    except os.error:
        return
    for path in paths:
        fullpath = os.path.join(root, path)
        yield fullpath
        
# Flatdiff is intended for use for directories that have
# a huge number of files and subdirectories (i.e > 50000).  The
# data structure that gets generated in simple_diff ends up pushing
# the memory boundary for the Python VM, which results in a MemoryException.
# Pretty simple algorithm, compare the files then each subdirectory before
# traversing lower into the tree.
def flatdiff(src_root, dest_root, src_exclude=[], dest_exclude=[], mtime=False, log=None):
    def string_sort(str_list):
        aux_list = [x for x in str_list]
        aux_list.sort()
        return [x for x in aux_list]
    srcdirstack = [src_root]
    destdirstack = [dest_root]
    isfile_src = lambda x: os.path.isfile(os.path.join(src_root, x))
    isfile_dest = lambda x: os.path.isfile(os.path.join(dest_root, x))
    getfsize = lambda x, y: os.stat(os.path.join(x, y))[ST_SIZE]
    getmtime = lambda x, y: os.stat(os.path.join(x, y))[ST_MTIME]
    isdir_src = lambda x: os.path.isdir(os.path.join(src_root, x))
    isdir_dest = lambda x: os.path.isdir(os.path.join(dest_root, x))
    # Both directory stacks need to be synchronized (i.e in sorted order) in
    # order for the test to pass. Otherwise, it is an indication that there
    # is a difference between the directories. Also, any variation in the
    # length of the stacks will fail the tests.
    while len(srcdirstack) == len(destdirstack) and len(srcdirstack) > 0:
        srcdirs = destdirs = []
        src_filelist = dest_filelist = {}
        srcpath = srcdirstack.pop()
        destpath = destdirstack.pop()
        print "current working src path: %s" % srcpath
        print "current working dest path: %s" % destpath
        # Generate relative paths for both the source and destination
        src_paths = [get_relative_path(path, src_root)
                     for path in flatwalk(srcpath)]
        dest_paths = [get_relative_path(path, dest_root)
                      for path in flatwalk(destpath)]
        # Check for excludes
        for exclude in src_exclude:
            if exclude in src_paths:
                src_paths.remove(exclude)
        for exclude in dest_exclude:
            if exclude in dest_paths:
                dest_paths.remove(exclude)
        src_paths = string_sort(src_paths)
        dest_paths = string_sort(dest_paths)
        if log:
            log.info("Source directory count: %d" % len(src_paths))
            log.info("Destination directory count: %d" % len(dest_paths))
        if len(src_paths) != len(dest_paths):
            return "Failure"
        if src_paths != dest_paths:
            return "Failure eq paths"
        # Make a dictionary of files and file size statistics, if mtime
        # is set, then also get the modification times for those files.
        if mtime:
            # We can create a dictionary of files with fsizes and (optional) mtimes
            # using a list comprehension and list filtering.
            src_filelist = dict([(path, (getfsize(src_root, path), getmtime(src_root, path)))
                                 for path in filter(isfile_src, src_paths)])
            dest_filelist = dict([(path, (getfsize(dest_root, path), getmtime(dest_root, path)))
                                  for path in filter(isfile_dest, dest_paths)])
        else:
            src_filelist = dict([(path, getfsize(src_root, path))
                                 for path in filter(isfile_src, src_paths)])
            dest_filelist = dict([(path, getfsize(dest_root, path))
                                  for path in filter(isfile_dest, dest_paths)])
        if len(src_filelist) != len(dest_filelist):
            return "Failure"
        if src_filelist != dest_filelist:
            return "Failure"
        # Start creating a list of directories that need to be
        # traversed, in natural alphabetical order.
        srcdirs = [os.path.join(src_root, path)
                   for path in filter(isdir_src, src_paths)]
        destdirs = [os.path.join(dest_root, path)
                    for path in filter(isdir_dest, src_paths)]
        srcdirs = string_sort(srcdirs)
        destdirs = string_sort(destdirs)
        # Extend the stacks with the subdirectores in the current
        # toplevel tree diff.
        srcdirstack.extend(srcdirs)
        destdirstack.extend(destdirs)
    # If somehow the stack lengths differed at all during the progress
    # of the directory diff, then check it and fail if it the two
    # stacks are ever different
    if len(srcdirstack) != len(destdirstack):
        return "Failure"
    return "Success"

# 08/19/2005 Henry Wong: simple_diff added to compare directory
# structure of snapup and restore. Added generators to simplify the
# directory tree traversal. This method should be used only with
# trees that are known to contain less than 1000 elements, since
# generator might generate a huge list of paths.
#
# 08/28/2005 Henry Wong: modified file dictionary generation using a
# list comprehension, rather than a for loop construct. Also added
# flatdiff for huge directory structures.
def simple_diff(src_root, dest_root, exclusion_list=[], log=None, mtime=False):
    def string_sort(str_list):
        aux_list = [x for x in str_list]
        aux_list.sort()
        return [x for x in aux_list]
    isfile_src = lambda x: os.path.isfile(os.path.join(src_root, x))
    isfile_dest = lambda x: os.path.isfile(os.path.join(dest_root, x))
    getfsize = lambda x, y: os.stat(os.path.join(x, y))[ST_SIZE]
    getmtime = lambda x, y: os.stat(os.path.join(x, y))[ST_MTIME]
    # List comprehension for the entire tree starting
    # from src_root and dest_root.
    src_tree = [get_relative_path(path, src_root)
                for path in treewalk(src_root)]
    dest_tree = [get_relative_path(path, dest_root)
                 for path in treewalk(dest_root)]
    if log:
        log.debug("source directory tree (before exclusions): ", src_tree)
        log.debug("destination directory tree (before exclusions): ", dest_tree)
    # File listings for the trees, stored as relative paths to the root.
    src_filelist = {}
    dest_filelist = {}
    # Need to keep track of removals since removing while iterating is bad.
    rmlist = []
    # Since the exclusions share the same parent path
    # we can factor that out and focus on them using
    # relative path names.
    for exclude in exclusion_list:
        src_tree.remove(exclude)
        for path in src_tree:
            # excludes will never end in a slash, since
            # we don't really care if its a file or a directory
            matcher = re.search(r"^%s(/.*)$" % exclude, path)
            if matcher is not None:
                rmlist.append(path)
    # Remove everything that matched from the source tree.
    if log:
        log.debug("paths to remove", rmlist)
    # Make sure the path is still present in the source tree.
    for path in rmlist:
        if path in src_tree:
            src_tree.remove(path)
    if log:
        log.debug("source directory tree (after exclusions): ", src_tree)
        log.debug("destination directory tree (after exclusions): ", dest_tree)
    # Check for the length of the source and destination
    # tree after pruning the list of any exluded directories and files.
    src_tree = string_sort(src_tree)
    dest_tree = string_sort(dest_tree)
    if len(src_tree) != len(dest_tree):
        return "Failure"
    if src_tree != dest_tree:
        return "Failure"
    # Make a dictionary of files and file size statistics, if mtime
    # is set, then also get the modification times for those files.
    if mtime:
        src_filelist = dict([(path, (getfsize(src_root, path), getmtime(src_root, path)))
                             for path in filter(isfile_src, src_tree)])
        dest_filelist = dict([(path, (getfsize(dest_root, path), getmtime(dest_root, path)))
                              for path in filter(isfile_dest, dest_tree)])
    else:
        src_filelist = dict([(path, getfsize(src_root, path))
                             for path in filter(isfile_src, src_tree)])
        dest_filelist = dict([(path, getfsize(dest_root, path))
                              for path in filter(isfile_dest, dest_tree)])
    if log:
        log.debug("src file tree: ", src_filelist)
        log.debug("dst file tree: ", dest_filelist)
    # Should never be the case that the sizes mismatch, but do
    # a sanity check in case.
    if len(src_filelist) != len(dest_filelist):
        return "Failure"
    # Compare files and file statistics to see if statistics
    # are preserved before and after snapups
    if src_filelist != dest_filelist:
        return "Failure"
    return "Success"


def diff(source1, source2, excludelist=None, srcmodtimes=None, ignoreline=None):
    if os.name == 'nt':
        return recursivediffw(source1, source2, ignoreline)
    else:
        return posixdiff(source1, source2, excludelist, srcmodtimes)

def recursivediffw(dir1, dir2, ignoreline=None):
    dirsep = "\\"
    #prefix = unicode(dirsep + dirsep + '?' + dirsep)
    prefix = ""
    
    dir1 = unicode(dir1)
    dir2 = unicode(dir2)
    
    # find all the entries in each dir, sort them
    # stepping through one by one, if the adjacent entries are files,
    # compare the relevant attributes.  If they're directories, 
    # call into this again

    ffpath1 = prefix + dir1 + unicode(dirsep + '*')
    ffpath2 = prefix + dir2 + unicode(dirsep + '*')
    #sys.exit(0);

    print_ffpath1 = ffpath1.encode('iso-8859-1')
    print_ffpath2 = ffpath2.encode('iso-8859-1')
    
    try:
        res1 = win32file.FindFilesW(ffpath1)
    except:
        print "FindFilesW barfed for '%s'" % print_ffpath1
        res1 = []
        raise

    try:
        res2 = win32file.FindFilesW(ffpath2)
    except:
        print "FindFilesW barfed for '%s'" % print_ffpath2
        res2 = []
        raise

    if len(res1) != len(res2):
        diff_output = "Found differing number of entries in %s vs %s" % (print_ffpath1, print_ffpath2)
        print diff_output
        return -1, diff_output
    
    maxi = max(len(res1), len(res2))
    i = 0
    while i < maxi:
        f1 = res1[i]
        f2 = res2[i]
        i = i + 1
        #print "f1: ", f1
        #print "f2: ", f2
        name1 = f1[8]
        name2 = f2[8]

        if name1 != name2:
            diff_output = "%s != %s" % (name1, name2)
            print diff_output
            return -2, diff_output
            
        if name1 == r'.' or name1 == r'..': continue
        
        path1 = dir1 + unicode(dirsep) + name1
        path2 = dir2 + unicode(dirsep) + name2

        attr1 = win32file.GetFileAttributesW(prefix + path1)
        attr2 = win32file.GetFileAttributesW(prefix + path2)

        # The NORMAL attribute is just set when nothing else is; it
        # carries no information.  We set the ARCHIVE bit after archiving
        # stuff, so it doesn't either.
        testattr1 = attr1 & (~win32file.FILE_ATTRIBUTE_ARCHIVE)
        testattr1 = testattr1 & (~win32file.FILE_ATTRIBUTE_NORMAL)
        testattr2 = attr2 & (~win32file.FILE_ATTRIBUTE_ARCHIVE)
        testattr2 = testattr2 & (~win32file.FILE_ATTRIBUTE_NORMAL)
        if testattr1 != testattr2:
            diff_output = "%s attr != %s attr" % (print_path1, print_path2) #@UndefinedVariable TODO: Verify print path
            diff_output = diff_output + '\n' + str(attr1) + "\t" + str(testattr1)
            diff_output = diff_output + '\n' + str(attr2) + "\t" + str(testattr2) + '\n'
            print diff_output
            return -3, diff_output

        if attr1 == 16:
            # it's a directory, so we should push it's name onto our dir list
            recursivediffw(path1, path2)        
            

        else:
        # Grig 8/6/04 -- diff the contents of the files
            r1 = open(path1)
            l1 = r1.readlines()
            r1.close()
            r2 = open(path2)
            l2 = r2.readlines()
            r2.close()
            from difflib import Differ
            diff = Differ()
            result = list(diff.compare(l1, l2))
            # only keep the lines that start with +, - or ?
            searchFunction = lambda line: re.search(r'^[+|-|?]', line)  
            result = filter(searchFunction, result)
            print_path1 = path1.encode('iso-8859-1')
            print_path2 = path2.encode('iso-8859-1')

            if result:
                diff_output1 = "Differing file contents for: \n\'%s\' \nvs \n\'%s\'\n" % \
                    (print_path1, print_path2)
                diff_output = diff_output1 + '\n'.join(result)
                print_diff_output = diff_output1 + '\n'.join(result[:100])
                print print_diff_output
                return -4, diff_output
        

            
    return 1, None
"""

def recursivediffw(dir1, dir2, ignoreline=None):
    dirsep = "\\"
    #prefix = unicode(dirsep + dirsep + '?' + dirsep)
    prefix = ""
    
    dir1 = unicode(dir1)
    dir2 = unicode(dir2)
    
    # find all the entries in each dir, sort them
    # stepping through one by one, if the adjacent entries are files,
    # compare the relevant attributes.  If they're directories, 
    # call into this again

    ffpath1 = prefix + dir1 + unicode(dirsep + '*')
    ffpath2 = prefix + dir2 + unicode(dirsep + '*')
    #sys.exit(0);

    print_ffpath1 = ffpath1.encode('iso-8859-1')
    print_ffpath2 = ffpath2.encode('iso-8859-1')
    
    try:
        res1 = win32file.FindFilesW(ffpath1)
    except:
        print "FindFilesW barfed for '%s'" % print_ffpath1
        res1 = []
        raise

    try:
        res2 = win32file.FindFilesW(ffpath2)
    except:
        print "FindFilesW barfed for '%s'" % print_ffpath2
        res2 = []
        raise

    if len(res1) != len(res2):
        diff_output = "Found differing number of entries in %s vs %s" % (print_ffpath1, print_ffpath2)
        print diff_output
        return -1, diff_output
    
    maxi = max(len(res1), len(res2))
    i = 0
    while i < maxi:
        f1 = res1[i]
        f2 = res2[i]
        i = i+1
        #print "f1: ", f1
        #print "f2: ", f2
        name1 = f1[8]
        name2 = f2[8]

        if name1 != name2:
            diff_output = "%s != %s" % (name1, name2)
            print diff_output
            return -2, diff_output
            
        if name1 == r'.' or name1 == r'..': continue
        
        path1 = dir1 + unicode(dirsep) + name1
        path2 = dir2 + unicode(dirsep) + name2

        # Grig 8/6/04 -- diff the contents of the files
        r1 = open(path1)
        l1 = r1.readlines()
        r1.close()
        r2 = open(path2)
        l2 = r2.readlines()
        r2.close()
        from difflib import Differ
        diff = Differ()
        result = list(diff.compare(l1, l2))
        # only keep the lines that start with +, - or ?
        searchFunction = lambda line: re.search(r'^[+|-|?]', line)  
        result = filter(searchFunction, result)
        print_path1 = path1.encode('iso-8859-1')
        print_path2 = path2.encode('iso-8859-1')

        if result:
            diff_output1 = "Differing file contents for: \n\'%s\' \nvs \n\'%s\'\n" % \
                    (print_path1, print_path2)
            diff_output = diff_output1 + '\n'.join(result)
            print_diff_output = diff_output1 + '\n'.join(result[:100])
            print print_diff_output
            return -4, diff_output
        
        attr1 = win32file.GetFileAttributesW(prefix + path1)
        attr2 = win32file.GetFileAttributesW(prefix + path2)

        # The NORMAL attribute is just set when nothing else is; it
        # carries no information.  We set the ARCHIVE bit after archiving
        # stuff, so it doesn't either.
        testattr1 = attr1 & (~win32file.FILE_ATTRIBUTE_ARCHIVE)
        testattr1 = testattr1 & (~win32file.FILE_ATTRIBUTE_NORMAL)
        testattr2 = attr2 & (~win32file.FILE_ATTRIBUTE_ARCHIVE)
        testattr2 = testattr2 & (~win32file.FILE_ATTRIBUTE_NORMAL)
        if testattr1 != testattr2:
            diff_output = "%s attr != %s attr" % (print_path1, print_path2)
            diff_output = diff_output + '\n' + str(attr1) + "\t" + str(testattr1)
            diff_output = diff_output + '\n' + str(attr2) + "\t" + str(testattr2) + '\n'
            print diff_output
            return -3, diff_output

        if attr1 == 16:
            # it's a directory, so we should push it's name onto our dir list
            recursivediffw(path1, path2)
            
    return 1, None
"""

def srinfo(statresult):
    return "%d:%d:%d:%d" % (statresult.st_mode, statresult.st_uid, statresult.st_gid, statresult.st_size)


def posixdiff(source1, source2, excludelist=None, srcmodtimes=None, verbose=False):
    """A more agressive diff of two directories than the diff utility.

    Things we should worry about:
    * Gross directory structure; are there the same files and directories in the
      same places and with the same names.
    * File contents; do two files with the same path have the same bytes.
    * Permissions
    * ACLs
    * Modification times (to the extent that avtar preserves them).
    * Link targets; both symlinks and hardlinks, if a file has a certain
      number of hard links in one tree it should have the same number in
      the copy as well?
    """

    srcinodes = {}
    destinodes = {}
    inosrc2dest = {}
    stack = []
    lp = LocationPair(source1, source2)

    stack.append(lp)

    while len(stack):
        lp = stack.pop()
        lp.cdsrc()
        s_entries = os.listdir('.')
        s_entries.sort()
        
        lp.cddest()
        d_entries = os.listdir('.')
        d_entries.sort()

        if len(s_entries) != len(d_entries):
            diff_output = "Differing number of entries (%d and %d) for \n%s \nvs \n%s" % \
                          (len(s_entries), len(d_entries), lp.srcpath(), lp.destpath())
            if verbose:
                print diff_output
            return -1, diff_output

        while len(s_entries):
            n1 = s_entries.pop()
            n2 = d_entries.pop()
#            print "value of n1 and n2 is %s and %s" %(n1,n2)

            if n1 != n2:
                diff_output = "mismatched file names: \n%s \nvs \n%s" % (n1, n2)
                if verbose:
                    print diff_output
                return -2, diff_output

#            lp.cdsrc()
            sr1 = os.lstat(n1)
#            print "\nvalue of sr1 is: %s\n" %sr1
            n1isdir = os.path.isdir(n1)
            n1islink = os.path.islink(n1)
            lp.cddest()
            sr2 = os.lstat(n2)
#            print "\nvalue of sr2 is: %s\n" %sr2
            n2isdir = os.path.isdir(n2)
            n2islink = os.path.islink(n2)

            if srinfo(sr1) != srinfo(sr2): #fileinfo(sr1) != fileinfo(sr2):
                diff_output = "differing fileinfo \n%s\n%s\nfor: \n%s \nvs \n%s\n%s - %s" % (sr1, sr2,
                                                                                             os.path.join(lp.srcpath(), n1),
                                                                                             os.path.join(lp.destpath(), n2),
                                                                                             srinfo(sr1), srinfo(sr2))
                if verbose:
                    print diff_output
                return -3, diff_output

            if n1islink and n2islink:
                continue

            # The only way to verify that a group of hard links to the same inode
            # turns into an equivalent group after copy or restore is to keep track
            # of the set of files that the inode on the source and dest sides are
            # equivalent to, and compare after we're done with the tree walk.
            if sr1.st_nlink > 0 and sr2.st_nlink > 0:
                if not srcinodes.has_key(sr1.st_ino.__repr__()):
                    srcinodes[sr1.st_ino.__repr__()] = []
                if not destinodes.has_key(sr2.st_ino.__repr__()):
                    destinodes[sr2.st_ino.__repr__()] = []
                srcinodes[sr1.st_ino.__repr__()].append(n1)
                inosrc2dest[sr1.st_ino.__repr__()] = sr2.st_ino.__repr__()
                destinodes[sr2.st_ino.__repr__()].append(n2)

            if n1isdir and n2isdir:
                nlp = copy.deepcopy(lp)
                nlp.descend(n1)
                stack.append(nlp)
            else:
                if not lp.filesequal(n1, n2):
                    diff_output = "differing file contents for: \n%s \nvs \n%s" % (lp.srcpath(), lp.destpath())
                    if verbose:
                        print diff_output
                    return -4, diff_output

    # Handle all the shared hardlink checks...
    for ino in srcinodes.keys():
        srcset = srcinodes[ino]
        dino = inosrc2dest[ino]
        destset = destinodes[dino]
        if srcset != destset:
            diff_output = "Hard links to inode %s did not translate into appropriate set of hard links in copy %s" % (ino, dino)
            if verbose:
                print diff_output
            return -5, diff_output

    return 1, None


def diff_solaris_acls(source1, source2, excludelist=None):
    files1 = findfiles("*", source1)
    files2 = findfiles("*", source2)
    if excludelist: exclude(files1, excludelist)
    if len(files1) != len(files2): return -1
    for i in xrange(len(files1)):
        name1 = files1.pop()
        name2 = files2.pop()
        if (os.path.split(name1)[1] != os.path.split(name2)[1]): return -2
        acl1 = os.popen("getfacl " + name1, "r").read();
        acl2 = os.popen("getfacl " + name2, "r").read();
        acl1 = re.sub(r'# file: .*\n', '', acl1)
        acl2 = re.sub(r'# file: .*\n', '', acl2)
        if acl1 != acl2:
            print ("acl1:-------------------------------------------\n%s" % acl1);
            print ("acl2:-------------------------------------------\n%s" % acl2);
            return -3
    return 1


#--- RANDOM DATA GENERATION AND MODIFICATION -----------------------------------

def random_int(max):
    return choice(xrange(max))


def random_string(length):
    result = ""
    for i in xrange(length):
        flip_coin = choice(range(2))
        if flip_coin:
            start_from = 65 # A
        else:
            start_from = 97 # a
        result = result + chr(random_int(25) + start_from)
    return result


def random_hex_string(kperblock=1):
    #result = ""
    cstr = cStringIO.StringIO()
    for i in xrange(kperblock):
        for j in xrange(128):
            cstr.write('%04x' % int(random() * ((16 ** 4) - 1)))
            cstr.write('%04x' % int(random() * ((16 ** 4) - 1)))

    result = cstr.getvalue()
    cstr.close()
    #result = substr(result, 0, (1024 * kperblock - 1)) + "\n";
    result = result[0:(1024 * kperblock - 1)] + "\n";
    return result


def random_files(startdir, filecount, blockcount, kperblock=1, filename=None, log=None):
    usedd = os.access("/dev/urandom", os.F_OK) and (os.system("dd bs=1k count=1 if=/dev/null of=/dev/null > /dev/null 2>&1") == 0) and blockcount and kperblock

    for i in xrange(filecount):
        if filecount > 1 or filename is None:
            filename = random_string(10)
        fullname = os.path.join(startdir, filename)
        if log: log("Creating file %s with size %d KB" % (fullname, blockcount * kperblock))
        if usedd:
            #if log: log("Using fast /dev/urandom to generate " + fullname)
            cmd = "dd bs=%dk count=%d if=/dev/urandom of=%s > /dev/null 2>&1" % (kperblock, blockcount, fullname)
            os.system(cmd)
        else:
            #if log: log("Using slow internal random_hex_string data generation for " + fullname)
            outfile = open(fullname, "wb")
            for j in xrange(blockcount):
                outfile.write(random_hex_string(kperblock))
            outfile.close()

def random_links(startdir):
    filename = random_string(10) + ".file"
    dirname = random_string(10) + ".dir"
    
    fullname = os.path.join(startdir, filename)    
    fulldirname = os.path.join(startdir, dirname)

    outfile = open(fullname, "wb")
    outfile.write(random_hex_string(128))
    outfile.close()

    os.mkdir(fulldirname)
    
    # make abs and relative links to file
    os.system("ln -s %s %s" % (fullname, fullname + ".abssym"))
    os.system("ln -s %s %s" % (fulldirname, fulldirname + ".abssym"))
    origdir = os.getcwd()
    os.chdir(startdir)
    os.system("ln %s %s" % (filename, filename + ".hard"))
    os.system("ln -s %s %s" % (filename, filename + ".relsym"))
    os.system("ln -s %s %s" % (dirname, dirname + ".relsym"))
    os.chdir(origdir)
    
        
def random_data(startdir, dirlevels=1, dircount=1, filecount=1, filesize=128, kperblock=1):
    #topdir = os.path.join(startdir, random_string(8))
    #os.mkdir(topdir, 0777)
    #random_data_recursive(topdir, dirlevels - 1, dircount, filecount, filesize, kperblock)
    random_data_recursive(startdir, dirlevels, dircount, filecount, filesize, kperblock)


def random_data_recursive(startdir, dirlevels=1, dircount=1, filecount=1, filesize=128, kperblock=1):
    if not startdir: return 0

    # Make the files in the current directory level
    #for i in xrange(filecount):
    random_files (startdir, filecount, filesize, kperblock)

    # Terminate recursion
    if dirlevels < 1:
        #random_files (startdir, filecount, filesize, kperblock)
        return

    # Next level
    for i in xrange(dircount):
        nextdir = os.path.join (startdir, random_string(8))
        os.mkdir(nextdir, 0777)
        random_data_recursive (nextdir, dirlevels - 1, dircount, filecount, filesize, kperblock)


def generate_exhaustive_chmod_dir (targetdir):
    if not os.access(targetdir, os.F_OK):
        os.mkdir (targetdir)

    S_list = (0, 2, 4)
    O_list = G_list = W_list = (0, 1, 2, 3, 4, 5, 6, 7)

    for S in S_list:
        for O in O_list:
            for G in G_list:
                for W in W_list:
                    (dir1, dir2, file) = (random_string(8), random_string(8), random_string(8))
                    os.mkdir(os.path.join(targetdir, dir1))
                    os.mkdir(os.path.join(targetdir, dir2))
                    fullfname = os.path.join(targetdir, dir2, file)
                    os.system ("date > " + fullfname)
                    chmodperms = int('%d%d%d%d' % (S, O, G, W))
                    #print "setting chmod $chmod for $dir1 and $dir2\n";
                    os.chmod (os.path.join(targetdir, dir2, file), chmodperms)
                    os.chmod (os.path.join(targetdir, dir1), chmodperms)
                    os.chmod (os.path.join(targetdir, dir2), chmodperms)
                    
def generate_macosx_bsd(targetdir):
    if not os.access(targetdir, os.F_OK):
        os.mkdir(targetdir)
    os.chdir(targetdir)
    file_flag = ("arch", "opaque", "nodump", "sappnd", "schg", "uappnd", "uchg")
    for flag in file_flag:
        random_str = random_string(8)
        file1 = open(random_str, "w")
        file1.write("test bsd file flag")
        file1.close()
        cmd = "chflags " + flag + " " + random_str

        os.popen(cmd)

    
                            

def generate_representative_solaris_acl_dir (targetdir):
    if not os.access(targetdir, os.F_OK):
        os.mkdir(targetdir)
        
    USRGRP_list = xrange(0, 1000)
    PERM_list = xrange(0, 8)

    for i in xrange(0, 20):  # make 20 files
        (dir1, dir2, file) = (random_string(8), random_string(8), random_string(8))
        os.mkdir(os.path.join(targetdir, dir1))
        os.mkdir(os.path.join(targetdir, dir2))
        fullfname = os.path.join(targetdir, dir2, file)
        os.system ("date > " + fullfname)

        # Ok, with the empty dir, the dir with file, and the file, apply some random acls
        for j in xrange(0, 5):
            facl = "-m %s:%d:%d" % (choice(('user', 'group')),
                                    choice(USRGRP_list),
                                    choice(PERM_list))
            fulldir1 = os.path.join(targetdir, dir1)
            fulldir2 = os.path.join(targetdir, dir2)
            os.system ("setfacl %s %s" % (facl, fulldir1))
            os.system ("setfacl %s %s" % (facl, fulldir2))
            os.system ("setfacl %s %s" % (facl, fullfname))

def modify_dir_tree(tree_root):
    os.path.walk(tree_root, modify_dir_element, arg=None)

def modify_dir_element(arg, dirpath, namelist):
    funclist = [delete_file, rename_file]
    file_funclist = funclist + [create_file, replace_file_with_link,
                grow_file, shrink_file, modify_file_stats]
    link_funclist = funclist + [replace_link_with_file]
    for name in namelist:
        fullpath = os.path.join(dirpath, name)
        if os.path.isdir(fullpath):
            continue
        if os.path.islink(fullpath):
            func = choice(link_funclist)
        else:
            func = choice(file_funclist)
        func(fullpath)

def create_file(fullpath, log=None, is_set=0):
    startdir = os.path.dirname(fullpath)
    filename = os.path.basename(fullpath)
    blockcount = choice(range(1, 128))
    kperblock = choice(range(1, 10))
    filecount = 1
    if log:
        log.info("Creating random file")
    if not is_set:
        # let random_files choose a random filename
        filename = None
    random_files(startdir, filecount, blockcount, kperblock, filename=filename, verbose=1)

def delete_file(fullpath, log=None):
    if log:
        log.info("Deleting", fullpath)
    os.unlink(fullpath)

def rename_file(fullpath, log=None):
    pid = os.getpid()
    new_filename = "%s_%d" % (fullpath, pid)
    if log:
        log.info("Renaming %s to %s" % (fullpath, new_filename))
    os.rename(fullpath, new_filename)

def grow_file(fullpath, log=None):
    f = open(fullpath, "ab")
    blockcount = choice(range(1, 128))
    kperblock = choice(range(1, 10))
    if log:
        log.info("Growing %s by %d KB" % (fullpath, blockcount * kperblock))
    for j in xrange(blockcount):
        f.write(random_hex_string(kperblock))
    f.close()

def shrink_file(fullpath, log=None):
    stats = os.stat(fullpath)
    size = stats[stat.ST_SIZE]
    keep = choice(range(1, 99))
    new_size = (size * keep) / 100
    if log:
        log.info("Shrinking %s from %d to %d bytes" % (fullpath, size, new_size))
    f = open(fullpath, "wb")
    f.truncate(new_size)
    f.close()

def modify_file_stats(fullpath, log=None):
    if os.name == 'nt':
        return
    (mode, inode, devid, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(fullpath)
    our_uid = os.getuid() #@UndefinedVariable Available on unix
    if our_uid == 0:    # we are root
        percent = choice(range(1, 100))
        new_uid = (uid * percent) / 100
        if log:
            log.info("Changing uid of %s from %d to %d" % (fullpath, uid, new_uid))
        os.system("chown %d %s" % (new_uid, fullpath))
        percent = choice(range(1, 100))
        new_gid = (gid * percent) / 100
        if log:
            log.info("Changing gid of %s from %d to %d" % (fullpath, gid, new_gid))
        os.system("chgrp %d %s" % (new_gid, fullpath))
        modlist = ["u+r", "u+w", "u+x", "u-r", "u-w", "u-x",
                   "g+r", "g+w", "g+x", "g-r", "g-w", "g-x",
                   "o+r", "o+w", "o+x", "o-r", "o-w", "o-x",
                   "a+r", "a+w", "a+x", "a-r", "a-w", "a-x"]
        mod = choice(modlist)
        if log:
            log.info("Changing mod of %s to '%s'" % (fullpath, mod))
        os.system("chmod %s %s" % (mod, fullpath))
    delta = choice(xrange(-43200, 43200))
    new_atime = time.asctime(time.localtime(atime + delta))
    if log:
        log.info("Changing atime of %s from '%s' to '%s'" % \
                 (fullpath, time.asctime(time.localtime(atime)), new_atime))
    os.system("touch -a --date='%s' %s" % (new_atime, fullpath))
    delta = choice(xrange(-43200, 43200))
    new_mtime = time.asctime(time.localtime(mtime + delta))
    if log:
        log.info("Changing mtime of %s from '%s' to '%s'" % \
                 (fullpath, time.asctime(time.localtime(mtime)), new_mtime))
    os.system("touch -m --date='%s' %s" % (new_mtime, fullpath))

def replace_link_with_file(fullpath, log=None):
    delete_file(fullpath)
    if log:
        log.info("Replacing link %s with file" % (fullpath))
    create_file(fullpath, is_set=1)
    
def replace_file_with_link(fullpath, log=None):
    if os.name == 'nt':
        # sorry, no links
        return
    startdir = os.path.dirname(fullpath)
    linkname = os.path.basename(fullpath)
    toss = choice(range(100))
    if toss < 50:
        symlink = 0
    else:
        symlink = 1
    toss = choice(range(100))
    if toss < 50:
        filelink = 0
    else:
        filelink = 1
    # hard links are not allowed for directories
    if not filelink:
        symlink = 1
    if symlink:
        type = "symbolic"
    else:
        type = "hard"
    if filelink:
        src = "file"
    else:
        src = "directory"
    if log:
        log.info("Replacing file %s with %s link to %s" % (fullpath, type, src))
    delete_file(fullpath)
    create_link(startdir, linkname, symlink, filelink)

def create_link(startdir, linkname, symlink=1, filelink=1):
    filename = random_string(10) + ".file"
    dirname = random_string(10) + ".dir"
    
    fullname = os.path.join(startdir, filename)    
    fulldirname = os.path.join(startdir, dirname)

    if filelink:
        outfile = open(fullname, "wb")
        outfile.write(random_hex_string(128))
        outfile.close()
        src = fullname
    else:
        os.mkdir(fulldirname)
        src = fulldirname
    
    dest = os.path.join(startdir, linkname)
    if symlink: 
        os.system("ln -s %s %s" % (src, dest))
    else:
        os.system("ln %s %s" % (src, dest))

def get_os_name():
    if os.name == "nt":
        return "Windows"
    else:
        stdin, stdout, stderr = os.popen3("uname")
        line = stdout.readlines()[0]
        return string.rstrip(line)

def get_os_type():
    kickstart_version = os.popen("ls / | egrep 'rhel|sles'").read()
    return kickstart_version[0:4] 
        
def run_shell_cmd(cmd):
    stdin, stdout, stderr = os.popen3(cmd)
    lines = stdout.readlines()
    return "".join(lines)

def cat(file):
    f = open(file, "r")
    content = "".join(f.readlines())
    f.close()
    return content

def prep_dirs(workdir):
    os.mkdir(workdir, 0777)
    os.mkdir(os.path.join(workdir, "vardir"), 0777)
    os.mkdir(os.path.join(workdir, "backup"), 0777)

def get_run_id(dir):
    #runid is the timestamp + pid
    timestamp = "%s.%s" % (time.time(), os.getpid())
    while (os.path.exists(os.path.join(dir, timestamp + ".out"))):
        timestamp = "%s.%s" % (time.time(), os.getpid())
    filename = os.path.join(dir, "%s.out" % timestamp)
    #out = open(filename, "w")
    #out.write("File created\n")
    #out.close()
    return timestamp

def run_parallel(commands):
    pids = []
    for command in commands:
        pid = os.fork() #@UndefinedVariable Available on unix
        if pid: 
            pids.append(pid)
        else:
            exec(command)
            break
    return pids
def os_fork(command):
    pid = os.fork() #@UndefinedVariable Available on unix
    if not pid: 
        exec(command)
        os.waitpid(pid, WNOHANG) #@UndefinedVariable Available on unix

# cleans temp log folder before a test starts
def logclean(workingdir):
    os.system("rm -f %s/*.out" % workingdir)        # remove dirty log files before starting testcase
    os.system("rm -f %s/*.messages" % workingdir)        # remove dirty log files before starting testcase
    os.system("rm -f %s/*.csv" % workingdir)        # remove dirty log files before starting testcase
    os.system("rm -f %s/*.txt" % workingdir)
    os.system("rm -f %s/*.png" % workingdir) 
        
# parse options array for either help definition or option values
def parse_opt(arg, default=0):
    if arg == '/help' or arg == '/h':
        return options_help.iteritems()
    elif options.has_key(arg):
        return options[arg]
    else:  
        return default
    
# define options descriptions
def define_opt(arg, descript):
    options_help[arg] = descript

# read in user defined options
def read_opt(arg, value):
    options[arg] = value;
    
def read_opts(argv):
    args = ""
    for arg in argv:
        args += arg + " "
        if arg == '/help' or arg == '/h':
            for help in parse_opt('/h'):
                print help[1] 
            sys.exit(0)
        elif re.search('=', arg):
            arg, value = arg.split('=')
            read_opt(arg, value)    # this is for value specified options (ie. /fill=15)
        else:    
            read_opt(arg, 1)     # this simply means the option is on/off (ie. /checkdpn)
    return args
 
def check_mapall_running():
    mapall = os.popen("ps -ef | grep -v grep | grep mapall").readlines()
    return len(mapall) > 0
    
def get_storage_node_ip(node=0):
    addresses = os.popen("nodedb print | grep -A 2 storage | grep address").readlines()

    if len(addresses) == 0: # singlenode
        return re.search("value=\"(\S+)\"", os.popen("nodedb print | grep address").readlines()[node]).group(1)
    else:
        return re.search("value=\"(\S+)\"", addresses[node]).group(1)

def get_clients_count(node=0):
    maplts_output = os.popen("maplts --probedir=/home/admin/lts --noerror --quiet /bin/hostname").readlines()
    client_hostnames = []
    for line in maplts_output:
        # trim out the unresponsive nodes
        a = re.compile("(?!.*not responding, removing from list.*$)")
        regex = a.match(line)
        
        # if the regex is not empty then add to list of hostnames
        if regex is not None :
            client_hostnames.append(regex.string) 
            
    print "client count (with unresponsive nodes trimmed) : " + str(len(client_hostnames))
    return len(client_hostnames)
    
def get_hfscheck_stripes_completed():
    if check_mapall_running():
        time.sleep(5)
        
    stripes = os.popen("avmaint hfscheckstatus | grep stripes-completed").read()
    count = re.search("stripes-completed=\"(\d+)\"", stripes).group(1)
    return count
   
def get_stripe_count(node=""):
    #stripes = Popen("avmaint ping --xmlperline=5 |  egrep \"<nodelist|<stripeinfo\" | egrep -v \"stripe(.*)ONLINE|/nodelist\"", shell=True, stdout=PIPE,stderr=PIPE).stdout.readlines()
    stripes = ""
    
    if node:
        stripes = Popen("avmaint ping --xmlperline=5 |  egrep \"<nodelist|<stripeinfo\" | egrep -v \"stripe(.*)ONLINE|/nodelist\" | grep " + node, shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
        
    else:
        stripes = Popen("avmaint ping --xmlperline=5 |  egrep \"<nodelist|<stripeinfo\" | egrep -v \"stripe(.*)ONLINE|/nodelist\"", shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
        
    count = 0
    stripe_counts = re.findall("count=\"(\d+)\"", stripes)
    for stripe_count in stripe_counts:
        #if not re.search("DEAD|OFFLINE", stripe):
        count += int(stripe_count)
    return count

def get_data_stripe_count():
    #stripes = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"data\\\"|dat\\\"\"", shell=True, stdout=PIPE).stdout.readlines()
    stripes = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"data\\\"|dat\\\"\"", shell=True, stdout=PIPE).communicate()[0]
    count = 0
    stripe_counts = re.findall("count=\"(\d+)\"", stripes)
    for stripe_count in stripe_counts:
        count += int(stripe_count)
    return count

def get_comp_data_stripe_count():
    #stripes = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"comp\\\"|\\\"wcmp\\\"\"", shell=True, stdout=PIPE).stdout.readlines()
    stripes = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"comp\\\"|\\\"wcmp\\\"\"", shell=True, stdout=PIPE).communicate()[0]
    count = 0
    stripe_counts = re.findall("count=\"(\d+)\"", stripes)
    for stripe_count in stripe_counts:
        count += int(stripe_count)
    
    return count

def get_parity_stripe_count():
    #stripes = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"par\\\"|\\\"lpar\\\"\"", shell=True, stdout=PIPE).stdout.readlines()
    stripes = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"par\\\"|\\\"lpar\\\"\"", shell=True, stdout=PIPE).communicate()[0]
    count = 0
    stripe_counts = re.findall("count=\"(\d+)\"", stripes)
    for stripe_count in stripe_counts:
        count += int(stripe_count)
    return count

def get_index_stripe_count():
    #stripes = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"indx|inx\\\"\"", shell=True, stdout=PIPE).stdout.readlines()
    stripes = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"indx|inx\\\"\"", shell=True, stdout=PIPE).communicate()[0]
    count = 0
    stripe_counts = re.findall("count=\"(\d+)\"", stripes)
    for stripe_count in stripe_counts:
        count += int(stripe_count)
    return count
                    
# returns count of all stripes in one array [index, composite data, parity, atomic data]
def get_all_stripe_count():
    #lines = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"data\\\"|dat\\\"|\\\"comp\\\"|\\\"wcmp\\\"|\\\"lpar\\\"|\\\"indx|inx\\\"\"", shell=True, stdout=PIPE).stdout.read()
    lines = Popen("avmaint perf status --ava | egrep -A 1 \"\\\"data\\\"|dat\\\"|\\\"comp\\\"|\\\"wcmp\\\"|\\\"lpar\\\"|\\\"indx|inx\\\"\"", shell=True, stdout=PIPE).communicate()[0]
    index_count = 0
    parity_count = 0
    data_count = 0
    comp_count = 0
    
    for count in re.findall("name=\"[indx|uinx|winx]+\"\s+count=\"(\S+)\"", lines):
        index_count += int(count)
        
    for count in re.findall("name=\"[comp|wcmp]+\"\s+count=\"(\S+)\"", lines):
        comp_count += int(count)
        
    for count in re.findall("name=\"[lpar]+\"\s+count=\"(\S+)\"", lines):
        parity_count += int(count)
    
    for count in re.findall("name=\"[data|udat|wdat]+\"\s+count=\"(\S+)\"", lines):
        data_count += int(count)
        
    return [index_count, comp_count, parity_count, data_count]

def get_num_of_nodes():
    length = len(Popen("avmaint ping --xmlperline=5 |  egrep \"<nodelist|<stripeinfo\" | egrep -v \"stripe(.*)ONLINE|/nodelist\" | grep ONLINE", shell=True, stdout=PIPE, stderr=PIPE).stdout.readlines())
    
    retry = 0
    while length == 0 and retry <= 5:
        length = len(Popen("avmaint ping --xmlperline=5 |  egrep \"<nodelist|<stripeinfo\" | egrep -v \"stripe(.*)ONLINE|/nodelist\" | grep ONLINE", shell=True, stdout=PIPE, stderr=PIPE).stdout.readlines())
        retry += 1
    return length

# total space used in GB
def get_gsan_usage(decom=""):
    if check_mapall_running():
        time.sleep(5)
        
    TWOPLACES = Decimal(10) ** -2
    gsan_usage = Decimal(0)
    lines = []
    if not decom:
        #lines = Popen("mapall ./cps | grep cur| awk '{print $1}'", shell=True, stdout=PIPE,stderr=STDOUT).stdout.readlines()
        lines = Popen("mapall ./cps | grep cur[^.] | awk '{print $1}'", shell=True, stdout=PIPE, stderr=STDOUT).communicate()[0]
        
    else:
        nodes = Popen("avmaint ping --xmlperline=5 |  egrep \"<nodelist|<stripeinfo\" | egrep -v \"stripe(.*)ONLINE|/nodelist\"", shell=True, stdout=PIPE, stderr=PIPE).stdout.readlines()
        nodelist = ""
        for node in nodes:
            if not re.search("DEAD|OFFLINE|stripe", node) and re.search("nodelist id", node):
                id = re.search("id=\"(\S+)\"", node).group(1)
                nodelist += id + ","
            
        #lines = Popen("mapall --nodes=%s ./cps | grep cur | awk '{print $1}'" % nodelist, shell=True, stdout=PIPE,stderr=STDOUT).stdout.readlines()
        lines = Popen("mapall --nodes=%s ./cps | grep cur[^.] | awk '{print $1}'" % nodelist, shell=True, stdout=PIPE, stderr=STDOUT).communicate()[0]
    
    #for line in lines:
    #    if re.search("ERR|No such file", line):
    #        gsan_usage = Decimal(0)
    #        line = 0
    #        break
    
    #    if not re.search("ssh", line):
    #        gsan_usage += Decimal(line)
        
    usages = re.findall("\\\n(\d+\.\d+)", lines)
    for usage in usages:
        gsan_usage += Decimal(usage)
        
    return "%s" % gsan_usage.quantize(TWOPLACES).to_eng_string()
    
# total available space in TB
def get_total_storage():
    if check_mapall_running():
        time.sleep(5)
        
    TWOPLACES = Decimal(10) ** -2
    total_storage = Decimal(0)
    #lines = Popen("mapall ./cps | grep 'blocks on node' | awk '{print $1}'", shell=True, stdout=PIPE,stderr=STDOUT).stdout.readlines()
    lines = Popen("mapall ./cps | grep 'blocks on node' | awk '{print $1}'", shell=True, stdout=PIPE, stderr=STDOUT).communicate()[0]
    #for line in lines:
    #    if re.search("ERR|No such file", line):
    #        total_storage = Decimal(0)
    #        line = 0
    #        break
        
    #    if not re.search("ssh", line):
    #        total_storage += Decimal(line)
    
    usages = re.findall("\\\n(\d+\.\d+)", lines)
    for usage in usages:
        total_storage += Decimal(usage)
        
    total_storage /= Decimal(1024)
    
    return "%s" % total_storage.quantize(TWOPLACES).to_eng_string()

def get_luns_size():
    #lunsObj = Popen("mapall --nodes=0.0 ls / | grep data", shell=True, stdout=PIPE,stderr=PIPE)
    #if isTimedOut(lunsObj):
    #    return 0
    #length = len(lunsObj.stdout.readlines())
    #count = Popen("avmaint nodelist --ava | grep \"disks count\"", shell=True, stdout=PIPE,stderr=PIPE).stdout.readlines()[0]
    count = Popen("avmaint nodelist --ava | grep \"disks count\"", shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
    length = int(re.search("count=\"(\d+)\"", count).group(1))
    return length

def get_cpu_core_size():
    if check_mapall_running():
        time.sleep(5)
        
    #cpu_sizeObj= Popen("mapall --nodes=0.0 \"cat /proc/cpuinfo\" | grep processor", shell=True, stdout=PIPE,stderr=PIPE)
    #cpu_sizeObj= Popen("mapall --nodes=0.0 \"cat /proc/cpuinfo\" | grep processor", shell=True, stdout=PIPE,stderr=PIPE).communicate()[0]
    cpu_sizeObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"cat /proc/cpuinfo\" 2>> /home/admin/ssh_debug.log | grep processor", shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
    #if isTimedOut(cpu_sizeObj):
    #    return 0
    length = len(re.findall("processor", cpu_sizeObj))
    return length

def get_cpu_info():
    if check_mapall_running():
        time.sleep(5)
        
    #modelObj = Popen("mapall --nodes=0.0 \"cat /proc/cpuinfo\" | egrep \"model name\" | awk '{print $4, $5, $6, $7, $8, $9}'", shell=True, stdout=PIPE)
    modelObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"cat /proc/cpuinfo\" 2>> /home/admin/ssh_debug.log | egrep \"model name\" | awk '{print $4, $5, $6, $7, $8, $9}'", shell=True, stdout=PIPE).communicate()[0]
    #model_numberObj = Popen("mapall --nodes=0.0 \"cat /proc/cpuinfo\" | egrep \"model\" | awk '{print $3}'", shell=True, stdout=PIPE)
    model_numberObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"cat /proc/cpuinfo\" 2>> /home/admin/ssh_debug.log | egrep \"model\" | awk '{print $3}'", shell=True, stdout=PIPE).communicate()[0]
    #cache_sizeObj = Popen("mapall --nodes=0.0 \"cat /proc/cpuinfo\" | egrep \"cache size\" | awk '{print $4}'", shell=True, stdout=PIPE)
    cache_sizeObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"cat /proc/cpuinfo\" 2>> /home/admin/ssh_debug.log | egrep \"cache size\" | awk '{print $4}'", shell=True, stdout=PIPE).communicate()[0]
    #steppingObj = Popen("mapall --nodes=0.0 \"cat /proc/cpuinfo\" | egrep \"stepping\" | awk '{print $3}'", shell=True, stdout=PIPE)
    steppingObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"cat /proc/cpuinfo\" 2>> /home/admin/ssh_debug.log | egrep \"stepping\" | awk '{print $3}'", shell=True, stdout=PIPE).communicate()[0]
    
    #if isTimedOut(modelObj) or isTimedOut(model_numberObj) or isTimedOut(cache_sizeObj) or isTimedOut(steppingObj):
    #    return "N/A"
    #else:
    modelStr = modelObj.split("\n")[0]
    model_numberStr = model_numberObj.split("\n")[0]
    cache_sizeStr = cache_sizeObj.split("\n")[0]
    steppingStr = steppingObj.split("\n")[0]
        
    return modelStr + ", Model-" + model_numberStr + " Stepping-" + steppingStr + ", Cache-" + cache_sizeStr + "KB"
    
def get_mem_info():
    if check_mapall_running():
        time.sleep(5)
        
    #memObj = Popen("mapall --nodes=0.0 \"cat /proc/meminfo\" | grep MemTotal | awk '{print $2}'", shell=True, stdout=PIPE,stderr=PIPE)
    memObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"cat /proc/meminfo\" 2>> /home/admin/ssh_debug.log | grep MemTotal | awk '{print $2}'", shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
    #if isTimedOut(memObj):
    #    return "N/A"
    memStr = memObj.strip()
    return "%s" % memStr

def get_raid_level():
    if check_mapall_running():
        time.sleep(5)
        
    if re.search("no", Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"which %s\"" % getomreport(), shell=True, stdout=PIPE, stderr=PIPE).communicate()[1]):
        return "No_%s" % getomreport()
    else:
        #raidObj = Popen("mapall --nodes=0.0 \"%s storage vdisk controller=0\" | grep Layout  | awk '{print $3}'" % getomreport(), shell=True, stdout=PIPE,stderr=PIPE)
        raidObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s storage vdisk controller=0\" 2>> /home/admin/ssh_debug.log | grep Layout  | awk '{print $3}'" % getomreport(), shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
        #if isTimedOut(raidObj):
        #    return "N/A"
        raidStr = raidObj.split("\n")[0]
    return raidStr

def get_read_ahead():
    if check_mapall_running():
        time.sleep(5)
        
    #powerpath = Popen("mapall --nodes=0.0 df", shell=True, stdout=PIPE, stderr=PIPE).stdout.read()
    powerpath = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " df", shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
    if re.search("power", powerpath):
        #readaheadObj = Popen("mapall --nodes=0.0 --user=root \"blockdev -v --getra /dev/emcpower??\" | grep read | awk '{print$3}'", shell=True, stdout=PIPE,stderr=PIPE)
        readaheadObj = Popen(ssh_cmd + " root@" + get_storage_node_ip(0) + " \"blockdev -v --getra /dev/emcpower??\" 2>> /home/admin/ssh_debug.log | grep read | awk '{print$3}'", shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
        #if isTimedOut(readaheadObj):
        #    return 0
        #readaheadStr = readaheadObj.stdout.readlines()[0]
        
    else:
        #partition = Popen("mapall --nodes=0.0 \"df\" | grep data01 | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE).stdout.read().rstrip()
        partition = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"df\" | grep data01 | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE).communicate()[0].rstrip()
        #readaheadObj = Popen("mapall --nodes=0.0 --user=root \"blockdev -v --getra\" %s | grep read | awk '{print$3}'" % partition, shell=True, stdout=PIPE,stderr=PIPE)
        readaheadObj = Popen(ssh_cmd + " root@" + get_storage_node_ip(0) + " \"blockdev -v --getra\" %s 2>> /home/admin/ssh_debug.log | grep read | awk '{print$3}'" % partition, shell=True, stdout=PIPE, stderr=PIPE).communicate()[0]
        #if isTimedOut(readaheadObj):
        #    return 0
        #readaheadStr = readaheadObj..read()
    return readaheadObj.rstrip()

def get_RAIN():
    if get_num_of_nodes() == 1:
        return "Axion-E"
    
    #rainObj = Popen("avmaint config --ava | grep nearparity", shell=True, stdout=PIPE)
    rainObj = Popen("avmaint config --ava | grep nearparity", shell=True, stdout=PIPE).communicate()[0]
    #if isTimedOut(rainObj):
    #    return "N/A"
    #rainStr = rainObj.stdout.read()
    if re.search("0", rainObj):
        return "Non-RAIN"
    else:
        return "RAIN"

# GB license size
def get_partition_total_size():
    df = Popen("mapall --nodes=0.0 df | grep data | awk '{print $2}'", shell=True, stdout=PIPE, stderr=PIPE).stdout.readlines()
    total_size = 0
    for line in df:
        total_size += int(line)
    total_size = total_size / (1024 * 1024)
    return str(total_size)

def get_gsan_usable_size():
    TWOPLACES = Decimal(10) ** -2
    return (Decimal(get_partition_total_size()) * Decimal('.65')).quantize(TWOPLACES).to_eng_string()
    
def get_drive_type():
    if check_mapall_running():
        time.sleep(5)
        
    if re.search("no", Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"which %s\"" % getomreport(), shell=True, stdout=PIPE, stderr=PIPE).communicate()[1]):
        return "No_%s" % getomreport()
    else:
        #version = Popen("mapall --nodes=0.0 \"%s about\" | grep Version | awk '{print $3}'" % getomreport(), shell=True, stdout=PIPE, stderr=PIPE).stdout.read().rstrip()
        version = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s about\" 2>> /home/admin/ssh_debug.log | grep Version | awk '{print $3}'" % getomreport(), shell=True, stdout=PIPE, stderr=PIPE).communicate()[0].rstrip()
        driveObj = None
        if version > "6.0.0":
            #driveObj = Popen("mapall --nodes=0.0 \"%s storage pdisk controller=0\" | grep Bus | awk '{print $4}'" % getomreport(), shell=True, stdout=PIPE)
            driveObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s storage pdisk controller=0\" 2>> /home/admin/ssh_debug.log | grep Bus | awk '{print $4}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
            
        else:
            #driveObj = Popen("mapall --nodes=0.0 \"%s storage pdisk controller=0\" | grep Type | awk '{print $3}'" % getomreport(), shell=True, stdout=PIPE)
            driveObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s storage pdisk controller=0\" 2>> /home/admin/ssh_debug.log | grep Type | awk '{print $3}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
            
        #if isTimedOut(driveObj):
        #    return "N/A"
        driveStr = driveObj.split("\n")[0]
        return driveStr

def get_perc_controller():
#    if re.search("no", Popen("mapall --nodes=0.0 which %s" % getomreport(), shell=True, stdout=PIPE,stderr=PIPE).stderr.read()):
#        return "No_%s" % getomreport()
#    else:
#        perc = subproc.Subprocess("mapall --quiet --nodes=0.0 %s storage controller | grep Name" % getomreport())
#        if perc.wait(60):
#            output = perc.readPendingLine()
#            if output == '':
#                return 'N/A'    # if we hit this, mapall zombied
#            perc = Popen("echo %s | awk '{print $3, $4, $5}'" % output, shell=True, stdout=PIPE).stdout.read().strip()
#            
#        else: 
#            return 'N/A'
#        
#        version = subproc.Subprocess("mapall --quiet --nodes=0.0 %s storage controller | grep \"Firmware Version\"" % getomreport()).readlineErr().rstrip()
#        if version.wait(60):
#            output = version.readPendingLine()
#            if version == '':
#                return 'N/A'    # if we hit this, mapall zombied
#            version = Popen("echo %s | awk '{print $4}'" % output, shell=True, stdout=PIPE).stdout.read().strip()
#
#        else: 
#            return 'N/A'
        if check_mapall_running():
            time.sleep(5)
        
        #percObj = Popen("mapall --nodes=0.0 \"%s storage controller\" | grep Name | awk '{print $3, $4, $5}'" % getomreport(),shell=True, stdout=PIPE)
        percObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s storage controller\" 2>> /home/admin/ssh_debug.log | grep Name | awk '{print $3, $4, $5}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
        #if isTimedOut(percObj):
        #    return "N/A"
        percStr = percObj.rstrip()
        
        #versionObj = Popen("mapall --nodes=0.0 \"%s storage controller\" | grep \"Firmware Version\" | awk '{print $4}'" % getomreport(), shell=True, stdout=PIPE)
        versionObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s storage controller\" 2>> /home/admin/ssh_debug.log | grep \"Firmware Version\" | awk '{print $4}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
        #if isTimedOut(versionObj):
        #    return "N/A"
        versionStr = versionObj.split("\n")[0].rstrip()
        
        return percStr + " " + versionStr
    
def get_kernel_info():
    if check_mapall_running():
        time.sleep(5)
        
    kernelObj = Popen("ssh -x " + get_storage_node_ip(0) + " \"uname -a\" 2>> /home/admin/ssh_debug.log | awk '{print $3}'", shell=True, stdout=PIPE).communicate()[0].strip()
 
    kernelStr = kernelObj.rstrip()
    
    #redhatObj = Popen("mapall --nodes=0.0 \"cat /etc/redhat-release\"", shell=True, stdout=PIPE)
    rhOs = len(os.popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"ls / | grep rhel\"").readlines())
    slesOs = len(os.popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"ls / | grep sles\"").readlines())
    osObj = 0
    osStr = ""
    
    if rhOs:
        osObj = Popen("ssh -x " + get_storage_node_ip(0) + " \"cat /etc/redhat-release\" 2>> /home/admin/ssh_debug.log", shell=True, stdout=PIPE).communicate()[0]
        osStr = osObj.split("\n")[0]
        
    elif slesOs:
        osObj = Popen("ssh -x " + get_storage_node_ip(0) + " \"cat /etc/SuSE-release\" 2>> /home/admin/ssh_debug.log", shell=True, stdout=PIPE).communicate()[0]
        osStr = osObj.split("\n")[0]
        

    return osStr + " " + kernelStr
    
    return "N/A"

def get_server_model():
    if check_mapall_running():
        time.sleep(5)
        
    if re.search("no", Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"which %s\"" % getomreport(), shell=True, stdout=PIPE, stderr=PIPE).communicate()[1]):
        return "N/A"
    else:
        serverObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s system summary\" 2>> /home/admin/ssh_debug.log | grep \"Chassis Model\" | awk '{print $4, $5}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
        #if isTimedOut(serverObj):
        #    return "N/A"
        serverStr = serverObj.rstrip()
    return serverStr 

def get_uptime():
    if check_mapall_running():
        time.sleep(5)
        
    return Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"uptime\" 2>> /home/admin/ssh_debug.log | awk '{print $3, $4}' ", shell=True, stdout=PIPE).communicate()[0].strip()

def get_bios_version():
    if check_mapall_running():
        time.sleep(5)
        
    if re.search("no", Popen(ssh_cmd + " "+ get_storage_node_ip(0) + " \"which %s\"" % getomreport(), shell=True, stdout=PIPE, stderr=PIPE).communicate()[1]):
        return "N/A"
    else:
       #manufacturerObj = Popen("mapall --nodes=0.0 \"%s system summary\" | grep Manufacturer | awk '{print $3, $4}'" % getomreport(), shell=True, stdout=PIPE)
       manufacturerObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s system summary\" 2>> /home/admin/ssh_debug.log | grep Manufacturer | awk '{print $3, $4}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
       #if isTimedOut(manufacturerObj):
       #    return "N/A"
       manufacturerStr = manufacturerObj.rstrip()
       #versionObj = Popen("mapall --nodes=0.0 \"%s system summary\" | grep Version | awk '{print $3, $4}'" % getomreport(), shell=True, stdout=PIPE)
       versionObj = Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s system summary\" 2>> /home/admin/ssh_debug.log | grep Version | awk '{print $3, $4}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
       #if isTimedOut(versionObj):
       #    return "N/A"
       versionStr = versionObj.split("\n")[3]
       return manufacturerStr + " " + versionStr
   
def get_encrypt_at_rest():
    encryptatrestObj = 0
    if getDPNVersion() <= "5.0.0":
        encryptatrestObj = Popen("avmaint nodelist | grep restsalt", shell=True, stdout=PIPE)
        if isTimedOut(encryptatrestObj):
            return "N/A"
        encryptatrestStr = encryptatrestObj.communicate()[0]
        if re.search("\d+", encryptatrestStr):
            return "On"
        else:
            return "Off"
    
    elif getDPNVersion() >= "6.0.0":
        encryptatrestObj = Popen("avmaint nodelist | grep encryptatrest", shell=True, stdout=PIPE)
        encryptatrestStr = encryptatrestObj.communicate()[0]
        
        if isTimedOut(encryptatrestObj):
            return "N/A"
        
        if re.search("true", encryptatrestStr):
            return "On"
        else:
            return "Off"

def get_drive_model_revision():
    if check_mapall_running():
        time.sleep(5)
        
    if re.search("no", Popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"which %s\"" % getomreport(), shell=True, stdout=PIPE, stderr=PIPE).communicate()[1]):
        return "N/A"
    else:
       #driveObj = Popen("mapall --nodes=0.0 \"%s storage pdisk controller=0\" | grep Product | awk '{print $4,$5}'" % getomreport(), shell=True, stdout=PIPE)
       #driveObj = Popen("mapall --nodes=0.0 \"%s storage pdisk controller=0\" | grep Product | awk '{print $4,$5}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
       driveObj = os.popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s storage pdisk controller=0\" 2>> /home/admin/ssh_debug.log | grep Product | awk '{print $4,$5}'" % getomreport()).read()
              #if isTimedOut(driveObj):
       #    return "N/A"
       #revisionObj = Popen("mapall --nodes=0.0 \"%s storage pdisk controller=0\" | grep Revision | awk '{print $3}'" % getomreport(), shell=True, stdout=PIPE)
       #revisionObj = Popen("mapall --nodes=0.0 \"%s storage pdisk controller=0\" | grep Revision | awk '{print $3}'" % getomreport(), shell=True, stdout=PIPE).communicate()[0]
       revisionObj = os.popen(ssh_cmd + " " + get_storage_node_ip(0) + " \"%s storage pdisk controller=0\" 2>> /home/admin/ssh_debug.log | grep Revision | awk '{print $3}'" % getomreport()).read()
       #if isTimedOut(revisionObj):
       #    return "N/A"
       
       return driveObj.split("\n")[0].rstrip() + ", " + revisionObj.split("\n")[0].rstrip()
    
def getDPNVersion(hostname=socket.gethostname()):
    version = ""
    p = Popen(ssh_cmd + " admin@" + hostname + " rpm -qa | grep dpn", shell=True, close_fds=True,
              stdin=PIPE, stdout=PIPE, stderr=PIPE)
    for line in p.communicate()[0].split("\n"):
        if re.search("dpnserver", line):
            version = line[10:].strip()
    return version

def getomreport():
    if getDPNVersion() < "9.0.0.0":
        return "omreport"
    else:
        return "avsysreport"

def get_qa_url(short_hostname=False):
    short_name = re.compile("\s*([^.]+)\.?")
    try:
        global_config = imp.load_source("global_config", "/qadepot/qts/global_config.py")
        # This should return either "qahome.asl.lab.emc.com" or "duhome.asl.lab.emc.com"
        name = global_config.qadb 
    except:
        # If the file does not exist, is not readable, or the attribute does not exist
        # Attempt to get the domain name from the bash envrionment variables
        # or return this default value
        name = os.environ.get("QADB", "qahome.avamar.com")
    return short_name.match(name).group(1) if short_hostname else name 

# if any polling command (particularly mapall) takes longer than timeout (default 60 seconds), return false (N/A)
def isTimedOut(popenObject, timeout=60):
    timer = 0
    while popenObject.poll() == None:
        time.sleep(1)
        timer += 1
        if timer >= timeout:
            return True
    return False
        
if __name__ == "__main__":
    print get_run_id("/");



class LogScanner(threading.Thread):
    def __init__(self, kwords, targets, signal=19, mode='default'):
        self._stopevent = threading.Event()
        self._sleepperiod = 1.0
        threading.Thread.__init__(self, name="LogScannerThread")
        self.kwords = kwords
        self.orgTargets = targets
        self.targets = []
        self.sizes = []
        self.signal = signal;
        self.mode = mode
        self.stopScan = False
        for target in self.orgTargets:
            if os.path.isfile(target):
                self.sizes.append(os.path.getsize(target))
                self.targets.append(target)
    def run (self):
        self.start_logscan()
    def stop(self):
        self.stopScan = True
    def start_logscan(self):       
        while not self.stopScan:
            return_array = self.log_scan()
            if len(return_array) == 2:
                print "Keyword(s) found."
                processID = os.getpid()
                #print processID
                f = open("/home/admin/.%d_lg" % processID, "w")
                f.write("%s found in %s \n" % (return_array[0], return_array[1]));
                if(globalPID != 0):
                    print " Freezing PID : %s since keyword %s found in %s" % (globalPID, return_array[0], return_array[1])
                    os.kill(globalPID, self.signal)    
                    sizes = []
                    sizes = return_array  
                else:                          
                    sys.exit(1)
            else:
                time.sleep(1)
    def log_scan(self):
        filesizes = []
        counter = 0
        found = []
        for target in self.targets:
            self.sizes[counter] += 0
            log = open(target, "r")
            log.seek(self.sizes[counter])
            temp_file_size = os.path.getsize(target)
            for line in log.readlines():
                #print line
                for keyword in self.kwords:
                    #insert regex here
                    m = re.search(keyword, line)
                    if(m):
                        if self.mode == 'default':                    
                            found = [keyword, target]
                        else:
                            sys.stdout.write("[" + format_time() + "] " + line)            
            self.sizes[counter] = temp_file_size
            log.close()
            counter += 1
        return found         
    

### scanLog(keywords, logFiles, 'freeze', 'default'): 
### default mode: scan the log files list for keywords and freeze the main process if found
### non-default mode: scan the log files list for keywords and write to stdout if found. 
###                   Used to print certain progress messages from the log file.
### action=freeze,terminate
### the function will return the Logscanner thread object that can be stop by objName.stop()
###

def scanLog(keywords, logFiles, action='freeze', mode='default'): 
    global globalPID

    globalPID = os.getpid();
    if mode == 'default':    
        print "global pid :%s" % globalPID

    if action == 'terminate':
        signal = 9
    else:
        signal = 19   
    myThread = LogScanner(keywords, logFiles, signal, mode)
    myThread.start()
    return myThread
