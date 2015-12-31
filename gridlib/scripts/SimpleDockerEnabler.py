import os
import time
import sys
import os.path
import re
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
        
        self.__dockerImage = getVariableValue("DOCKER_IMAGE")
        
        if not self.__dockerImage:
            raise "DOCKER_IMAGE must be specified"
        
        imageDetails = self.__dockerImage.split(":")
        if len(imageDetails) > 1:
            self.__dockerImage = imageDetails[0]
            self.__dockerImageTag = imageDetails[1]
        else:
            self.__dockerImageTag = getVariableValue("DOCKER_IMAGE_TAG") 
            
        if not self.__dockerImageTag:
            self.__dockerImageTag = "latest"
        
        self.__dockerContext = getVariableValue("DOCKER_CONTEXT")
        self.__dockerRegistry = getVariableValue("DOCKER_REGISTRY")

        self.__dockerContainerName = getVariableValue("DOCKER_CONTAINER_NAME")
        
        if not self.__dockerContainerName:
            compName = proxy.container.getCurrentDomain().getName()
            logger.info("Using component name to derive Docker container name:" + compName)
            self.__dockerContainerName = compName
            
        self.__dockerContainerName = re.sub("\s+", "", self.__dockerContainerName)
        activationInfo = proxy.container.getActivationInfo()
        componentInstance = activationInfo.getProperty(ActivationInfo.COMPONENT_INSTANCE)
        self.__dockerContainerName = "sf-"+self.__dockerContainerName + "-"+ componentInstance
        logger.info("Docker container name:" + self.__dockerContainerName)
        
        self.__basedir = getVariableValue("CONTAINER_WORK_DIR")
        self.__cidfile = os.path.join(self.__basedir , self.__dockerContainerName + ".cid")
        self.__inspect = os.path.join(self.__basedir , self.__dockerContainerName + ".inspect")
        self.__stats = os.path.join(self.__basedir , self.__dockerContainerName + ".stats")
        self.__sudo = Boolean.parseBoolean(getVariableValue("USE_SUDO", "false"))
        
        self.__dockerlogs = getVariableValue("DOCKER_CONTAINER_LOGS")
        
        self.__runningRegex = re.compile("\"Running\":\s*true")
        self.__running = False
        self.__inspectInfo = None
        
        self.__lockExpire = int(getVariableValue("LOCK_EXPIRE", "300000"))
        self.__lockWait = int(getVariableValue("LOCK_WAIT", "30000"))
        self.__locked = None
        self.__dockerStats = {}
        
        self.__buildLock = "docker-build:"+getVariableValue("LISTEN_ADDRESS")
        self. __getEc2PrivateIpv4s(additionalVariables)
     
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
                    dockerHostIp = ipList[engineInstance]
                    logger.info("Setting DOCKER_HOST_IP:" +dockerHostIp)
                    additionalVariables.add(RuntimeContextVariable("DOCKER_HOST_IP", dockerHostIp, RuntimeContextVariable.STRING_TYPE, "Docker Host IP", False, RuntimeContextVariable.NO_INCREMENT))
                else:
                    listenAddress = getVariableValue("LISTEN_ADDRESS")
                    additionalVariables.add(RuntimeContextVariable("DOCKER_HOST_IP", listenAddress, RuntimeContextVariable.STRING_TYPE, "Docker Host IP", False, RuntimeContextVariable.NO_INCREMENT))
        except:
            type, value, traceback = sys.exc_info()
            logger.info("read engine session properties error:" + `value`)
            
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
    
    def __imageExists(self):
        imageExists = False
        file = None
        try:
            path = os.path.join(self.__basedir , "docker.images")
            file = open(path, "w")
            image = self.__dockerImage +":" + self.__dockerImageTag
            
            if self.__dockerRegistry:
                image = "*/"+ image
                
            cmdList = ["docker", "images", image]
      
            if self.__sudo:
                cmdList.insert(0, "sudo")
            
            logger.info("Docker local images:" + list2str(cmdList))
            retcode = call(cmdList, stdout=file)
            logger.info("Local images return code:" + `retcode`)
            
            file.flush()
            file.close()
            
            image = self.__dockerImage
            if self.__dockerRegistry:
                image = self.__dockerRegistry +"/" + image
                        
            file = open(path, "r")
            lines = file.readlines()
            for line in lines:
                row = line.split()
                if row:
                    logger.info("Checking cached images:" + list2str(row))
                    if row[0] == image and self.__dockerImageTag == row[1]:
                        logger.info("Cached image matches:" + row[0] +":"+ row[1])
                        imageExists = True
                        break
        finally:
            if file:
                file.close()
            
        return imageExists

    def __containerExists(self):
        containerExists = False
        file = None
        try:
            path = os.path.join(self.__basedir , "docker.ps")
            file = open(path, "w")
            cmdList = ["docker", "ps", "--filter", "name=" + self.__dockerContainerName]
      
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
                if row and row[-1].strip() == self.__dockerContainerName:
                    image = self.__dockerImage + ":" + self.__dockerImageTag
                    if self.__dockerRegistry:
                        image = self.__dockerRegistry + "/" + image
                    if image.find(row[1]) == 0:
                        logger.info("Container exists with matching image:" + self.__dockerContainerName + " " + image)
                        containerExists = True
                        break
                    else:
                        logger.info("No container found with matching image:" + self.__dockerContainerName +" " + image)
        finally:
            if file:
                file.close()
            
        return containerExists
    
    def __build(self):
        "build image"
        
        self.__lock()
        try:
            self.__rm()
            self.__rmi()
        
            cmdList = ["docker", "build", "-t", self.__dockerImage]
            options = getVariableValue("DOCKER_EXTRA_BUILD_OPTIONS")
            if options:
                cmdList = cmdList + options.split()
        
            cmdList.append(self.__dockerContext)
    
            if self.__sudo:
                cmdList.insert(0, "sudo")
            
            logger.info("Build image:" + list2str(cmdList))
            retcode = call(cmdList)
            logger.info("Build image return code:" + `retcode`)
        finally:
            self.__unlock()
            
    def __start(self):
        "start stopped container"
        
        cmdList = ["docker", "start", self.__dockerContainerName]
      
        if self.__sudo:
            cmdList.insert(0, "sudo")
            
        logger.info("Start Docker container:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Start Docker container return code:" + `retcode`)
        if retcode != 0:
            raise "Error return code while starting docker container"

    def __pull(self):
        "pull image from repository"
        self.__lock()
        try:
            image = self.__dockerImage + ":"+ self.__dockerImageTag
            
            if self.__dockerRegistry:
                image = self.__dockerRegistry + "/"  + image
            
            cmdList = ["docker", "pull", image]
      
            if self.__sudo:
                cmdList.insert(0, "sudo")
            
            logger.info("Pull docker image:" + list2str(cmdList))
            retcode = call(cmdList)
            logger.info("Pull docker image return code:" + `retcode`)
        finally:
            self.__unlock()
        
    def __run(self):
        "run docker container"
        
        logger.info("Enter __run")
        cmdList = ["docker", "run"]
        
        network = getVariableValue("DOCKER_CONTAINER_NETWORK_MODE")
        if network:
            cmdList.append(network)
        
        expose = getVariableValue("DOCKER_EXPOSE_PORTS")
        if expose:
            cmdList = cmdList + expose.split()
            
        publish = getVariableValue("DOCKER_PUBLISH_PORTS")
        if publish:
            cmdList = cmdList + publish.split()
            
        volumes = getVariableValue("DOCKER_MOUNT_VOLUMES")
        if volumes:
            cmdList = cmdList + volumes.split()
            
        envs = getVariableValue("DOCKER_ENV_VARIABLES")
        if envs:
            cmdList = cmdList + envs.split()
            
        dns = getVariableValue("DNS_SEARCH_DOMAINS")
        if dns:
            cmdList = cmdList + dns.split()
            
        work = getVariableValue("DOCKER_CONTAINER_WORK_DIR")
        if work:
            cmdList.append("--workdir=" + work)
            
        cmdList.append("--name=" + self.__dockerContainerName)
        cmdList.append("--cidfile=" + self.__cidfile)
        
        options = getVariableValue("DOCKER_EXTRA_RUN_OPTIONS")
        if options:
            options = options.split()
            
            if "--detach=false" in options:
                options.remove("--detach=false")

            if not ("-d" in options) and not ("--detach=true" in options):
                options.append("--detach=true")
                
            cmdList = cmdList + options
        
        image = self.__dockerImage + ":"+ self.__dockerImageTag
        if self.__dockerRegistry:
            image = self.__dockerRegistry +"/" + image
        
        cmdList.append(image)
    
        command = getVariableValue("DOCKER_COMMAND")
        if command:
            cmdList.append(command)
            
        commandArgs = getVariableValue("DOCKER_COMMAND_ARGS")
        if commandArgs:
            args = commandArgs.split()
            if args:
                cmdList.extend(args)
      
        if self.__sudo:
            cmdList.insert(0, "sudo")
            
        logger.info("Run Docker container:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Run Docker container return code:" + `retcode`)
        self.__logs()
        
        if retcode != 0:
            raise "Error return code while running docker container"
            
        logger.info("Exit __run")
        
    def __stop(self):
        "stop docker container"
        
        logger.info("Enter __stop")
        cmdList = ["docker", "stop"]
       
        options = getVariableValue("DOCKER_STOP_OPTIONS")
        if options:
            options = options.split()
            cmdList = cmdList + options
        
        cmdList.append(self.__dockerContainerName)
        
        if self.__sudo:
            cmdList.insert(0, "sudo")
        
        logger.info("Stop docker container:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Stop docker container return code:" + `retcode`)
        
        logger.info("Exit __stop")
        
    def __logs(self):
        "docker container logs"
        file = None
        
        try:
            path = self.__dockerlogs
            if not path:
                path = os.path.join(self.__basedir , "docker.logs")
            file = open(path, "w")
            cmdList = ["docker", "logs", self.__dockerContainerName]
       
            if self.__sudo:
                cmdList.insert(0, "sudo")
        
            call(cmdList, stdout=file, stderr=file)
        except:
            type, value, traceback = sys.exc_info()
            logger.info("docker logs error:" + `value`)
        finally:
            if file:
                file.close()
        
    def __rm(self):
        "remove docker container"
        
        logger.info("Enter __rm")
        cmdList = ["docker", "rm"]
        
        options = getVariableValue("DOCKER_REMOVE_OPTIONS")
        if options:
            options = options.split()
            cmdList = cmdList + options
        
        cmdList.append(self.__dockerContainerName)
        
        if self.__sudo:
            cmdList.insert(0, "sudo")
            
        logger.info("Remove Docker container:" + list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Remove Docker container return code:" + `retcode`)
        logger.info("Exit __rm")
        
    def __rmi(self):
        "remove docker image"
        
        logger.info("Enter __rmi")
        cmdList = ["docker", "rmi"]
        
        options = getVariableValue("DOCKER_REMOVE_IMAGE_OPTIONS")
        if options:
            options = options.split()
            cmdList = cmdList + options
        
        image = self.__dockerImage + ":"+ self.__dockerImageTag
        if self.__dockerRegistry:
            image = self.__dockerRegistry + "/" + image
            
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
        
        reuseContainer = Boolean.parseBoolean(getVariableValue("REUSE_DOCKER_CONTAINER", "false"))
        reuseImage = Boolean.parseBoolean(getVariableValue("REUSE_DOCKER_IMAGE", "true"))
        
        if reuseContainer and self.__containerExists():
            self.__start()
        elif reuseImage and self.__imageExists():
            self.__run()
        elif self.__dockerContext:
            self.__build()
            self.__run()
        else:
            self.__pull()
            self.__run()
      
        logger.info("Exit start")
    
    def stop(self):
        "stop enabler"
        logger.info("Enter stop")
        copyContainerEnvironment()
        
        self.__stop()
        logger.info("Exit stop")
    
        
    def cleanup(self):
        "cleanup"
        
        logger.info("Enter cleanup")
        try:
            copyContainerEnvironment()
            removeContainer = Boolean.parseBoolean(getVariableValue("REMOVE_DOCKER_CONTAINER", "true"))
            if removeContainer:
                self.__rm()
             
            removeImage = Boolean.parseBoolean(getVariableValue("REMOVE_DOCKER_IMAGE", "false"))
            if removeImage:
                self.__rmi()
        except:
            type, value, traceback = sys.exc_info()
            logger.info("cleanup error:" + `value`)
            
        logger.info("Exit cleanup")
               
    def __writeInspect(self):
        "write inspect output"
        
        file = None
        try:
            file = open(self.__inspect, "w")
            cmdList = ["docker", "inspect", self.__dockerContainerName]
            if self.__sudo:
                cmdList.insert(0, "sudo")
                
            retcode = call(cmdList, stdout=file)
        finally:
            if file:
                file.close()
                
    def __writeStats(self):
        "write stats output"
        
        file = None
        try:
            file = open(self.__stats, "w")
            cmdList = ["docker", "stats", "--no-stream=true", self.__dockerContainerName]
            if self.__sudo:
                cmdList.insert(0, "sudo")
                
            retcode = call(cmdList, stdout=file)
        finally:
            if file:
                file.close()

    def __readInspect(self):
        "read inspect output"
        
        self.__running = False
        
        file = None
        self.__inspectInfo = ""
        try:
            path = self.__inspect
            if os.path.isfile(path):
                
                file = open(path, "r")
                lines = file.readlines()
                for line in lines:
                    self.__inspectInfo = self.__inspectInfo + line
                    
                    if not self.__running:
                        match = self.__runningRegex.search(line)
                        if match:
                            self.__running = True
        finally:
            if file:
                file.close()
                
    def __readStats(self):
        "read stats output"
        file = None
        self.__dockerStats.clear()
        
        try:
            path = self.__stats
            if os.path.isfile(path):
                file = open(path, "r")
                lines = file.readlines()
                for line in lines:
                    row = line.replace('%','').replace('/','').split()
                    if row and (len(row) == 15) and (row[0] == self.__dockerContainerName):
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
                             
    def isRunning(self):
        copyContainerEnvironment()  
        
        try:
            self.__writeInspect()
            self.__readInspect()
            if self.__running:
                self.__writeStats()
                self.__readStats()
                self.__logs()
        except:
            type, value, traceback = sys.exc_info()
            logger.info("isRunning error:" + `value`)
        
        return self.__running
    
    def installActivationInfo(self, info):
        "install activation info"

        routes = getVariableValue("HTTP_STATIC_ROUTES")
        if routes:
            routes = routes.split()
            index = 1
            for route in routes:
                propertyName = "HTTP_STATIC_ROUTE" + self.__dockerContainerName + str(index)
                info.setProperty(propertyName, route)
    
    def getStat(self, statName):
        " get statistic"
        return self.__dockerStats[statName]
                

def convertToMB(value, unit):
    unit = unit.lower()
    value = float(value)
    if unit == "gb":
        value = value * 1000.0
    elif unit == "b":
        value = value / 1000.0
        
    return value
        
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
