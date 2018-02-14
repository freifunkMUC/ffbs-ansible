#!/usr/bin/env python3
import etcd
import random
import json
import time
import ssl
import subprocess
import sys
import signal

class EqmttClusterManager():

    def whoAmI(self):    
        # find out which node this is
        self.node = False 
        try: 
            self.node = subprocess.check_output(['/usr/sbin/emqttd_ctl','status']).decode().split('\'')[1]
        except subprocess.CalledProcessError as e:
            print("ERROR: emqtt_ctl returned with non zero: %s"% (e,))
            sys.exit(-1)
        except FileNotFoundError as e:
            print("ERROR: emqtt_ctl is no present")
            sys.exit(-1)

    
    def parseOutput(self, output):
        #output = "Cluster status: [{running_nodes,['emq@172.16.1.2','emq@172.16.1.1']},\n	  {stopped_nodes,['emq@172.16.1.3']}]"
        output = output.decode().split(':')[1]
        sBracketBal = 0
        cBracketBal = 0
        sBracketCount = 0
        cBracketCount = 0
        val = ''
        tList = []
        tdict = {}
        running_nodes = []
        stopped_nodes = []
        state = None
        success = False 
        code = ""
        for c in output:
            if c == '[':
                sBracketBal += 1 
                sBracketCount += 1 
            elif c == '{':
                cBracketBal += 1 
                cBracketCount += 1 
            elif c == ']':
                sBracketBal -= 1 
                if state == 'running_nodes':
                    running_nodes.append(val.strip('\''))
                    val = ''
                if state == 'stopped_nodes':
                    stopped_nodes.append(val.strip('\''))
                    val = ''
                state = None
            elif c == '}':
                cBracketBal -= 1 
                state = None
            elif c == ',':
                if state == None:
                    if val == 'running_nodes':
                        state = 'running_nodes'
                        val = ''
                        success = True 
                    if val == 'stopped_nodes':
                        state = 'stopped_nodes'
                        val = ''
                        success = True 
                    if val == 'node_down':
                        code = val
                        val = ''
                        success = False
                    if val == 'already_in_cluster':
                        code = val
                        val = ''
                        success = True 
                if state == 'running_nodes':
                    running_nodes.append(val.strip('\''))
                    val = ''
                if state == 'stopped_nodes':
                    stopped_nodes.append(val.strip('\''))
                    val = ''
            else:
                val += c
        return (success, code, running_nodes, stopped_nodes)


    def announceMe(self,state):        
        if self.etcdNodeKey == None:
            self.etcNodeKey = self.client.write(self.nodePrefix+self.node, state ,self.nodeTTL)
        else:
            self.etcNodeKey.ttl = self.nodeTTL
            self.etcNodeKey = self.client.update(self.etcNodeKey)
            
        print("announced me to etcd in %s"% (self.etcNodeKey.key))

    def getAnnouncedNodes(self):
        result = self.client.read(self.nodePrefix, recursive = True)
        nodes = []
        for clusterNode in result.children:
            print("%s: %s" %(clusterNode.key,clusterNode.value))
            if clusterNode.value != self.node:
                nodes.append(clusterNode.value)
        return nodes

    def joinCluster(self,node):
       try: 
           output = subprocess.check_output(['/usr/sbin/emqttd_ctl','cluster','join',node])
           success, code, self.running_nodes, self.stoped_nodes = self.parseOutput(output)
           if not success:
               print(code)
           return success 
       except subprocess.CalledProcessError as e:
           print("ERROR: emqtt_ctl returned with non zero: %s"% (e,))
           return False 
       except FileNotFoundError as e:
           print("ERROR: emqtt_ctl is no present")
           sys.exit(-1)

    def leaveCluster(self):
       try: 
           output = subprocess.check_output(['/usr/sbin/emqttd_ctl','cluster','leave'])
           success, code, self.running_nodes, self.stoped_nodes = self.parseOutput(output)
           if not success:
               print(code)
           return success 
       except subprocess.CalledProcessError as e:
           print("ERROR: emqtt_ctl returned with non zero: %s"% (e,))
           return False 
       except FileNotFoundError as e:
           print("ERROR: emqtt_ctl is no present")
           sys.exit(-1)
           
    def getCluster(self):
       try: 
           output = subprocess.check_output(['/usr/sbin/emqttd_ctl','cluster','leave'])
           success, code, self.running_nodes, self.stoped_nodes = self.parseOutput(output)
           return success 
       except subprocess.CalledProcessError as e:
           print("ERROR: emqtt_ctl returned with non zero: %s"% (e,))
           return False 
       except FileNotFoundError as e:
           print("ERROR: emqtt_ctl is no present")
           sys.exit(-1)



    def exit(self,signum, frame):
        self.running = False
            
    def __init__(self):
        
        signal.signal(signal.SIGINT, self.exit)
        signal.signal(signal.SIGTERM, self.exit)
        self.running = True
        
        self.whoAmI()
        self.etcdEndpoint = False 
        self.etcdConf = json.load(open('/etc/etcd-client.json'))
        #figure out wether this machiene is an etcd endpoint and connect to it
        for endpoint in self.etcdConf['ENDPOINTS'].split(','):
            if self.node.split('@')[1] == endpoint.split(':')[1][2:]:
                self.etcdEndpoint = endpoint
        if not self.etcdEndpoint:
            self.etcdEndpoint = random.choice(self.etcdConf['ENDPOINTS'].split(',')) #choose arandom etcd endpoint
        self.etcdEndpoint = self.etcdEndpoint.split(':')
        self.etcdPort = int(self.etcdEndpoint[2])
        self.etcdProtocol = self.etcdEndpoint[0] 
        self.etcdEndpoint = self.etcdEndpoint[1][2:] # remove slashes
        self.etcdCert = None
        self.etcdCaCert = None
        self.etcdKey = None
        self.etcdNodeKey = None
        if self.etcdProtocol == 'https':
            self.etcdCert = self.etcdConf['CERT'] 
            self.etcdKey = self.etcdConf['KEY']
            self.etcdCaCert = self.etcdConf['CACERT'] 
    
        self.client = etcd.Client(host=self.etcdEndpoint, port=self.etcdPort, read_timeout=60, protocol=self.etcdProtocol, ca_cert=self.etcdCaCert, cert=(self.etcdCert,self.etcdKey))
        self.client.http.connection_pool_kw['ssl_version'] = ssl.PROTOCOL_TLSv1_2 #forcing TLS version 1.2
 
        #put this node into the etcd 
        self.nodePrefix = '/emqttd/cluster/nodes/'
        self.nodeTTL = 60
 
        lastUpdate = time.time() - self.nodeTTL 
        while self.running:
            if lastUpdate + self.nodeTTL/2 < time.time():
                self.announceMe(self.node)
                #join cluster with all announced nodes
                for n in self.getAnnouncedNodes():
                    self.joinCluster(n)
                lastUpdate = time.time()
            time.sleep(1)
        self.leaveCluster()
        
if __name__ == '__main__':
    clusterM = EqmttClusterManager()
    sys.exit(0)
