#!/usr/bin/env python26

import re
import os
import shlex
import sqlite3
import socket
import time
import fcntl
import consts
import subprocess
import json

tokenize = re.compile(r'(\d+)|(\D+)').findall
def natural_sortkey(string):
    return tuple(int(num) if num else alpha for num, alpha in tokenize(string))

def setup_sqlite_lib():
    ld_path = '/opt/sqlite3/lib/'
    if os.environ.has_key('LD_LIBRARY_PATH'):
        os.environ['LD_LIBRARY_PATH'] = "%s:%s" %(ld_path, os.environ['LD_LIBRARY_PATH'])
    else:
        os.environ['LD_LIBRARY_PATH'] = ld_path

def getcommandoutput(cmd, queue=None):
    """Return (status, output) of executing cmd in a shell."""
    """Add the process object to the queue"""
    import subprocess
    cmd = str(cmd)
    args = shlex.split(cmd)
    p = subprocess.Popen(args, shell=False, universal_newlines=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if queue != None:
        queue.put(p)

    output = str.join("", p.stdout.readlines())
    sts = p.wait()
    if queue != None:
        queue.queue.remove(p)

    if sts is None:
        sts = 0
    return sts, output

def get_checkpoints_frombackup(backup_filepath):
    db = sqlite3.connect(backup_filepath)
    cursor = db.execute('select cpoint_id from cpoint_state')
    cpoint_list = map(lambda x: x[0], cursor.fetchall())
    return sorted(cpoint_list)

def create_split_db(db_file_name, max_db_size):
    db = None
    max_db_size = max_db_size * 1024 * 1024 # Convert MB to bytes

    try:
        db = sqlite3.connect(db_file_name)
        db.text_factory = str
        db.executescript("""
        BEGIN;
        CREATE TABLE cpoint_op
        (vbucket_id integer, cpoint_id integer, seq integer, op text,
        key varchar(250), flg integer, exp integer, cas integer, cksum integer, val blob);
        CREATE TABLE cpoint_state
        (vbucket_id integer, cpoint_id integer, prev_cpoint_id integer, state varchar(1),
        source varchar(250), updated_at text);
        COMMIT;
        """)
        db_page_size = db.execute("pragma page_size").fetchone()[0]
        db_max_page_count = max_db_size / db_page_size
        db.execute("pragma max_page_count=%d" % (db_max_page_count))
    except Exception:
        return False

    return db

def copy_checkpoint_state_records(checkpoint_states, db):
    c = db.cursor()
    stmt = "INSERT OR IGNORE into cpoint_state" \
           "(vbucket_id, cpoint_id, prev_cpoint_id, state, source, updated_at)" \
           " VALUES (?, ?, ?, ?, ?, ?)"
    for cstate in checkpoint_states:
        c.execute(stmt, (cstate[0], cstate[1], cstate[2], cstate[3], cstate[4], cstate[5]))
    db.commit()
    c.close()

def copy_checkpoint_op_records(op_records, db):
    result = True
    c = db.cursor()
    stmt = "INSERT OR IGNORE into cpoint_op" \
           "(vbucket_id, cpoint_id, seq, op, key, flg, exp, cas, val)" \
           " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    try:
        for oprecord in op_records:
            c.execute(stmt, (oprecord[0], oprecord[1], oprecord[2], oprecord[3], oprecord[4],
                             oprecord[5], oprecord[6], oprecord[7], sqlite3.Binary(oprecord[8])))
    except sqlite3.Error:
        result = False
    if result == True:
        db.commit()
    c.close()
    return result

def gethostname():
    """
    Return hostname from hostname.va2.zynga.com
    """
    hostname = socket.gethostname().split('.')
    return hostname[0]

def backup_filename_to_epoch(filename):
    """
    Return epoch from filename-timestamp
    """

    dt = "-".join(os.path.basename(filename).split('-')[1:-1])
    return time.mktime(time.strptime(dt,'%Y-%m-%d_%H:%M:%S'))

def backup_files_filter(date, files):
    """
    Filter files list by comparing date < given data
    """
    r_list = []
    cmp_epoch = backup_filename_to_epoch("backup-%s_00:00:00-00000.mbb" %date)
    for f in files:
        s = os.path.basename(f)
        if '.split' in f:
            s = s.replace('.split', '-00000.mbb')

        epoch = backup_filename_to_epoch(s)

        if epoch < cmp_epoch:
            r_list.append(f)

    return r_list

def markBadDisk(disk_id):
    """
    Add the given disk into bad disk file
    The disk mapper can verify the disk and consider for swapping disk
    """

    return appendToFile_Locked(consts.BAD_DISK_FILE, ["data_%d" %disk_id])

def appendToFile_Locked(filename, data):
    """
    Append to a file after holding an flock
    Create the file if it does not exist
    """

    try:
        lockname = "%s.lock" %filename
        for fl in (lockname, filename):
            if not os.path.exists(fl):
                os.system("touch %s && chown storageserver.storageserver %s" %(fl, fl))

        lock = open(lockname, 'w')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        f = open(filename, 'aw')
        for d in data:
            f.write("%s\n" %d)
        os.system("chown storageserver.storageserver %s" %filename)
        f.close()
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
    except:
        return False

    return True

def zruntime_readkey(user, passwd, namespace, gameid, key):
    """
    Read a key from zRuntime
    """

    cmd = "curl --retry %d %s/%s/%s/current --insecure -u %s:%s" %(consts.ZRT_RETRIES, consts.ZRT_URL, gameid,
            namespace, user, passwd)

    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        d = p.communicate()[0]
        data = json.loads(d)

        if p.returncode == 0:
            if data['output'].has_key(key):
                return data['output'][key]
            else:
                return None
        else:
            print p.returncode
            return False
    except Exception, e:
        return False

def parse_backupname(filename):
    if filename.endswith(".mbb"):
        return "-".join(os.path.basename(filename).split('-')[:-1])
    else:
        return os.path.basename(filename).replace(".split", "")

def split_by_lines(data):
    d = data.split('\n')
    d = map(lambda x: x.strip(), d)
    d = filter(lambda x: x != "", d)
    return d

def is_location_empty(location):
    """
    Check if an s3 location is empty
    """

    ls_cmd = "%s ls s3://%s/" %(consts.PATH_S3CMD_EXEC, location)
    st, out = getcommandoutput(ls_cmd)
    if st > 0:
        return st, "FAILED: Execution %s" %ls_cmd

    files = filter(lambda x: x.strip() != '', out.split('\n'))
    if len(files) > 0:
        return len(files), "FAILED: Location %s is not empty"

    return 0, ""

def clear_location(location):
    """
    Remove contents of s3 location
    """

    del_cmd = "%s del s3://%s/" %(consts.PATH_S3CMD_EXEC, location)
    st, out = getcommandoutput(del_cmd)

    return st


