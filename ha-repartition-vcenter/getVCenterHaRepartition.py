#!/usr/bin/python
import pyVmomi
import argparse
import atexit
import humanize
import re
import os

from pyVim import connect
from pyVmomi import vim
from pyVim.connect import Disconnect
from operator import itemgetter


MBFACTOR = float(1 << 20)

REGEX_HOST_FILTER = "." # to filter by name (if using naming norm)
REGEX_DS_FILTER = "." # to filter by name (if using naming norm)

LIST_DC_IGNORED = [] # To exclude DC from the search base
LIST_HOSTS_IGNORED = [] # To exclude some hosts from the availability list
LIST_DS_IGNORED = [] # To exlude some datastores from the availability list

LIMIT_DS_FREE_SPACE = 10 # Need more than X percents free space disk (based on each datastore)
LIMIT_HOSTS_FREE_RAM = 10 # Need more than X percents free ram (based on each hosts)
LIMIT_HOSTS_FREE_CPU = 10 # Need more than X percents free cpu (based on each hosts)

def req(var):
    if var not in os.environ:
        print("[ERROR] %s variable need to be defined in environment."%var)
        os._exit(1)
    return os.environ[var]

def GetArgs():

    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=False, action='store',
                        help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-i', '--size', type=int, default=1, action='store',
                        help='Size of HA Cluster')
    args = parser.parse_args()
    return args

class VCenter:
    def __init__(self, host, port, username, password):
        try:
            si = connect.Connect(host, port, username, password)
            atexit.register(Disconnect, si)
            self.content = si.RetrieveContent()

        except ValueError:
            print(ValueError)

    def fetchDatacenters(self, ignoreList=[]):
        self.datastore = []
        self.hostFolder = [] 
        for datacenter in self.content.rootFolder.childEntity:
            if datacenter.name not in ignoreList:
                self.datastore += datacenter.datastore
                self.hostFolder += datacenter.hostFolder.childEntity
        
        return self

    def fetchDatastores(self, ignoreList=[], regex="."):
        self.datastores = []
        for datastore in self.datastore:
            if datastore.name not in ignoreList and re.search(regex, datastore.name):
                #HDD
                dsSummary = datastore.summary
                capacity = dsSummary.capacity
                freeSpace = dsSummary.freeSpace
                uncommittedSpace = dsSummary.uncommitted
                freeSpacePercentage = (float(freeSpace) / capacity) * 100
                freeSpacePercentageHumanized = str(int(round(freeSpacePercentage, 0))) + "%"

                if freeSpacePercentage > LIMIT_DS_FREE_SPACE:
                    self.datastores.append({
                        'name' : datastore.name,
                        'freeSpace' : freeSpace,
                        'freeSpacePercentage' : freeSpacePercentage,
                        'sum' : "%s free disk space, %sGB disk space capacity, %sGB disk space used"%(freeSpacePercentageHumanized, 
                            round((capacity / MBFACTOR) / 1000, 0), 
                            round((freeSpace / MBFACTOR) / 1000, 0))
                    })
        self.datastores = Pile(sorted(self.datastores, key=itemgetter('freeSpace')))
        return self

    def fetchHostList(self, ignoreList=[], regex="."):
        self.hosts = []
        for computeResource in self.hostFolder:
            for host in computeResource.host:
                if host.name not in ignoreList and re.search(regex, host.name):
                    stats = host.summary.quickStats
                    hardware = host.hardware

                    #CPU
                    cpuCapacityMhz = (host.hardware.cpuInfo.hz * host.hardware.cpuInfo.numCpuCores) / 1000 / 1000
                    cpuUsageMhz = stats.overallCpuUsage
                    cpuUsageMhzPercentage = int(100 * cpuUsageMhz / cpuCapacityMhz)
                    cpuUsageMhzPercentageHumanized = str(int(100 * cpuUsageMhz / cpuCapacityMhz)) + '%'

                    #RAM
                    memoryCapacity = hardware.memorySize
                    memoryCapacityInMB = hardware.memorySize/MBFACTOR
                    memoryUsage = stats.overallMemoryUsage
                    freeMemoryPercentage = 100 - ((memoryUsage / memoryCapacityInMB) * 100)
                    freeMemoryPercentageHumanized = str(int(round(freeMemoryPercentage, 0))) + '%'

                    #UpTime
                    uptime = stats.uptime
                    uptimeDays = int(uptime / 60 / 60 / 24)
                    if freeMemoryPercentage > LIMIT_HOSTS_FREE_RAM and int(100 - cpuUsageMhzPercentage) > LIMIT_HOSTS_FREE_RAM:
                        self.hosts.append({
                            'name': host.name ,
                            'ram': freeMemoryPercentage,
                            'cpu': cpuUsageMhzPercentage,
                            'sum' : "%s CPU usage,  %s Free Memory"%(cpuUsageMhzPercentageHumanized, freeMemoryPercentageHumanized),
                            'cpuSum' : "%sMhz CPU capacity,  %sMhz CPU usage"%(round(cpuCapacityMhz, 0), round(cpuUsageMhz, 0)),
                            'ramSum' : "%sGB ram capacity,  %sGB ram usage"%(round(memoryCapacityInMB/1000, 0), round(memoryUsage/1000, 0)),
                            'uptime' : uptimeDays
                        })
        self.hosts = Pile(sorted(self.hosts, key=itemgetter('ram')))

        return self

class Pile:
    def __init__(self, arr=[]):
        self.list = arr
        self.index = 0

    def pop(self):
        if self.index == len(self.list):
            self.index = 0
            return self.list[self.index]
        else:
            self.index+=1
            return self.list[self.index-1]

    def append(self, el):
        self.list.append(el)
        return

    def len(self):
        return len(self.list)

def main():
    args = GetArgs()

    if args.user == None:
        args.user = req('USERNAME')

    if args.password == None: 
        args.password = req('PASSWORD')

    addressList = args.host.split(',')
    configList = []
    vCentersPile = Pile()
    for vCenterHost in addressList:
        vc = VCenter(vCenterHost, args.port, args.user, args.password)
        vc.fetchDatacenters(LIST_DC_IGNORED).fetchHostList(LIST_HOSTS_IGNORED, REGEX_HOST_FILTER).fetchDatastores(LIST_DS_IGNORED, REGEX_DS_FILTER)
        if vc.datastores.len() > 0 and vc.hosts.len() > 0:
            vCentersPile.append(vc)

    for i in range(args.size):
        vcTmp = vCentersPile.pop()
        configList.append({
            'vmNum': i+1,
            'host': vcTmp.hosts.pop(),
            'ds': vcTmp.datastores.pop()
        })

    print(configList)

if __name__ == "__main__":
    main()