### Simple Docker Enabler User Guide

### Introduction
--------------------------------------
`Simple Docker Enabler` is used in conjunction with `TIBCO Silver Fabric` to manage a related set of Docker containers. 

This Silver Fabric Enabler uses Docker CLI, Docker Remote API
and TIBCO Silver Fabric Jython Scripting API. This Enabler was developed using Docker version 1.9.0
and Silver Fabric Scripting API version 5.7.1. However, it is expected to  work  with other earlier or later compatible versions of Docker CLI, Remote API
 and Silver Fabric.  It has been tested with Docker version 1.10.1. 

This Enabler is compatible with  `Docker Compose` and `Docker Swarm`.

### Building the Enabler
--------------------------------------
This Enabler project builds a `Silver Fabric Enabler Grid Library`. The Enabler Grid Library can be built using Maven. 
The Grid Library file is created under target directory created by Maven.

### Installing the Enabler
--------------------------------------
Installation of the `Simple Docker Enabler` is done by copying the `Simple Docker Enabler Grid Library` from the `target` 
project folder to the `SF_HOME/webapps/livecluster/deploy/resources/gridlib` folder on the Silver Fabric Broker. 

### Enabling Docker on the Silver Fabric Engine host
-------------------------------------------------------------------
 Silver Fabric Engine host needs to be `Docker enabled` before it can run Silver Fabric Components that use this Enabler. 
The main steps for Docker enabling a Silver Fabric Engine host are as follows:

1. Install `Docker 1.9.0` or later runtime on Silver Fabric Engine host
    * See [Install Docker] for details
2. Configure `Password-less sudo` or non-root Docker access for the OS user running Silver Fabric Engine so the OS user running Silver Fabric Engine is able to run Docker CLI commands without password prompting:
    * If sudo is not required, the password-less requirement still holds
3. Configure `Docker Remote API` to run on a TCP port
    * See [Configure Docker Remote API] for details
4. Configure `Docker Daemon storage-driver Option`
    * Configure Docker dameon `storage-driver` option to use a non-looback driver
    * See [Docker Daemon reference] for details
    * See [Docker Storage blog] for additional details
5. Configure `Docker Daemon selinux-enabled Option`
    * Configure Docker dameon selinux-enabled appropriately. During the development and testing of this Enabler, `--selinux-enabled=false` options was used. 
    * See [Docker and SELinux] for additional information
   
After you have completed the steps noted above, restart Silver Fabric Engine Daemon so that it will register the host with Silver Fabric Broker as `Docker Enabled`. It is recommended that you setup and enable `systemd` services for Silver Fabric Engine Daemon and Docker Daemon so both these services automatically startup when the host operating system is booted up.

### Configuring Main Docker Daemon on the Silver Fabric Engine host
------------------------------------------------------------------------------------------

Create a file [`/etc/sysconfig/docker`](scripts/docker) and specify Docker OPTIONS in this file.

Note the name of the default bridge in the Docker OPTIONS is set to `sfdocker0` and not `docker0`. The reason for this is that the default `docker0` name interferes
with Silver Fabric Engine Daemon startup, which, by default, is configured to use the first network interface available in the alphabetical order. 
To avoid this interference, one solution is to create a network bridge named `sfdocker0` using following commands (tested
on Centos 7):

* sudo brctl addbr sfdocker0
* sudo ip addr add 172.17.0.1/16  dev sfdocker0
* sudo ip link set dev sfdocker0 up

To make this bridge persistent on reboot, create a file named [`/etc//sysconfig/network-scripts/ifcfg-sfdocker0`] (scripts/ifcfg-sfdocker0)

In [`/usr/lib/systemd/system/docker.service`](scripts/docker.service)  file add  `/etc/sysconfig/docker` as the `EnviornmentFile`.
Enable Main Docker daemon service using the command shown below:

* sudo systemctl enable docker.service


### Docker Container Feature Support
---------------------------------------------------

