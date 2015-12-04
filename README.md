### Simple Docker Enabler User Guide

### Introduction
--------------------------------------
`Simple Docker Enabler` is used with `TIBCO Silver Fabric` to manage Docker Containers. This Silver Fabric Enabler uses Docker CLI and TIBCO Silver Fabric Jython Scripting API. Although this Enabler was developed using Docker version 1.9.0 and Silver Fabric Scripting API version 5.7.1, it is expected to  work  with other earlier or later compatible versions of Docker CLI and Silver Fabric Scripting API.

### Building the Enabler
--------------------------------------
This Enabler project builds a `Silver Fabric Enabler Grid Library`. The Enabler Grid Library is built using the provided Ant `build.xml` file. After a successful build, the Enabler Grid Library is available under a folder named `dist` that is created automatically under the project root during the build process. 

### Installing the Enabler
--------------------------------------
Installation of the Silver Fabric Docker Enabler is done by copying the `Silver Fabric Enabler Grid Library` from the `dist` project folder to the `SF_HOME/webapps/livecluster/deploy/resources/gridlib` folder on the Silver Fabric Broker. 

### Enabling Docker on the Silver Fabric Engine host
-----------------------------------------------------------
Each Silver Fabric Engine host needs to be `docker enabled` before it can be used to run Silver Fabric Components based on this enabler. The main steps for docker enabling a Silver Fabric Engine host are as follows:

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
   
After you have completed the steps noted above, restart Silver Fabric Engine Daemon so that it will register the host with Silver Fabric Broker as `Docker Enabled`. It is recommneded that you setup and enable systemd services for Silver Fabric Engine Daemon and Docker Daemon so both these servcies automatially startup when the host operating system is booted up.

### Docker Container Feature Support
---------------------------------------------------
Docker containers provide two key capabilities:
* Operating System level isolation above the kernel layer
* Application level packaging

This Docker Enabler supports both these key Docker capabilities and it does not impose any significant restrictions on native Docker Container features. The only restriction this Enabler imposes is that the Docker Containers managed by this Enabler are always run in `detached` mode.

### Docker Container Instantiation Limits
------------------------------------------
Each Silver Fabric Engine docker enabled host can run Docker containers up to the number of Silver Fabric Engine instances available on the host. Running multiple Docker Containers on a single docker enabled host will eventually bump into CPU and memory limits on the host. The number of Silver Fabric Engine instances configured on a docker enabled host should reflect the CPU and memory resources available on the docker enabled host.

### Configuring Silver Fabric Engine Resource Preference
---------------------------------------------------------

Since not all Silver Fabric Engine hosts managed by a single Silver Fabric Broker may be docker enabled, a [Resource Preference rule] using `Docker Enabled` engine property must be configured in any Silver Fabric Component using this Enabler. This enables Silver Fabric Broker to allocate Components that are based on this Enabler exclusively to docker enabled hosts. Failure to use the suggested [Resource Preference rule] may result in the Components to be allocated to hosts that are not docker enabled, resulting in Silver Fabric Component activation failure. In addition, you may optionally use the `Docker VersionInfo` engine property to select docker enabled hosts with a specific Docker version.

### Pulling Docker Images from a Docker Registry
-------------------------------------------------
Silver Fabric Components using this Enabler must define `DOCKER_IMAGE` runtime context variable. If the value of the `DOCKER_IMAGE` variable points to a Docker `repository:tag` image, the relevant image is pulled down to the docker enabled host. This assumes there is appropriate network and security configuration in place on the docker enabled host such that the image can be pulled down from the specified Docker registry given by the value of the runtime variable `DOCKER_REGISTRY`. If no Docker registry is specified, default Docker Hub registry is used by the Enabler.

### Building Docker Images
------------------------------
If the specified `DOCKER_IMAGE` runtime context variable points to an image that does not exist in the specified Docker registry, and if `DOCKER_CONTEXT` variable points to a folder containing a `Dockerfile` and other optional docker context files, a new Docker image is built locally on the docker enabled host and is tagged with the value specified in the `DOCKER_IMAGE` variable.

### Silver Fabric Enabler Features
----------------------------------
This Enabler supports following Silver Fabric Enabler features:

* HTTP Support
* Application Logging Support
* Component Notification Support
* Archive Management Support

### Silver Fabric Enabler Statistics
-------------------------------------

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

### Docker Container Logs
-----------------------------
Docker Container logs are periodically retrieved and written to the file path specified by the Runtime Context variable `DOCKER_CONTAINER_LOGS`. 

### Silver Fabric Runtime Context Variables
------------------------------
Components using this enabler can configure following Enabler Runtime Context variables:

