import os
import time
import sys
import os.path
import re
import socket
from subprocess import call

from java.lang import Boolean
from java.util import Properties
from java.io import File
from java.io import FileReader

from com.datasynapse.fabric.util import ContainerUtils
from com.datasynapse.fabric.common import RuntimeContextVariable
from com.datasynapse.fabric.common import ActivationInfo
    
class Docker:
    def __init__(self, additionalVariables):
        " initialize Docker"
        
        images = getVariableValue("DOCKER_IMAGE")
        if not images:
            raise "DOCKER_IMAGE must be specified"
        imageList = images.split(",")
        
        tagsList = None
        tags = getVariableValue("DOCKER_IMAGE_TAG") 
        if tags:
            tagList = tags.split(",")
        
        self.__dockerImage = []
        self.__dockerImageTag = []
        
        for index, item in enumerate(imageList):
            item = item.strip()
            imageDetails = item.split(":")
            if len(imageDetails) > 1:
                self.__dockerImage.append(imageDetails[0])
                self.__dockerImageTag.append(imageDetails[1])
            else:
                self.__dockerImage.append(item)
                if listItem(tagList, index):
                    self.__dockerImageTag.append(tagList[index])
                else:
                    self.__dockerImageTag.append("latest")
        
        
        self.__dockerContext  = None
        dockerContext = getVariableValue("DOCKER_CONTEXT")
        if dockerContext:
            self.__dockerContext = dockerContext.split(",")
        
        self.__dockerRegistry =  None
        dockerRegistry = getVariableValue("DOCKER_REGISTRY")
        if dockerRegistry:
            self.__dockerRegistry = dockerRegistry.split()

        activationInfo = proxy.container.getActivationInfo()
        componentInstance = activationInfo.getProperty(ActivationInfo.COMPONENT_INSTANCE)
        self.__compName = proxy.container.getCurrentDomain().getName()
        self.__compName = re.sub("[\s]+", "", self.__compName)
        
        self.__dockerContainerName = []
        containerName = getVariableValue("DOCKER_CONTAINER_NAME")
        if containerName:
            self.__dockerContainerName = containerName.split(",")
        
        self.__basedir = getVariableValue("CONTAINER_WORK_DIR")
        self.__cidfile = []
        self.__inspect  = []
        self.__stats = []
        self.__running = []
        self.__ipaddress=[]
        
        self.__dockerLog = getVariableValue("DOCKER_CONTAINER_LOGS")
        if not self.__dockerLog:
            self.__dockerLog = os.path.join(self.__basedir , "docker.log")
       
        for index, item in enumerate(self.__dockerImage):
            if not listItem(self.__dockerContainerName, index):
                dcname = self.__compName  +"-"+ item + "-"+ componentInstance
                dcname = re.sub("[\./]+", "_", dcname)
                if not (index < len(self.__dockerContainerName)):
                    self.__dockerContainerName.append(dcname)
                else:
                     self.__dockerContainerName[index] = dcname
            containerName = listItem(self.__dockerContainerName, index)
            logger.info("Docker container name:" + containerName)
            self.__cidfile.append(os.path.join(self.__basedir , containerName + ".cid"))
            self.__inspect.append(os.path.join(self.__basedir , containerName + ".inspect"))
            self.__stats.append(os.path.join(self.__basedir , containerName + ".stats"))
            self.__running.append(False)
            self.__ipaddress.append("")
            
        self.__sudo = Boolean.parseBoolean(getVariableValue("USE_SUDO", "false"))
        
        self.__runningRegex = re.compile("\"Running\":\s*true")
        self.__ipaddressRegex = re.compile("\"IPAddress\":\s*\"([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\".*")
        
        self.__lockExpire = int(getVariableValue("LOCK_EXPIRE", "300000"))
        self.__lockWait = int(getVariableValue("LOCK_WAIT", "30000"))
        self.__locked = None
        self.__dockerStats = {}
        
        self.__buildLock = "docker-build:"+getVariableValue("LISTEN_ADDRESS")
        self.__startInterval = getVariableValue("DOCKER_START_INTERVAL_SECS", "15")

        
        self. __getEc2PrivateIpv4s(additionalVariables)
    
    def __initOptions(self):
        self.__buildOptions = None
        buildOptions = getVariableValue("DOCKER_EXTRA_BUILD_OPTIONS")
        if buildOptions:
            self.__buildOptions = buildOptions.split(",")
            
        self.__networkMode = None
        networkMode = getVariableValue("DOCKER_CONTAINER_NETWORK_MODE")
        if networkMode:
            self.__networkMode = networkMode.split(",")
            
        self.__exposePorts = None
        exposePorts = getVariableValue("DOCKER_EXPOSE_PORTS")
        if exposePorts:
            self.__exposePorts = exposePorts.split(",")
            
        self.__publishPorts = None
        publishPorts = getVariableValue("DOCKER_PUBLISH_PORTS")
        if publishPorts:
            self.__publishPorts = publishPorts.split(",")
            
        self.__mountVolumes = None
        mountVolumes = getVariableValue("DOCKER_MOUNT_VOLUMES")
        if mountVolumes:
            self.__mountVolumes = mountVolumes.split(",")
            
        self.__envVars = None
        envVars = getVariableValue("DOCKER_ENV_VARIABLES")
        if envVars:
            self.__envVars = envVars.split(",")
            
        self.__envFile = None
        envFile = getVariableValue("DOCKER_ENV_FILE")
        if envFile:
            self.__envFile = envFile.split(",")
            
        self.__dnsSearch = None
        dnsSearch = getVariableValue("DNS_SEARCH_DOMAINS")
        if dnsSearch:
            self.__dnsSearch = dnsSearch.split(",")
        
        self.__containerHostname = None
        containerHostname = getVariableValue("DOCKER_CONTAINER_HOSTNAME")
        if containerHostname:
            self.__containerHostname = containerHostname.split(",")
            
        self.__workDir = None
        workDir = getVariableValue("DOCKER_CONTAINER_WORK_DIR")
        if workDir:
            self.__workDir = workDir.split(",")
        
        self.__link= None
        link = getVariableValue("DOCKER_LINK")
        if link:
            self.__link = link.split(",")
            
        self.__runOptions = None
        runOptions = getVariableValue("DOCKER_EXTRA_RUN_OPTIONS")
        if runOptions:
            self.__runOptions = runOptions.split(",")
            
        self.__command = None
        command = getVariableValue("DOCKER_COMMAND")
        if command:
            self.__command = command.split(",")
            
        self.__commandArgs = None
        commandArgs = getVariableValue("DOCKER_COMMAND_ARGS")
        if commandArgs:
            self.__commandArgs = commandArgs.split(",")
            
        self.__runningPorts = None
        runningPorts = getVariableValue("APP_RUNNING_PORTS")
        if runningPorts:
            self.__runningPorts = runningPorts.split(",")
            
    def __getEc2PrivateIpv4s(self, additionalVariables):
        try:
            dir = File(self.__basedir)
            dir = dir.getParentFile().getParentFile().getParentFile()
            fileReader = FileReader(File(dir, "engine-session.properties" ))
            props = Properties()
            props.load(fileReader)
            ec2PrivateIpv4s = props.getProperty("ec2PrivateIpv4s")
            if ec2PrivateIpv4s:
                ipList = ec2PrivateIpv4s.split()
                logger.info("Ec2 Private IPv4s:" + list2str(ipList))
                engineInstance = getVariableValue("ENGINE_INSTANCE")
                engineInstance = int(engineInstance)
                if len(ipList) > engineInstance:
                    self.__dockerHostIp = ipList[engineInstance]
                    logger.info("Setting DOCKER_HOST_IP:" +self.__dockerHostIp)
                    additionalVariables.add(RuntimeContextVariable("DOCKER_HOST_IP", self.__dockerHostIp, RuntimeContextVariable.STRING_TYPE, "Docker Host IP", False, RuntimeContextVariable.NO_INCREMENT))
                else:
                    self.__dockerHostIp  = getVariableValue("LISTEN_ADDRESS")
                    additionalVariables.add(RuntimeContextVariable("DOCKER_HOST_IP", self.__dockerHostIp , RuntimeContextVariable.STRING_TYPE, "Docker Host IP", False, RuntimeContextVariable.NO_INCREMENT))
        except:
            type, value, traceback = sys.exc_info()
            logger.warning("read engine session properties error:" + `value`)
            
    def __lock(self):
        "get build lock"
        logger.info("Acquire build lock:" + self.__buildLock)
        self.__locked = ContainerUtils.acquireGlobalLock(self.__buildLock, self.__lockExpire, self.__lockWait)
        if not self.__locked:
            raise Exception("Unable to acquire build lock:" + self.__buildLock)
    
    def __unlock(self):
        "unlock global lock"
        logger.info("Release build lock:" + self.__buildLock)
        if self.__locked:
            ContainerUtils.releaseGlobalLock(self.__buildLock)
    
    def __imageExists(self, index):
        imageExists = False
        file = None
        try:
            path = os.path.join(self.__basedir , "docker.images")
            file = open(path, "w")
            image = listItem(self.__dockerImage, index) +":" + listItem(self.__dockerImageTag, index)
            
            registry = listItem(self.__dockerRegistry, index, True)
            if registry:
                image = "*/"+ image
                
            cmdList = ["docker", "images", image]
      
            if self.__sudo:
                cmdList.insert(0, "sudo")
            
            logger.info("Docker local images:" + list2str(cmdList))
            retcode = call(cmdList, stdout=file)
            logger.info("Local images return code:" + `retcode`)
            
            file.flush()
            file.close()
            
            image = listItem(self.__dockerImage, index)
            if registry:
                image = registry +"/" + image
                        
            file = open(path, "r")
            lines = file.readlines()
            for line in lines:
                row = line.split()
                if row:
                    logger.info("Checking cached images:" + list2str(row))
                    if row[0] == image and listItem(self.__dockerImageTag, index) == row[1]:
                        logger.info("Cached image matches:" + row[0] +":"+ row[1])
                        imageExists = True
                        break
        finally:
            if file:
                file.close()
            
        return imageExists

    def __containerExists(self, index):
        containerExists = False
        file = None
        try:
            path = os.path.join(self.__basedir , "docker.ps")
            file = open(path, "w")
            cmdList = ["docker", "ps", "--filter", "name=" + listItem(self.__dockerContainerName, index)]
      
            if self.__sudo:
                cmdList.insert(0, "sudo")
            
            logger.info("Docker container list:" + list2str(cmdList))
            retcode = call(cmdList, stdout=file)
            logger.info("Docker container list return code:" + `retcode`)
            
            file.flush()
            file.close()
            file = open(path, "r")
            lines = file.readlines()
            for line in lines:
                row = line.split()
                logger.info("Checking container:" + list2str(row))
                if row and row[-1].strip() == listItem(self.__dockerContainerName, index):
                    image = listItem(self.__dockerImage, index) + ":" + listItem(self.__dockerImageTag, index)
                    registry = listItem(self.__dockerRegistry, index, True)
                    if registry:
                        image = registry + "/" + image
                    if image.find(row[1]) == 0:
                        logger.info("Container exists with matching image:" + listItem(self.__dockerContainerName, index) + " " + image)
                        containerExists = True
                        break
                    else:
                        logger.info("No container found with matching image:" + listItem(self.__dockerContainerName, index) +" " + image)
        finally:
            if file:
                file.close()
            
        return containerExists
    
    def __build(self, index):
        "build image"
        
        self.__lock()
        try:
            self.__rm(index)
            self.__rmi(index)
        
            cmdList = ["docker", "build", "-t", listItem(self.__dockerImage, index)]
            options = listItem(self.__buildOptions, index, True)
            if options:
                cmdList = cmdList + options.split()
        
            cmdList.append(self.__dockerContext[index])
    
            if self.__sudo:
                cmdList.insert(0, "sudo")
            
            logger.info("Build image:" + list2str(cmdList))
            retcode = call(cmdList)
            logger.info("Build image return code:" + `retcode`)
        finally:
            self.__unlock()
            
    def __start(self, index):
        "start stopped container"
        
        cmdList = ["docker", "start", listItem(self.__dockerContainerName, index)]
      
        if self.__sudo:
            cmdList.insert(0, "sudo")
            
        logger.info("Start Docker container:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Start Docker container return code:" + `retcode`)
        if retcode != 0:
            raise "Error return code while starting docker container"

    def __pull(self, index):
        "pull image from repository"
        self.__lock()
        try:
            image = listItem(self.__dockerImage, index) + ":"+ listItem(self.__dockerImageTag, index)
            
            registry = listItem(self.__dockerRegistry, index, True)
            if registry:
                image = registry + "/"  + image
            
            cmdList = ["docker", "pull", image]
      
            if self.__sudo:
                cmdList.insert(0, "sudo")
            
            logger.info("Pull docker image:" + list2str(cmdList))
            retcode = call(cmdList)
            logger.info("Pull docker image return code:" + `retcode`)
        finally:
            self.__unlock()
        
    def __run(self, index):
        "run docker container"
        
        logger.info("Enter __run")
        cmdList = ["docker", "run"]
        
        network = listItem(self.__networkMode, index, True)
        if network:
            cmdList.append(network)
        
        expose = listItem(self.__exposePorts, index)
        if expose:
            cmdList = cmdList + expose.split()
            
        publish = listItem(self.__publishPorts, index)
        if publish:
            cmdList = cmdList + publish.split()
            
        volumes = listItem(self.__mountVolumes, index)
        if volumes:
            cmdList = cmdList + volumes.split()
            
        envs = listItem(self.__envVars, index)
        if envs:
            cmdList = cmdList + envs.split()
            
        envFile = listItem(self.__envFile, index)
        if envFile:
            cmdList = cmdList + envFile.split()
            
        dns = listItem(self.__dnsSearch, index)
        if dns:
            cmdList = cmdList + dns.split()
        
        link = listItem(self.__link, index)
        if link:
            cmdList = cmdList + link.split()
        
        hostname = listItem(self.__containerHostname, index)
        if hostname:
            cmdList.append("--hostname=" + hostname)
            
        work = listItem(self.__workDir, index)
        if work:
            cmdList.append("--workdir=" + work)
            
        cmdList.append("--name=" + listItem(self.__dockerContainerName, index))
        cmdList.append("--cidfile=" + self.__cidfile[index])
        
        options = listItem(self.__runOptions, index, True)
        if options:
            options = options.split()
            
            if "--detach=false" in options:
                options.remove("--detach=false")

            if not ("-d" in options) and not ("--detach=true" in options):
                options.append("--detach=true")
                
            cmdList = cmdList + options
        else:
            cmdList = cmdList + ["--detach=true"]
        
        image = listItem(self.__dockerImage, index) + ":"+ listItem(self.__dockerImageTag, index)
        registry = listItem(self.__dockerRegistry, index, True)
        if registry:
            image = registry +"/" + image
        
        cmdList.append(image)
    
        command = listItem(self.__command, index)
        if command:
            cmdList.append(command)
            
        commandArgs = listItem(self.__commandArgs, index)
        if commandArgs:
            args = commandArgs.split()
            if args:
                cmdList.extend(args)
      
        if self.__sudo:
            cmdList.insert(0, "sudo")
            
        logger.info("Run Docker container:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Run Docker container return code:" + `retcode`)
        self.__logs(index)
        
        if retcode != 0:
            raise "Error return code while running docker container"
            
        logger.info("Exit __run")
        
    def __stop(self, index):
        "stop docker container"
        
        logger.info("Enter __stop")
        cmdList = ["docker", "stop"]
       
        options = getVariableValue("DOCKER_STOP_OPTIONS")
        if options:
            options = options.split()
            cmdList = cmdList + options
        
        cmdList.append(listItem(self.__dockerContainerName, index))
        
        if self.__sudo:
            cmdList.insert(0, "sudo")
        
        logger.info("Stop docker container:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Stop docker container return code:" + `retcode`)
        
        logger.info("Exit __stop")
        
    def __logs(self, index):
        "docker container logs"
        file = None
        
        try:
            path = self.__dockerLog
            if index == 0:
                file = open(path, "w")
            else:
                file = open(path, "a")
            
            cmdList = ["docker", "logs", listItem(self.__dockerContainerName, index)]
       
            if self.__sudo:
                cmdList.insert(0, "sudo")
        
            logger.fine("Write Docker container logs:" + list2str(cmdList))
            retcode = call(cmdList, stdout=file, stderr=file)
            logger.fine("Write Docker container logs return code:" + `retcode`)
        except:
            type, value, traceback = sys.exc_info()
            logger.warning("docker logs error:" + `value`)
        finally:
            if file:
                file.close()
        
    def __rm(self, index):
        "remove docker container"
        
        logger.info("Enter __rm")
        cmdList = ["docker", "rm"]
        
        options = getVariableValue("DOCKER_REMOVE_OPTIONS")
        if options:
            options = options.split()
            cmdList = cmdList + options
        
        cmdList.append(listItem(self.__dockerContainerName, index))
        
        if self.__sudo:
            cmdList.insert(0, "sudo")
            
        logger.info("Remove Docker container:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Remove Docker container return code:" + `retcode`)
        logger.info("Exit __rm")
        
    def __rmi(self, index):
        "remove docker image"
        
        logger.info("Enter __rmi")
        cmdList = ["docker", "rmi"]
        
        options = getVariableValue("DOCKER_REMOVE_IMAGE_OPTIONS")
        if options:
            options = options.split()
            cmdList = cmdList + options
        
        image = listItem(self.__dockerImage, index) + ":"+ listItem(self.__dockerImageTag, index)
        registry = listItem(self.__dockerRegistry, index, True)
        if registry:
            image = registry + "/" + image
            
        cmdList.append(image)
        
        if self.__sudo:
            cmdList.insert(0, "sudo")
       
        logger.info("Remove Docker image:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Remove Docker image return code:" + `retcode`)
        logger.info("Enter __rmi")
        
    def start(self):
        "start enabler"
        
        logger.info("Enter start")
        copyContainerEnvironment()
        self.__initOptions()
        
        reuseContainer = Boolean.parseBoolean(getVariableValue("REUSE_DOCKER_CONTAINER", "false"))
        reuseImage = Boolean.parseBoolean(getVariableValue("REUSE_DOCKER_IMAGE", "true"))
        
        for index in range(len(self.__dockerContainerName)):
            if reuseContainer and self.__containerExists(index):
                self.__start(index)
            elif reuseImage and self.__imageExists(index):
                self.__run(index)
            elif listItem(self.__dockerContext, index):
                self.__build(index)
                self.__run(index)
            else:
                self.__pull(index)
                self.__run(index)
            while True:
                logger.info("Waiting for container to start:" + listItem(self.__dockerContainerName, index))
                time.sleep(float(self.__startInterval))
                self.__isContainerRunning(index)
                if self.__running[index]:
                    break
      
        logger.info("Exit start")
    
    def stop(self):
        "stop enabler"
        logger.info("Enter stop")
        copyContainerEnvironment()
        
        for index in range(len(self.__dockerContainerName) - 1, -1, -1):
            self.__stop(index)
        logger.info("Exit stop")
    
        
    def cleanup(self):
        "cleanup"
        
        logger.info("Enter cleanup")
        try:
            copyContainerEnvironment()
            removeContainer = Boolean.parseBoolean(getVariableValue("REMOVE_DOCKER_CONTAINER", "true"))
            removeImage = Boolean.parseBoolean(getVariableValue("REMOVE_DOCKER_IMAGE", "false"))
            
            for index in range(len(self.__dockerContainerName) - 1, -1, -1):
                if removeContainer:
                    self.__rm(index)
            
                if removeImage:
                    self.__rmi(index)
        except:
            type, value, traceback = sys.exc_info()
            logger.warning("cleanup error:" + `value`)
            
        logger.info("Exit cleanup")
               
    def __writeInspect(self, index):
        "write inspect output"
        
        file = None
        try:
            file = open(self.__inspect[index], "w")
            cmdList = ["docker", "inspect", listItem(self.__dockerContainerName, index)]
            if self.__sudo:
                cmdList.insert(0, "sudo")
                
            retcode = call(cmdList, stdout=file)
        finally:
            if file:
                file.close()
                
    def __writeStats(self, index):
        "write stats output"
        
        file = None
        try:
            file = open(self.__stats[index], "w")
            cmdList = ["docker", "stats", "--no-stream=true", listItem(self.__dockerContainerName, index)]
            if self.__sudo:
                cmdList.insert(0, "sudo")
                
            retcode = call(cmdList, stdout=file)
        finally:
            if file:
                file.close()

    def __readInspect(self, index):
        "read inspect output"
        
        self.__running[index] = False
        
        file = None
        try:
            path = self.__inspect[index]
            if os.path.isfile(path):
                file = open(path, "r")
                lines = file.readlines()
                for line in lines:
                    line = line.strip()
                    if not self.__running[index]:
                        match = self.__runningRegex.search(line)
                        if match:
                            self.__running[index] = True
                    elif not self.__ipaddress[index]:
                        result = self.__ipaddressRegex.match(line)
                        if result:
                            self.__ipaddress[index] = result.group(1)
                            logger.info("Container ip address:" + str(self.__ipaddress))
                    if self.__running[index] and self.__ipaddress[index]:
                        break
        finally:
            if file:
                file.close()
                
    def __readStats(self, index):
        "read stats output"
        file = None
        self.__dockerStats.clear()
        
        try:
            path = self.__stats[index]
            if os.path.isfile(path):
                file = open(path, "r")
                lines = file.readlines()
                for line in lines:
                    row = line.replace('%','').replace('/','').split()
                    if row and (len(row) == 15) and (row[0] == listItem(self.__dockerContainerName, index)):
                        self.__dockerStats["Docker CPU Usage %"] = row[1]
                        self.__dockerStats["Docker Memory Usage (MB)"] = convertToMB(row[2], row[3])
                        self.__dockerStats["Docker Memory Limit (MB)"] = convertToMB(row[4], row[5])
                        self.__dockerStats["Docker Memory Usage %"] = row[6]
                        self.__dockerStats["Docker Network Input (MB)"] = convertToMB(row[7], row[8])
                        self.__dockerStats["Docker Network Output (MB)"] = convertToMB(row[9], row[10])
                        self.__dockerStats["Docker Block Input (MB)"] = convertToMB(row[11], row[12])
                        self.__dockerStats["Docker Block Output (MB)"] = convertToMB(row[13], row[14])
        finally:
            if file:
                file.close()
    
    def __isContainerRunning(self, index):
        try:
            self.__writeInspect(index)
            self.__readInspect(index)
            
            if self.__running[index]:
                runningPorts = listItem(self.__runningPorts, index)
                if runningPorts:
                    portList = runningPorts.split()
                    for port in portList:
                        self.__running[index] = ping(listItem(self.__ipaddress, index), port)
                        if not self.__running[index]:
                            break
        except:
            type, value, traceback = sys.exc_info()
            logger.warning("isContainerRunning error:" + `value`)
            self.__running[index] = False
        
    def isRunning(self):
        copyContainerEnvironment()  
        
        running = True
        try:
            llen = len(self.__dockerContainerName)
            for index in range(llen):
                self.__isContainerRunning(index)
                if self.__running[index]:      
                    self.__logs(index)
                    if index == llen - 1:
                        self.__writeStats(index)
                        self.__readStats(index)
                else:
                    running = False
                    break
            logger.fine("isRunning:" + `running`)
        except:
            running = False
            type, value, traceback = sys.exc_info()
            logger.warning("isRunning error:" + `value`)
        
        return running
    
    def installActivationInfo(self, info):
        "install activation info"

        routes = getVariableValue("HTTP_STATIC_ROUTES")
        if routes:
            routes = routes.split()
            index = 1
            for route in routes:
                propertyName = "HTTP_STATIC_ROUTE" + self.__compName + str(index)
                info.setProperty(propertyName, route)
    
    def getStat(self, statName):
        " get statistic"
        return self.__dockerStats[statName]
                