This Docker Enabler does not restrict any native Docker container  features, except that the Docker containers must be run in detached mode.


### Configuring Silver Fabric Engine Resource Preference
-------------------------------------------------------------------------

Since not all Silver Fabric Engine hosts managed by a single Silver Fabric Broker may be Docker enabled, a [Resource Preference rule] using `Docker Enabled` engine property must be configured in any Silver Fabric Component using this Enabler. This enables Silver Fabric Broker to allocate Components that are based on this Enabler exclusively to Docker enabled hosts. Failure to use the suggested [Resource Preference rule] may result in the Components to be allocated to hosts that are not Docker enabled, resulting in Silver Fabric Component activation failure. In addition, you may optionally use the `Docker VersionInfo` engine property to select Docker enabled hosts with a specific Docker version.

### Pulling Docker Images from a Docker Registry
-------------------------------------------------
 If the value of the `DOCKER_IMAGE` variable points to a Docker `repository:tag` image, the relevant image is pulled down to the Docker enabled host. 
 This assumes there is appropriate network and security configuration in place on the Docker enabled 
 host such that the image can be pulled down from the specified Docker registry given by the value of the runtime context variable `DOCKER_REGISTRY`. 
 If no Docker registry is specified, default Docker Hub registry is used by the Enabler. 
 
### Building Docker Images
------------------------------
If the specified `DOCKER_IMAGE` runtime context variable points to an image that does not exist in the specified Docker registry, 
and if `DOCKER_CONTEXT` variable points to a folder containing a `Dockerfile` and other optional Docker context files, 
a new Docker image is built locally on the Docker enabled host and is tagged with the value specified in the `DOCKER_IMAGE` variable.

### Silver Fabric Enabler Features
----------------------------------
This Enabler supports following Silver Fabric Enabler features:

* HTTP Support
* Application Logging Support
* Component Notification Support
* Archive Management Support

The Enabler currently does not implement any of the methods required for archive management. It is assumed that the application archives are managed 
directly through appropriate in the image or are managed by using a Dockerfile.

If needed, archive management can be implemented using Component Scripting methods inside a Component Jython script.

### Silver Fabric Enabler Statistics
-------------------------------------------

Components using this Enabler can track following Docker container statistics:

| Docker Container Statistic|Description|
|---------|-----------|
|`Docker CPU Usage %`|Docker CPU usage percentage|
|`Docker Memory Usage %`|Docker memory usage percentage|
|`Docker Memory Usage (MB)`|Docker memory usage (MB)|
|`Docker Memory Limit (MB)`|Docker Memory Limit (MB)|
|`Docker Network Input (MB)`|Docker network input (MB)|
|`Docker Network Output (MB)`|Docker network output (MB)|
|`Docker Block Output (MB)`|Docker block device output (MB)|
|`Docker Block Input (MB)`|Docker block device input (MB)|

If a Component using this Enabler specifies multiple Docker containers, the Enabler statistics contain a sum of the statistics from all the managed Docker containers.

### Docker Container Logs
-----------------------------
Docker container logs are periodically retrieved and written to the file path specified by the Runtime Context variable `DOCKER_CONTAINER_LOGS`. 

### Silver Fabric Runtime Context Variables
--------------------------------------------------------
This Enabler supports two mutually exclusive approaches for specifying the Docker container set managed by the Component using this Enabler:

* Docker containers may be specified in a `Docker Compose` file included within the Component.
  Under this approach, the variable DOCKER_COMPOSE_FILE must be specified, and  other
 DOCKER_COMPOSE variables may be used to specify appropriate values.

* Alternatively, the Docker container set maybe specified using Enabler runtime context variables without the  DOCKER_COMPOSE prefix. 
Under this approach, DOCKER_IMAGE must be specified.

 If both approaches are specified, Docker Compose approach takes precedence. The relative folder containing Docker compose file within the Component 
must contain all the Docker compose context files. 

