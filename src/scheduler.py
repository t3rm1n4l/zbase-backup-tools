#!/usr/bin/env python

"""
 Copyright 2012 Zynga
 Author: Sarath Lakshman
 Email: slakshman@zynga.com
 Description: Backup merge scheduler
"""

from subprocess import Popen, PIPE
from util import *
import time
import shlex
import datetime
import glob
import os
import consts

class MergeJob:
    """
    Backup merge job
    """

    DAILYJOB = 0
    MASTERJOB = 1

    def __init__(self, btype, location, date, logger):
        self.btype = btype
        self.logger = logger
        if location[-1] == '/':
            location = location[:-1]

        self.location = location
        self.date = date
        self.path = None
        self.process = None
        self.running = False

    def __eq__(self, obj):
        return obj.btype == self.btype and obj.location == self.location \
                and obj.date == self.date

    def getHost(self):
        """
        Return the hostname of the backups for the current merge job
        """
        return self.location.split('/')[-2]

    def getDisk(self):
        """
        Return the disk for the current merge job
        """
        return "/%s" %self.location.split('/')[1]

    def getCommand(self):
        """
        Return the command for merge
        """
        if self.btype == MergeJob.DAILYJOB:
            cmd = consts.PATH_DAILY_MERGE
        else:
            cmd = consts.PATH_MASTER_MERGE

        return shlex.split("%s -p %s -d %s" %(cmd, self.location, self.date))

    def markComplete(self):
        """
        Put .complete marker in the output directory
        Set the directory permissions to apache
        """

        if self.btype == MergeJob.DAILYJOB:
            self.path = os.path.join(self.location, consts.PERIODIC_DIRNAME, self.date)
        else:
            self.path = os.path.join(self.location, consts.MASTER_DIRNAME, self.date)

        try:
            if not os.path.exists(self.path):
                os.makedirs(self.path)
        except:
            self.logger.error("Unable to create directory, %s" %self.path)

        if os.system("touch %s" %os.path.join(self.path, ".complete")):
            self.logger.error("Unable to create .complete at %s" %self.path)

        if os.system("chown apache.apache -R %s" %self.path):
            self.logger.error("Unable to change permission to apache for location %s" %self.path)

    def markForCopy(self):
        """
        Add the files to be copied to secondary disk by marking the directory as dirty
        """
        dirtyfile = os.path.join(self.getDisk(), consts.DIRTY_DISK_FILE)
        if appendToFile_Locked(dirtyfile, "%s\n" %self.path):
            return True
        else:
            self.logger.error("Unable to mark %s to dirtyfile, %s" %(self.path, dirtyfile))
            return False

    def isRunning(self):
        return self.running

    def startExecution(self):
        """
        Execute backup merge job  - master merge or daily merge
        """
        self.running = True
        self.process = Popen(self.getCommand(), stdout=PIPE, stderr=PIPE, preexec_fn=os.setsid)

    def isProcessComplete(self):
        """
        Check if merge process is complete
        """
        if self.process.poll() is not None:
            self.running = False
            return True
        else:
            return False

    def getStatus(self):
        """
        Return status of merge job
        """
        if self.process:
            if self.isProcessComplete():
                if self.process.returncode == 0:
                    stext = "SUCCESS"
                else:
                    stext = "FAILED"
            else:
                stext = "RUNNING"
        else:
            stext = "NOT PROCESSED"

        return stext

    def postExecutionSteps(self):
        """
        Mark the job as complete
        If the job is successful, mark it as dirty
        """
        self.markComplete()
        if self.getStatus() == "SUCCESS":
            if os.path.exists(os.path.join(self.path, ".done")):
                self.markForCopy()