def ping(host, port):
    success = False
    s = None
    try:
        s = socket.socket()
        s.connect((host, int(port)))
        success = True
    except:
        type, value, traceback = sys.exc_info()
        logger.warning("ping failed:" + `value`)
    finally:
        if s:
            s.close()
    
    return success
    
def convertToMB(value, unit):
    unit = unit.lower()
    value = float(value)
    if unit == "gb":
        value = value * 1000.0
    elif unit == "b":
        value = value / 1000.0
        
    return value

def listItem(list, index, useDefault=False):
    item = None
    if list:
        llen = len(list)
        if llen > index:
            item = list[index].strip()
        elif useDefault and llen == 1:
            item = list[0].strip()
    
    return item

def list2str(list):
    content = str(list).strip('[]')
    content =content.replace(",", " ")
    content =content.replace("u'", "")
    content =content.replace("'", "")
    return content
    
def copyContainerEnvironment():
    count = runtimeContext.variableCount
    for i in range(0, count, 1):
        rtv = runtimeContext.getVariable(i)
        if rtv.type == "Environment":
            os.environ[rtv.name] = rtv.value
    
    os.unsetenv("LD_LIBRARY_PATH")
    os.unsetenv("LD_PRELOAD")
    
def mkdir_p(path, mode=0700):
    if not os.path.isdir(path):
        logger.info("Creating directory:" + path)
        os.makedirs(path, mode)

    