|Variable Name|Default Value|Type|Description|Export|Auto Increment|
|---|---|---|---|---|---|
|`DOCKER_CONTAINER_NAME`||String|Leave this blank (recommended), if you want unique name to be auto-generated|false|None|
|`DOCKER_REGISTRY`||String|Docker registry for fetching image. For example, https://registryhost:5000/|false|None|
|`DOCKER_IMAGE`||String|Docker registry for fetching image. For example, Docker image e.g centos:latests|false|None|
|`DOCKER_CONTEXT`||String|Docker context path or URL used for building new image|false|None|
|`DOCKER_COMMAND`||String|Docker command executed in Docker container at startup|false|None|
|`DOCKER_COMMAND_ARGS`||String|Docker command args|false|None|
|`DOCKER_CONTAINER_WORK_DIR`||String|Docker container work directory|false|None|
|`DOCKER_CONTAINER_LOGS`|${CONTAINER_WORK_DIR}/docker.logs|String|Docker container logs file|false|None|
|`DOCKER_CONTAINER_NETWORK_MODE`|--net=bridge|String|Docker container network mode|false|None|
|`DOCKER_EXTRA_RUN_OPTIONS`|--detach=true|String|Docker run options (--detach=false option is not supported)|false|None|
|`DOCKER_PUBLISH_PORTS`||String|Docker publish ports --publish ${LISTEN_ADDRESS}:hostPort:containerPort|false|None|
|`DOCKER_EXPOSE_PORTS`||String|Docker expose ports --expose port|false|None|
|`DOCKER_MOUNT_VOLUMES`||String|Docker mount volumes --volume hostdir:containerdir|false|None|
|`DOCKER_ENV_VARIABLES`||String|Docker environment variables --env var=value|false|None|
|`DNS_SEARCH_DOMAINS`||String|DNS search domains format: --dns-search=|false|None|
|`DOCKER_EXTRA_BUILD_OPTIONS`|--quiet=false --no-cache=true --rm=true|String|Docker build options|false|None|
|`DOCKER_STOP_OPTIONS`|--time=30|String|Docker stop options|false|None|
|`DOCKER_REMOVE_OPTIONS`|--force=true --volumes=true|String|Docker remove container options|false|None|
|`DOCKER_REMOVE_IMAGE_OPTIONS`|--force=true|String|Docker remove image options|false|None|
|`USE_SUDO`|false|String|Run Docker with sudo. The sudo must not prompt for password!|false|None|
|`REUSE_DOCKER_IMAGE`|true|String|Reuse existing local Docker image if it exists|false|None|
|`REUSE_DOCKER_CONTAINER`|false|String|Reuse existing local Docker container if it exists|false|None|
|`REMOVE_DOCKER_CONTAINER`|true|String|Remove Docker container on component shutdown|false|None|
|`REMOVE_DOCKER_IMAGE`|false|String|Remove Docker image on component shutdown|false|None|
|`HTTP_STATIC_ROUTES`||String|space separated list: ContextUrl:http://${LISTEN_ADDRESS}:port|false|None|
|`BIND_ON_ALL_LOCAL_ADDRESSES`|false|Environment|Specify if all network interfaces should be bounded for all public port access|false|None|
|`LISTEN_ADDRESS_NET_MASK`||Environment|A comma delimited list of net masks in `CIDR` notation. The first IP address found that matches one of the net masks is used as the listen address. Note that BIND_ON_ALL_LOCAL_ADDRESSES overrides this setting.|false|None|

### Linking Docker Containers
-----------------------------

To link Docker Containers, one can use the native Docker linking mechanism with the understanding that all the linked containers must be restricted to run in the same docker enabled host using Silver Fabric [Resource Preference rule]. Alternatively, Silver Fabric exported Runtime Variables can be defined to export settings from one Docker Container to other Silver Fabric dependent Docker Containers.

It is expected in future as Docker `Swarm` matures, this Enabler will evolve to support native linking across multiple docker enabled hosts that are part of a Swarm.

### Component Examples
------------------------
Below are screenshot images from example Silver Fabric Component configurations using this Enabler. Note the use of custom Runtime Context variables used to define and export (export is set to true) Docker Container configuration from one Docker Container to another Docker Container using Silver Fabric Runtime Context variables export mechanism.

* [MySQL Docker](images/mysql-docker.png)
* [Postgres Docker](images/postgres-docker.png)
* [Mongodb Docker](images/mongodb-docker.png)


[Install Docker]:<https://docs.docker.com/installation/>
[Configure Docker Remote API]:http://www.virtuallyghetto.com/2014/07/quick-tip-how-to-enable-docker-remote-api.html
[Docker and SELinux]:<http://www.projectatomic.io/docs/docker-and-selinux/>
[Resource Preference rule]:<https://github.com/fabrician/docker-enabler/blob/master/src/main/resources/images/docker_resource_preference.gif>
[Docker Daemon reference]:<https://docs.docker.com/engine/reference/commandline/daemon/>
[Docker Storage blog]:<http://www.projectatomic.io/blog/2015/06/notes-on-fedora-centos-and-docker-storage-drivers/>