Components using this Enabler may need to configure one or more of following Enabler runtime context variables.

All Enabler Runtime Context variables below marked with the tag [CSV] under description can be specified as comma separated value list, 
with each comma separated value applicable to corresponding image list entry.

If comma separated value list is specified for DOCKER_IMAGE, then all other variables marked [CSV] must have matching number of entries, 
except if an entry is also marked DEFAULT whereby a single value can apply across all image list entries.
If an entry in the values list is empty it can be marked with just a comma. If a single value is specified, no comma is needed at the end of the value.

There is a special implicitly runtime context variable named DOCKER_HOST_IP.
If the host has multiple secondary IP addresses associated with the primary network interface, then
this Enabler assigns the secondary IP corresponding to the Silver Fabric engine instance number to the DOCKER_HOST_IP variable. 

Multiple values in a CSV list entry corresponding to a single image must be separated with SPACES, NOT commas.

### Runtime Variable List:
--------------------------------

|Variable Name|Default Value|Type|Description|Export|Auto Increment|
|---|---|---|---|---|---|
|`DOCKER_COMPOSE_FILE`|| String| Docker compose (docker-compose.yml) file relative path in the Component. |false|None|
|`DOCKER_COMPOSE_PROJECT`|| String| Docker compose project name. Defaults to component name. |false|None|
|`DOCKER_COMPOSE_PATH`|/usr/local/bin/docker-compose| String| Docker compose executable path |false|None|
|`DOCKER_CONTAINER_NAME`|| String| [CSV] Leave this blank, if you want unique name to be auto-generated|false|None|
|`DOCKER_REGISTRY`||String| [CSV]  [DEFAULT] Docker registry for fetching image. For example, https://registryhost:5000/|false|None|
|`DOCKER_IMAGE`||String| [CSV] Docker registry for fetching image. For example, Docker image e.g centos:latests|false|None|
|`DOCKER_CONTEXT`||String| [CSV] Docker context path or URL used for building new image|false|None|
|`DOCKER_COMMAND`||String| [CSV] Docker command executed in Docker container at startup|false|None|
|`DOCKER_COMMAND_ARGS`||String| [CSV] Docker command args|false|None|
|`DOCKER_CONTAINER_HOSTNAME`||String| [CSV] Docker container hostname|false|None|
|`DOCKER_CONTAINER_WORK_DIR`||String| [CSV] Docker container work directory|false|None|
|`DOCKER_CONTAINER_LOGS`|${CONTAINER_WORK_DIR}/docker.log|String|Docker container logs file|false|None|
|`DOCKER_CONTAINER_NETWORK_MODE`|[CSV]  [DEFAULT] --net=bridge|String|Docker container network mode|false|None|
|`DOCKER_EXTRA_RUN_OPTIONS`|--detach=true|String|[CSV]  [DEFAULT] Docker run options (--detach=false option is not supported)|false|None|
|`DOCKER_PUBLISH_PORTS`||String|[CSV] Docker publish ports --publish ${LISTEN_ADDRESS}:hostPort:containerPort|false|None|
|`DOCKER_EXPOSE_PORTS`||String|[CSV] Docker expose ports --expose port|false|None|
|`DOCKER_MOUNT_VOLUMES`||String|[CSV] Docker mount volumes --volume hostdir:containerdir|false|None|
|`DOCKER_VOLUMES_FROM`||String|[CSV] Docker volumes from --volume-from foo|false|None|
|`DOCKER_ADD_HOST`||String|[CSV] Docker add host --add-host=host:ip|false|None|
|`DOCKER_ENV_VARIABLES`||String| [CSV] Docker environment variables --env var=value|false|None|
|`DOCKER_ENV_FILE`||String| [CSV] Docker environment file  --env-file=file|false|None|
|`DOCKER_LINK`||String| [CSV] Docker container links, e.g --link foo|false|None|
|`DNS_SEARCH_DOMAINS`||String| [CSV] DNS search domains format: --dns-search=|false|None|
|`DNS_SERVERS`||String| [CSV] Custom DNS server e.g. --dns server|false|None|
|`DOCKER_EXTRA_BUILD_OPTIONS`|--quiet=false --no-cache=true --rm=true|String|[CSV]  [DEFAULT]  Docker build options|false|None|
|`DOCKER_STOP_OPTIONS`|--time=30|String|Docker stop options|false|None|
|`DOCKER_REMOVE_OPTIONS`|--force=true --volumes=true|String|Docker remove container options|false|None|
|`DOCKER_REMOVE_IMAGE_OPTIONS`|--force=true|String|Docker remove image options|false|None|
|`APP_RUNNING_PORTS`|--force=true|String| [CSV] Docker container port used to check if container app is running|false|None|
|`USE_SUDO`|false|String|Run Docker with sudo. The sudo must not prompt for password!|false|None|
|`REUSE_DOCKER_IMAGE`|true|String|Reuse existing local Docker image if it exists|false|None|
|`REUSE_DOCKER_CONTAINER`|false|String|Reuse existing local Docker container if it exists|false|None|
|`REMOVE_DOCKER_CONTAINER`|true|String|Remove Docker container on component shutdown|false|None|
|`REMOVE_DOCKER_IMAGE`|false|String|Remove Docker image on component shutdown|false|None|
|`DOCKER_PORT`|2375|String|Docker daemon port on local host|false|None|
|`HTTP_STATIC_ROUTES`||String|space separated list: ContextUrl:http://${LISTEN_ADDRESS}:port|false|None|
|`BIND_ON_ALL_LOCAL_ADDRESSES`|false|Environment|Specify if all network interfaces should be bounded for all public port access|false|None|
|`LISTEN_ADDRESS_NET_MASK`||Environment|A comma delimited list of net masks in `CIDR` notation. The first IP address found that matches one of the net masks is used as the listen address. Note that BIND_ON_ALL_LOCAL_ADDRESSES overrides this setting.|false|None|