def getVariableValue(name, value=None):
    "get runtime variable value"
    var = runtimeContext.getVariable(name)
    if var != None:
        value = var.value
    
    return value

def doInit(additionalVariables):
    "do init"
    docker = Docker(additionalVariables)
             
    # save mJMX MBean server as a runtime context variable
    dockerRcv = RuntimeContextVariable("DOCKER__OBJECT", docker, RuntimeContextVariable.OBJECT_TYPE)
    runtimeContext.addVariable(dockerRcv)


def doStart():
    try:
        docker = getVariableValue("DOCKER__OBJECT")
        
        if docker:
            docker.start()
            
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in Docker:doStart:" + `value`)
    
def doShutdown():
    try:
        docker = getVariableValue("DOCKER__OBJECT")
        
        if docker:
            docker.stop()
            
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in Docker:doShutdown:" + `value`)
        
def hasContainerStarted():
    started = False
    try:
        docker = getVariableValue("DOCKER__OBJECT")
        
        if docker:
            started = docker.isRunning()
            if started:
                logger.info("Docker container has started!")
            else:
                logger.info("Docker container starting...")
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in Docker:hasContainerStarted:" + `value`)
    
    return started

def cleanupContainer():
    try:
        docker = getVariableValue("DOCKER__OBJECT")
        
        if docker:
            docker.cleanup()
            
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in Docker:cleanup:" + `value`)
    finally:
        proxy.cleanupContainer()
            
    
def isContainerRunning():
    running = False
    try:
        docker = getVariableValue("DOCKER__OBJECT")
        if docker:
            running = docker.isRunning()
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in Docker:isContainerRunning:" + `value`)
    
    return running

def doInstall(info):
    " do install of activation info"

    logger.info("doInstall:Enter")
    try:
        docker = getVariableValue("DOCKER__OBJECT")
        if docker:
            docker.installActivationInfo(info)
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in Docker:doInstall:" + `value`)
    finally:
        proxy.doInstall(info)
        
    logger.info("doInstall:Exit")
    

def getStatistic(statName):
    stat = None
    try:
        docker = getVariableValue("DOCKER__OBJECT")
        if docker:
            stat = docker.getStat(statName)
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in Docker:getStatistic:" + `value`)
    return stat

def getContainerStartConditionPollPeriod():
    poll = getVariableValue("START_POLL_PERIOD", "10000")
    return int(poll)
    
def getContainerRunningConditionPollPeriod():
    poll = getVariableValue("RUNNING_POLL_PERIOD", "60000")
    return int(poll)
