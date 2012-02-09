#!/usr/bin/env python26
#Description: Constants definitions

SYSLOG_TAG = 'membase-backup'
MBRESTORE_PID_FILE = '/var/run/mbrestore.pid'
MBBACKUP_PID_FILE = '/var/run/mbbackup.pid'
MBMERGE_PID_FILE = '/var/run/mbmerge.pid'
BLOBRESTORED_PID_FILE = '/var/run/blobrestored.pid'
MEMCACHED_PID_FILE = '/var/run/memcached/memcached.pid'
CONFIG_FILE = '/etc/membase-backup/default.ini'
MEMCACHED_SYSCONFIG_FILE = '/etc/sysconfig/memcached'
LAST_CHECKPOINT_FILE = '/db/last_closed_checkpoint'
BACKUP_TAPNAME = 'backup'
REPLICATION_TAPNAME = 'replication'
PATH_MBBACKUP_EXEC = '/opt/membase/lib/python/mbbackup-incremental'
PATH_S3CMD_EXEC = '/opt/membase/membase-backup/zstore_cmd'
PATH_S3CMD_ZYNGA_EXEC = '/usr/bin/s3cmd_zynga'
PATH_S3CMD_CONFIG = '/etc/membase-backup/s3cmd.cfg'
INCR_DIRNAME = 'incremental'
MASTER_DIRNAME = 'master'
PERIODIC_DIRNAME = 'daily'
MAX_BACKUP_SEARCH_TRIES = 4
PATH_MBRESTORE_EXEC = '/opt/membase/lib/python/mbadm-online-restore'
PATH_MBTAP_REGISTER_EXEC = '/opt/membase/lib/python/mbadm-tap-registration'
PATH_MBMERGE_EXEC = '/opt/membase/lib/python/mbbackup-merge-incremental'
S3_BUCKET = 'membase-backup'
DEFAULT_LOGLEVEL = 'INFO'
MERGE_CMD = "/opt/membase/membase-backup/merge.py"
BACKUP_ROOT = "/dev/shm"
MBA_BOOTSTRAP_PATH="empire"
SPLIT_UPLOAD_CMD = "/opt/membase/membase-backup/misc/split_backup.py"
SPLIT_SIZE = 512
DEL_COMMAND = "del"
BLOBRESTORE_JOBS_DIR = '/home/blobrestore/jobs/'
BLOBRESTORE_PROCESSED_JOBS_DIR = '/home/blobrestore/processed_jobs/'
SYSLOG_TAG_BLOBRESTORE = 'blobrestore'
BLOBRESTORE_DAEMON_LOG = '/var/log/blobrestore_daemon.log'
BACKUP_ARRAY_IPLIST = 's3://zynga-common/membase-backup-production-test2/configs/blobrestore-arrays'
STORAGE_SERVER_ROOT = '/var/www/html/membase_backup'
MAX_BACKUP_LOOKUP_DAYS = 10
LAST_MASTER_BACKUP_TIME = '/db/last_master_backup'