### Example Variables:
------------------------------
|Variable Name|Value|
|------|-----|
|`DOCKER_IMAGE`|boss, oracle, foo|
|`DOCKER_REGISTRY`|dockerregistry.example.com:5000|
|`DOCKER_PUBLISH_PORTS`|--publish ${DOCKER_HOST_IP}:8080:8080 --publish ${DOCKER_HOST_IP}:1521:1521, --publish ${DOCKER_HOST_IP}:389:389, --publish ${DOCKER_HOST_IP}:17080:17080|


### Native Linking of Docker Containers
---------------------------------------------------

To link Docker containers through Docker native Link capability, use DOCKER_LINK Runtime variable specified in the variable list.

### Component Examples
------------------------
Below are screenshot images from example Silver Fabric Component configurations using this Enabler. 
Note the use of custom Silver Fabric Runtime Context variables used to define and export (export is set to true) 
Docker container configuration from one Docker container to another Docker container using Silver Fabric Runtime Context variables export mechanism.

* [Docker Compose](images/docker-compose-example.png)
* [MySQL Docker](images/mysql-docker.png)
* [Postgres Docker](images/postgres-docker.png)
* [Mongodb Docker](images/mongodb-docker.png)


[Install Docker]:<https://docs.docker.com/installation/>
[Configure Docker Remote API]:http://www.virtuallyghetto.com/2014/07/quick-tip-how-to-enable-docker-remote-api.html
[Docker and SELinux]:<http://www.projectatomic.io/docs/docker-and-selinux/>
[Resource Preference rule]:<https://github.com/fabrician/docker-enabler/blob/master/src/main/resources/images/docker_resource_preference.gif>
[Docker Daemon reference]:<https://docs.docker.com/engine/reference/commandline/daemon/>
[Docker Storage blog]:<http://www.projectatomic.io/blog/2015/06/notes-on-fedora-centos-and-docker-storage-drivers/>