class BaseScheduler:
    """
    Base scheduler class
    """

    WAIT = 0
    SKIP = 1
    PROCEED = 2
    IGNORE = 3
    NOMEMORY = 4
    INTERVAL = 60

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.disks = []
        self.jobs = []
        self.current_execjobs = []
        self.type = "Base Scheduler" #To be implemented by derived class
        self.initialize()

    def initialize(self):
        raise NotImplementedError

    def getDisks(self):
        """
        Scan different partitions and identify valid primary directories
        """
        disks = glob.glob('/data_*')
        if os.path.exists(consts.BAD_DISK_FILE):
            f = open(consts.BAD_DISK_FILE)
            bad_disks = f.readlines()
            f.close()
            for d in disks[:]:
                for b in bad_disks:
                    if d in b:
                        disks.remove(d)
        return disks

    def getLocations(self):
        """
        Iterate though the directory tree and find out the jobs to be processed
        from the given list of disks
        """
        hosts = []
        disks = self.getDisks()
        for d in disks:
            st, out = getcommandoutput("find %s/primary -maxdepth 3 -mindepth 3 -type d" %d)
            if st == 0:
                for h in out.split():
                    hosts.append((d,h))

        return hosts

    def isDiskBusy(self, disk):
        """
        Check if the a disk is being used
        """
        if os.path.exists(os.path.join(disk, consts.DIRTY_DISK_FILE)):
            data = open(os.path.join(disk, consts.DIRTY_DISK_FILE), 'r').read().strip()
            if data != "":
                return True

        if os.system('ps -eo comm | grep "aria2c" | grep "%s" > /dev/null 2>&1' %disk) == 0:
            return True

        return False

    def waitForProcessSlot(self, completeAll=False):
        """
        Wait until atleast one jobslot is free
        """

        slotfree=False
        while True:
            for j in self.current_execjobs:
                if j.isProcessComplete():
                    j.postExecutionSteps()
                    self.logger.info("Completed execution of job [ DISK:%s HOST:%s STATUS:%s ]" %(j.getDisk(), j.getHost(), j.getStatus()))
                    self.current_execjobs.remove(j)
                    slotfree=True

            if not completeAll:
                if slotfree or len(self.current_execjobs)==0:
                    break
                else:
                    time.sleep(1)
            else:
                if len(self.current_execjobs):
                    time.sleep(1)
                else:
                    break

    def findJobs(self, date):
        """
        Find merge jobs to be queued for processing
        """
        raise NotImplementedError

    def canSchedule(self, job):
        """
        Check if given job can be scheduled
        """
        raise NotImplementedError

    def getFreeMemory(self):
        """
        Return current system free memory
        """
        mem = os.popen("free -m").readlines()[1].split()
        free = int(mem[3]) + int(mem[-1]) - len(self.current_execjobs)*consts.SPLIT_SIZE*2
        return free


    def execute(self, date):
        """
        Execute jobs batch by batch in parallel
        """

        ignore = False
        ret = True
        self.logger.info("==== Executing job processor for %s ====" %self.type)
        self.findJobs(date)
        if len(self.jobs):
            self.logger.info("Merge jobs to be processed: %s" %", ".join(["DISK:%s HOST:%s" %(x.getDisk(), x.getHost()) for x in self.jobs]))
        else:
            self.logger.info("No merge jobs found to be processed")
            ignore = True

        skipped = False

        while True:
            if len(self.jobs):
                job = self.jobs.pop()
                resp = self.canSchedule(job)
                if resp == BaseScheduler.PROCEED:
                    self.logger.info("Executing merge job [ DISK:%s HOST:%s ]" %(job.getDisk(), job.getHost()))
                    job.startExecution()
                    self.current_execjobs.append(job)
                elif resp == BaseScheduler.IGNORE:
                    self.jobs.insert(0, job)
                    time.sleep(1)
                elif resp == BaseScheduler.WAIT:
                    self.jobs.append(job)
                    self.waitForProcessSlot()
                elif resp == BaseScheduler.SKIP:
                    skipped = True
                    break
                elif resp == BaseScheduler.NOMEMORY:
                    self.logger.warning("Not enough free memory - Waiting for running job to free memory")
                    time.sleep(1)
                    self.jobs.append(job)
                    self.waitForProcessSlot()
            else:
                break

        self.waitForProcessSlot(True)

        if skipped == True:
            ret = False
            self.logger.info("Pre-emiting merge job processor")
            self.logger.info("Remaining jobs to be processed: %s" %", ".join(["DISK:%s HOST:%s" %(x.getDisk(), x.getHost()) for x in self.jobs]))
        elif not ignore:
            self.logger.info("Completed all %s jobs for the date:%s" %(self.type, date))

        self.logger.info("==== Completed executing job processor for %s ====" %self.type)

        return ret

class DailyMergeScheduler(BaseScheduler):

    def __init__(self, config, logger):
        BaseScheduler.__init__(self, config, logger)

        self.type = "Daily Merge Scheduler"

    def initialize(self):
        self.logger.info("Initializing Daily Merge Scheduler")

    def findJobs(self, date):
        for d,h in self.getLocations():
            path = os.path.join(h, consts.PERIODIC_DIRNAME, date)
            addhost = False
            if os.path.exists(path):
                if not os.path.exists(os.path.join(path, ".complete")):
                    addhost = True
            else:
                addhost = True

            if addhost:
                job = MergeJob(MergeJob.DAILYJOB, h, date, self.logger)
                if job not in self.current_execjobs:
                    if self.isDiskBusy(d):
                        self.jobs.insert(0, job)
                    else:
                        self.jobs.append(job)

    def canSchedule(self, job):

        if self.getFreeMemory() < self.config.daily_mem_threshold:
            return BaseScheduler.NOMEMORY

        if len(self.current_execjobs) < self.config.parallel_daily_jobs:
            if self.isDiskBusy(job.getDisk()):
                return BaseScheduler.IGNORE
            else:
                return BaseScheduler.PROCEED
        else:
            return BaseScheduler.WAIT


class MasterMergeScheduler(BaseScheduler):

    def __init__(self, config, logger):
        BaseScheduler.__init__(self, config, logger)

        self.type = "Master Merge Scheduler"

    def initialize(self):
        self.logger.info("Initializing Master Merge Scheduler")
        self.startdate = datetime.date.today()

    def findJobs(self, date):
        for d,h in self.getLocations():
            path = os.path.join(h, consts.MASTER_DIRNAME, date)
            addhost = False
            if os.path.exists(path):
                if not os.path.exists(os.path.join(path, ".complete")):
                    addhost = True
            else:
                addhost = True

            if addhost:
                job = MergeJob(MergeJob.MASTERJOB, h, date, self.logger)
                if job not in self.current_execjobs:
                    if self.isDiskBusy(d):
                        self.jobs.insert(0, job)
                    else:
                        self.jobs.append(job)

    def canSchedule(self, job):

        if self.getFreeMemory() < self.config.master_mem_threshold:
            return BaseScheduler.NOMEMORY

        if self.startdate != datetime.date.today():
            return BaseScheduler.SKIP

        if len(self.current_execjobs) < self.config.parallel_master_jobs:
            if self.isDiskBusy(job.getDisk()):
                return BaseScheduler.IGNORE
            else:
                return BaseScheduler.PROCEED
        else:
            return BaseScheduler.WAIT

