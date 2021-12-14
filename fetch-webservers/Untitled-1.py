##################################################################
# Creation Date: 13/12/2021
# Last Update: 14/12/2021
# Description: Retrieve all webservers on vcenters's virtualmachines 
# Interactive: No
# Test command: 
# Run command: python3 Untitled-1.py  -s vcenter.proute.com
##################################################################
#!/usr/bin/python3.6

#################################################
#       Importation des librairies              #
#################################################
import argparse
import re
import sys
import threading
import socket
import requests
import base64
import os

#################################################
#                 Programme                     #
#################################################
# Check if we are running this on windows platform
is_windows = sys.platform.startswith('win')

# Console Colors
if is_windows:
    # Windows deserves coloring too :D
    G = '\033[92m'  # green
    Y = '\033[93m'  # yellow
    B = '\033[94m'  # blue
    R = '\033[91m'  # red
    W = '\033[0m'   # white
    try:
        import win_unicode_console , colorama
        win_unicode_console.enable()
        colorama.init()
        #Now the unicode will work ^_^
    except:
        print("[!] Error: Coloring libraries not installed, no coloring will be used [Check the readme]")
        G = Y = B = R = W = G = Y = B = R = W = ''

else:
    G = '\033[92m'  # green
    Y = '\033[93m'  # yellow
    B = '\033[94m'  # blue
    R = '\033[91m'  # red
    W = '\033[0m'   # white

outPath = './out.csv'
TO = 6


def req(var):
    if var not in os.environ:
        print("[ERROR] %s variable need to be defined in environment."%var)
        os._exit(1)
    return os.environ[var]

def GetArgs():

    parser = argparse.ArgumentParser(
        description='Scan ports and retrive Server headers on web servers')
    parser.add_argument('-s', '--host', action='store',
                        help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', action='store',
                        help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-c', '--scan', type=str, default='80,443,8005,8080,8443,8000,8008,9000', action='store',
                        help='Size of HA Cluster')
    args = parser.parse_args()
    return args

class VCenter:
    def __init__(self, url, username, password):
        try:
            self.url = url
            r = requests.post(
                "https://%s/rest/com/vmware/cis/session"%(self.url), 
                headers = { 
                    "Authorization": "Basic %s"%(base64.b64encode(('%s:%s'%(username, password)).encode()).decode("utf-8")),
                    "vmware-use-header-authn": "string",
                    "Content-Type": "application/json"
                    }
            )
            self.token = r.json()["value"]

        except ValueError:
            print(ValueError)

    def getServers(self):
        try:
            r = requests.get(
                "https://%s/rest/vcenter/vm"%(self.url), 
                headers = { 
                    "vmware-api-session-id": self.token,
                    "Content-Type": "application/json"
                    }
            )
            
            return  list(map(lambda x: x["name"], r.json()["value"]))

        except ValueError:
            print(ValueError)

class portscan():
    def __init__(self, subdomains, ports, file):
        self.subdomains = subdomains
        self.ports = ports
        self.file = file
        self.threads = 40
        self.lockHost = threading.BoundedSemaphore(value=20)
        self.lock = threading.BoundedSemaphore(value=self.threads)

    def port_scan(self, host, ports):
        openports = []
        self.lock.acquire()
        for port in ports:
            try:
                
                r = requests.get(
                "http://%s:%s"%(host, port), timeout=TO
                )
                if r.headers['Server']:
                    openports.append("%s,%s"%(port, r.headers['Server']))
                    print(G + "[+] Port http://%s:%s opened %s" % (host, port, W))
                else:
                    openports.append("%s,Unknown version"%(port))
                    print(G + "[+] Port http://%s:%s opened %s" % (host, port, W))
            except Exception:

                try:

                    r = requests.get(
                    "https://%s:%s"%(host, port), timeout=TO, verify=False
                    )

                    if r.headers['Server']:
                        openports.append("%s,%s"%(port, r.headers['Server']))
                        print(G + "[+] Port https://%s:%s opened %s" % (host, port, W))
                    else:
                        openports.append("%s,Unknown version"%(port))
                        print(G + "[+] Port https://%s:%s opened %s" % (host, port, W))

                except Exception:
                    Exception
                    #print(R + "[-] Port %s:%s closed in http & https %s"% (host, port, W))

        self.lock.release()
        if len(openports) > 0:
            self.file.write("%s;%s\n" % (host, ';'.join(openports)))
        

    def run(self):
        for subdomain in self.subdomains:

            #self.port_scan(subdomain, self.ports)
            print(G + "[-] Scanning %s%s "%(W, subdomain))

            t = threading.Thread(target=self.port_scan, args=(subdomain, self.ports))
            t.start()

def main():
    args = GetArgs()

    if args.user == None:
        args.user = req('VSPHERE_USER')

    if args.password == None: 
        args.password = req('VSPHERE_PASSWORD')

    portsToScan = args.scan.split(',')

    if args.host == None: 
        args.host = req('VSPHERE_SERVER')
    serverList = []
    addressList = args.host.split(',')
    for vCenterHost in addressList:
        vc = VCenter(vCenterHost, args.user, args.password)
        serverList += vc.getServers()

    outFile = open(outPath, 'w')
    print(G + "[-] Setup port scan now for the following ports: %s%s" %(Y + W, portsToScan))
    pscan = portscan(serverList, portsToScan, outFile)
    print(G + "[-] Start port scan" + W)
    pscan.run()

if __name__ == "__main__":
    main()
