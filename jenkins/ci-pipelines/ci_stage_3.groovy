/* Copyright ETSI Contributors and Others
 *
 * All Rights Reserved.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License"); you may
 *   not use this file except in compliance with the License. You may obtain
 *   a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 *   License for the specific language governing permissions and limitations
 *   under the License.
 */

properties([
    parameters([
        string(defaultValue: env.GERRIT_BRANCH, description: '', name: 'GERRIT_BRANCH'),
        string(defaultValue: 'system', description: '', name: 'NODE'),
        string(defaultValue: '', description: '', name: 'BUILD_FROM_SOURCE'),
        string(defaultValue: 'unstable', description: '', name: 'REPO_DISTRO'),
        string(defaultValue: '', description: '', name: 'COMMIT_ID'),
        string(defaultValue: '-stage_2', description: '', name: 'UPSTREAM_SUFFIX'),
        string(defaultValue: 'pubkey.asc', description: '', name: 'REPO_KEY_NAME'),
        string(defaultValue: 'release', description: '', name: 'RELEASE'),
        string(defaultValue: '', description: '', name: 'UPSTREAM_JOB_NAME'),
        string(defaultValue: '', description: '', name: 'UPSTREAM_JOB_NUMBER'),
        string(defaultValue: '', description: '', name: 'UPSTREAM_JOB_NUMBER'),
        string(defaultValue: 'OSMETSI', description: '', name: 'GPG_KEY_NAME'),
        string(defaultValue: 'artifactory-osm', description: '', name: 'ARTIFACTORY_SERVER'),
        string(defaultValue: 'osm-stage_4', description: '', name: 'DOWNSTREAM_STAGE_NAME'),
        string(defaultValue: 'testing-daily', description: '', name: 'DOCKER_TAG'),
        booleanParam(defaultValue: false, description: '', name: 'SAVE_CONTAINER_ON_FAIL'),
        booleanParam(defaultValue: false, description: '', name: 'SAVE_CONTAINER_ON_PASS'),
        booleanParam(defaultValue: true, description: '', name: 'SAVE_ARTIFACTS_ON_SMOKE_SUCCESS'),
        booleanParam(defaultValue: true, description: '',  name: 'DO_BUILD'),
        booleanParam(defaultValue: true, description: '', name: 'DO_INSTALL'),
        booleanParam(defaultValue: true, description: '', name: 'DO_DOCKERPUSH'),
        booleanParam(defaultValue: false, description: '', name: 'SAVE_ARTIFACTS_OVERRIDE'),
        string(defaultValue: '/home/jenkins/hive/openstack-etsi.rc', description: '', name: 'HIVE_VIM_1'),
        booleanParam(defaultValue: true, description: '', name: 'DO_ROBOT'),
        string(defaultValue: 'sanity', description: 'sanity/regression/daily are the common options', name: 'ROBOT_TAG_NAME'),
        string(defaultValue: '/home/jenkins/hive/robot-systest.cfg', description: '', name: 'ROBOT_VIM'),
        string(defaultValue: '/home/jenkins/hive/port-mapping-etsi-vim.yaml', description: 'Port mapping file for SDN assist in ETSI VIM', name: 'ROBOT_PORT_MAPPING_VIM'),
        string(defaultValue: '/home/jenkins/hive/kubeconfig.yaml', description: '', name: 'KUBECONFIG'),
        string(defaultValue: '/home/jenkins/hive/clouds.yaml', description: '', name: 'CLOUDS'),
        string(defaultValue: 'Default', description: '', name: 'INSTALLER'),
        string(defaultValue: '100.0', description: '% passed Robot tests to mark the build as passed', name: 'ROBOT_PASS_THRESHOLD'),
        string(defaultValue: '80.0', description: '% passed Robot tests to mark the build as unstable (if lower, it will be failed)', name: 'ROBOT_UNSTABLE_THRESHOLD'),
    ])
])


////////////////////////////////////////////////////////////////////////////////////////
// Helper Functions
////////////////////////////////////////////////////////////////////////////////////////
def run_robot_systest(tagName,testName,osmHostname,prometheusHostname,prometheus_port=null,envfile=null,portmappingfile=null,jujudata=null,kubeconfig=null,clouds=null,hostfile=null,jujuPassword=null,pass_th='0.0',unstable_th='0.0') {
    tempdir = sh(returnStdout: true, script: "mktemp -d").trim()
    if ( !envfile )
    {
        sh(script: "touch ${tempdir}/env")
        envfile="${tempdir}/env"
    }
    PROMETHEUS_PORT_VAR = ""
    if ( prometheusPort != null) {
        PROMETHEUS_PORT_VAR = "--env PROMETHEUS_PORT="+prometheusPort
    }
    hostfilemount=""
    if ( hostfile ) {
        hostfilemount="-v "+hostfile+":/etc/hosts"
    }

    JUJU_PASSWORD_VAR = ""
    if ( jujuPassword != null) {
        JUJU_PASSWORD_VAR = "--env JUJU_PASSWORD="+jujuPassword
    }

    try {
        sh "docker run --env OSM_HOSTNAME=${osmHostname} --env PROMETHEUS_HOSTNAME=${prometheusHostname} ${PROMETHEUS_PORT_VAR} ${JUJU_PASSWORD_VAR} --env-file ${envfile} -v ${clouds}:/etc/openstack/clouds.yaml -v ${jujudata}:/root/.local/share/juju -v ${kubeconfig}:/root/.kube/config -v ${tempdir}:/robot-systest/reports -v ${portmappingfile}:/root/port-mapping.yaml ${hostfilemount} opensourcemano/tests:${tagName} -c -t ${testName}"
    } finally {
        sh "cp ${tempdir}/* ."
        outputDirectory = sh(returnStdout: true, script: "pwd").trim()
        println ("Present Directory is : ${outputDirectory}")
        step([
            $class : 'RobotPublisher',
            outputPath : "${outputDirectory}",
            outputFileName : "*.xml",
            disableArchiveOutput : false,
            reportFileName : "report.html",
            logFileName : "log.html",
            passThreshold : pass_th,
            unstableThreshold: unstable_th,
            otherFiles : "*.png",
        ])
    }
}

def archive_logs(remote) {

    sshCommand remote: remote, command: '''mkdir -p logs'''
    if (useCharmedInstaller) {
        sshCommand remote: remote, command: '''
            for container in `kubectl get pods -n osm | grep -v operator | grep -v NAME| awk '{print $1}'`; do
                logfile=`echo $container | cut -d- -f1`
                echo "Extracting log for $logfile"
                kubectl logs -n osm $container --timestamps=true 2>&1 > logs/$logfile.log
            done
        '''
    } else {
        sshCommand remote: remote, command: '''
            for deployment in `kubectl -n osm get deployments | grep -v operator | grep -v NAME| awk '{print $1}'`; do
                echo "Extracting log for $deployment"
                kubectl -n osm logs deployments/$deployment --timestamps=true --all-containers 2>&1 > logs/$deployment.log
            done
        '''
        sshCommand remote: remote, command: '''
            for statefulset in `kubectl -n osm get statefulsets | grep -v operator | grep -v NAME| awk '{print $1}'`; do
                echo "Extracting log for $statefulset"
                kubectl -n osm logs statefulsets/$statefulset --timestamps=true --all-containers 2>&1 > logs/$statefulset.log
            done
        '''
    }

    sh "rm -rf logs"
    sshCommand remote: remote, command: '''ls -al logs'''
    sshGet remote: remote, from: 'logs', into: '.', override: true
    sh "cp logs/* ."
    archiveArtifacts artifacts: '*.log'
}

def get_value(key, output) {
    for (String line : output.split( '\n' )) {
        data = line.split( '\\|' )
        if (data.length > 1) {
            if ( data[1].trim() == key ) {
                return data[2].trim()
            }
        }
    }
}

////////////////////////////////////////////////////////////////////////////////////////
// Main Script
////////////////////////////////////////////////////////////////////////////////////////
node("${params.NODE}") {

    INTERNAL_DOCKER_REGISTRY = 'osm.etsi.org:5050/devops/cicd/'
    INTERNAL_DOCKER_PROXY = 'http://172.21.1.1:5000'
    SSH_KEY = '~/hive/cicd_rsa'
    sh 'env'

    tag_or_branch = params.GERRIT_BRANCH.replaceAll(/\./,"")

    stage("Checkout") {
        checkout scm
    }

    ci_helper = load "jenkins/ci-pipelines/ci_helper.groovy"

    def upstream_main_job = params.UPSTREAM_SUFFIX

    // upstream jobs always use merged artifacts
    upstream_main_job += '-merge'
    container_name_prefix = "osm-${tag_or_branch}"
    container_name = "${container_name_prefix}"

    keep_artifacts = false
    if ( JOB_NAME.contains('merge') ) {
        container_name += "-merge"

        // On a merge job, we keep artifacts on smoke success
        keep_artifacts = params.SAVE_ARTIFACTS_ON_SMOKE_SUCCESS
    }
    container_name += "-${BUILD_NUMBER}"

    server_id = null
    http_server_name = null
    devopstempdir = null
    jujutempdir = null
    useCharmedInstaller = params.INSTALLER.equalsIgnoreCase("charmed")

    try {
        builtModules = [:]
///////////////////////////////////////////////////////////////////////////////////////
// Fetch stage 2 .deb artifacts
///////////////////////////////////////////////////////////////////////////////////////
        stage("Copy Artifacts") {
            // cleanup any previous repo
            sh 'rm -rf repo'
            dir("repo") {
                packageList = []
                dir("${RELEASE}") {
                    RELEASE_DIR = sh(returnStdout:true,  script: 'pwd').trim()

                    // check if an upstream artifact based on specific build number has been requested
                    // This is the case of a merge build and the upstream merge build is not yet complete (it is not deemed
                    // a successful build yet). The upstream job is calling this downstream job (with the its build artifiact)
                    def upstreamComponent=""
                    if ( params.UPSTREAM_JOB_NAME ) {
                        println("Fetching upstream job artifact from ${params.UPSTREAM_JOB_NAME}")

                        step ([$class: 'CopyArtifact',
                               projectName: "${params.UPSTREAM_JOB_NAME}",
                               selector: [$class: 'SpecificBuildSelector',
                               buildNumber: "${params.UPSTREAM_JOB_NUMBER}"]
                              ])

                        upstreamComponent = ci_helper.get_mdg_from_project(
                            ci_helper.get_env_value('build.env','GERRIT_PROJECT'))
                        def buildNumber = ci_helper.get_env_value('build.env','BUILD_NUMBER')
                        dir("$upstreamComponent") {
                            // the upstream job name contains suffix with the project. Need this stripped off
                            def project_without_branch = params.UPSTREAM_JOB_NAME.split('/')[0]
                            def packages = ci_helper.get_archive(params.ARTIFACTORY_SERVER,
                                upstreamComponent,
                                GERRIT_BRANCH,
                                "${project_without_branch} :: ${GERRIT_BRANCH}",
                                buildNumber)

                            packageList.addAll(packages)
                            println("Fetched pre-merge ${params.UPSTREAM_JOB_NAME}: ${packages}")
                        }
                    }

                    parallelSteps = [:]
                    def list = ["RO", "osmclient", "IM", "devops", "MON", "N2VC", "NBI", "common", "LCM", "POL", "NG-UI", "PLA", "tests"]
                    if (upstreamComponent.length()>0) {
                        println("Skipping upstream fetch of "+upstreamComponent)
                        list.remove(upstreamComponent)
                    }
                    for (buildStep in list) {
                        def component = buildStep
                        parallelSteps[component] = {
                            dir("$component") {
                                println("Fetching artifact for ${component}")
                                step ([$class: 'CopyArtifact',
                                       projectName: "${component}${upstream_main_job}/${GERRIT_BRANCH}"])

                                // grab the archives from the stage_2 builds (ie. this will be the artifacts stored based on a merge)
                                def packages = ci_helper.get_archive(params.ARTIFACTORY_SERVER,
                                    component,
                                    GERRIT_BRANCH,
                                    "${component}${upstream_main_job} :: ${GERRIT_BRANCH}",
                                    ci_helper.get_env_value('build.env','BUILD_NUMBER'))
                                packageList.addAll(packages)
                                println("Fetched ${component}: ${packages}")
                                sh "rm -rf dists"
                            }
                        }
                    }
                    parallel parallelSteps

///////////////////////////////////////////////////////////////////////////////////////
// Create Devops APT repository
///////////////////////////////////////////////////////////////////////////////////////
                    sh "mkdir -p pool"
                    for (component in [ "devops", "IM", "osmclient" ]) {
                        sh "ls -al ${component}/pool/"
                        sh "cp -r ${component}/pool/* pool/"
                        sh "dpkg-sig --sign builder -k ${GPG_KEY_NAME} pool/${component}/*"
                        sh "mkdir -p dists/${params.REPO_DISTRO}/${component}/binary-amd64/"
                        sh "apt-ftparchive packages pool/${component} > dists/${params.REPO_DISTRO}/${component}/binary-amd64/Packages"
                        sh "gzip -9fk dists/${params.REPO_DISTRO}/${component}/binary-amd64/Packages"
                    }

                    // create and sign the release file
                    sh "apt-ftparchive release dists/${params.REPO_DISTRO} > dists/${params.REPO_DISTRO}/Release"
                    sh "gpg --yes -abs -u ${GPG_KEY_NAME} -o dists/${params.REPO_DISTRO}/Release.gpg dists/${params.REPO_DISTRO}/Release"

                    // copy the public key into the release folder
                    // this pulls the key from the home dir of the current user (jenkins)
                    sh "cp ~/${REPO_KEY_NAME} 'OSM ETSI Release Key.gpg'"
                    sh "cp ~/${REPO_KEY_NAME} ."
                }

                // start an apache server to serve up the packages
                http_server_name = "${container_name}-apache"

                pwd = sh(returnStdout:true,  script: 'pwd').trim()
                repo_port = sh(script: 'echo $(python -c \'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()\');', returnStdout: true).trim()
                repo_base_url = ci_helper.start_http_server(pwd,http_server_name,repo_port)
                NODE_IP_ADDRESS=sh(returnStdout: true, script:
                    "echo ${SSH_CONNECTION} | awk '{print \$3}'").trim()
            }

            // Unpack devops package into temporary location so that we use it from upstream if it was part of a patch
            osm_devops_dpkg = sh(returnStdout: true, script: "find ./repo/release/pool/ -name osm-devops*.deb").trim()
            devopstempdir = sh(returnStdout: true, script: "mktemp -d").trim()
            println("Extracting local devops package ${osm_devops_dpkg} into ${devopstempdir} for docker build step")
            sh "dpkg -x ${osm_devops_dpkg} ${devopstempdir}"
            OSM_DEVOPS="${devopstempdir}/usr/share/osm-devops"
            // Convert URLs from stage 2 packages to arguments that can be passed to docker build
            for (remotePath in packageList) {
                packageName=remotePath.substring(remotePath.lastIndexOf('/')+1)
                packageName=packageName.substring(0,packageName.indexOf('_'))
                builtModules[packageName]=remotePath
            }
        }

///////////////////////////////////////////////////////////////////////////////////////
// Build docker containers
///////////////////////////////////////////////////////////////////////////////////////
        dir(OSM_DEVOPS) {
            def remote = [:]
            error = null
            if ( params.DO_BUILD ) {
                withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'gitlab-registry',
                                usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                    sh "docker login ${INTERNAL_DOCKER_REGISTRY} -u ${USERNAME} -p ${PASSWORD}"
                }
                moduleBuildArgs = ""
                for (packageName in builtModules.keySet()) {
                    envName=packageName.replaceAll("-","_").toUpperCase()+"_URL"
                    moduleBuildArgs += " --build-arg ${envName}=" + builtModules[packageName]
                }
                dir ("docker") {
                    stage("Build") {
                        containerList = sh(returnStdout: true, script:
                            "find . -name Dockerfile -printf '%h\\n' | sed 's|\\./||'")
                        containerList=Arrays.asList(containerList.split("\n"))
                        print(containerList)
                        parallelSteps = [:]
                        for (buildStep in containerList) {
                            def module = buildStep
                            def moduleName = buildStep.toLowerCase()
                            def moduleTag = container_name
                            parallelSteps[module] = {
                                dir("$module") {
                                    sh "docker build -t opensourcemano/${moduleName}:${moduleTag} ${moduleBuildArgs} ."
                                    println("Tagging ${moduleName}:${moduleTag}")
                                    sh "docker tag opensourcemano/${moduleName}:${moduleTag} ${INTERNAL_DOCKER_REGISTRY}opensourcemano/${moduleName}:${moduleTag}"
                                    sh "docker push ${INTERNAL_DOCKER_REGISTRY}opensourcemano/${moduleName}:${moduleTag}"
                                }
                            }
                        }
                        parallel parallelSteps
                    }
                }
            } // if ( params.DO_BUILD )

            if ( params.DO_INSTALL ) {
///////////////////////////////////////////////////////////////////////////////////////
// Launch VM
///////////////////////////////////////////////////////////////////////////////////////
                stage("Spawn Remote VM") {
                    println("Launching new VM")
                    output=sh(returnStdout: true, script: """#!/bin/sh -e
                        for line in `grep OS ~/hive/robot-systest.cfg | grep -v OS_CLOUD` ; do export \$line ; done
                        openstack server create --flavor osm.sanity \
                                                --image ubuntu18.04 \
                                                --key-name CICD \
                                                --property build_url="${BUILD_URL}" \
                                                --nic net-id=osm-ext \
                                                ${container_name}
                    """).trim()

                    server_id = get_value('id', output)

                    if (server_id == null) {
                        println("VM launch output: ")
                        println(output)
                        throw new Exception("VM Launch failed")
                    }
                    println("Target VM is ${server_id}, waiting for IP address to be assigned")

                    IP_ADDRESS = ""

                    while (IP_ADDRESS == "") {
                        output=sh(returnStdout: true, script: """#!/bin/sh -e
                            for line in `grep OS ~/hive/robot-systest.cfg | grep -v OS_CLOUD` ; do export \$line ; done
                            openstack server show ${server_id}
                        """).trim()
                        IP_ADDRESS = get_value('addresses', output)
                    }
                    IP_ADDRESS = IP_ADDRESS.split('=')[1]
                    println("Waiting for VM at ${IP_ADDRESS} to be reachable")

                    alive = false
                    while (! alive) {
                        output=sh(returnStdout: true, script: "sleep 1 ; nc -zv ${IP_ADDRESS} 22 2>&1 || true").trim()
                        println("output is [$output]")
                        alive = output.contains("succeeded")
                    }
                    println("VM is ready and accepting ssh connections")
                } // stage("Spawn Remote VM")

///////////////////////////////////////////////////////////////////////////////////////
// Installation
///////////////////////////////////////////////////////////////////////////////////////
                stage("Install") {
                    commit_id = ''
                    repo_distro = ''
                    repo_key_name = ''
                    release = ''

                    if ( params.COMMIT_ID )
                    {
                        commit_id = "-b ${params.COMMIT_ID}"
                    }

                    if ( params.REPO_DISTRO )
                    {
                        repo_distro = "-r ${params.REPO_DISTRO}"
                    }

                    if ( params.REPO_KEY_NAME )
                    {
                        repo_key_name = "-k ${params.REPO_KEY_NAME}"
                    }

                    if ( params.RELEASE )
                    {
                        release = "-R ${params.RELEASE}"
                    }

                    if ( params.REPOSITORY_BASE )
                    {
                        repo_base_url = "-u ${params.REPOSITORY_BASE}"
                    }
                    else
                    {
                        repo_base_url = "-u http://${NODE_IP_ADDRESS}:${repo_port}"
                    }

                    remote.name = container_name
                    remote.host = IP_ADDRESS
                    remote.user = 'ubuntu'
                    remote.identityFile = SSH_KEY
                    remote.allowAnyHosts = true
                    remote.logLevel = 'INFO'
                    remote.pty = true

                    sshCommand remote: remote, command: """
                        wget https://osm-download.etsi.org/ftp/osm-10.0-ten/install_osm.sh
                        chmod +x ./install_osm.sh
                        sed -i '1 i\\export PATH=/snap/bin:\${PATH}' ~/.bashrc
                    """

                    if ( useCharmedInstaller ) {
                        // Use local proxy for docker hub
                        sshCommand remote: remote, command: '''
                            sudo snap install microk8s --classic --channel=1.19/stable
                            sudo sed -i "s|https://registry-1.docker.io|http://172.21.1.1:5000|" /var/snap/microk8s/current/args/containerd-template.toml
                            sudo systemctl restart snap.microk8s.daemon-containerd.service
                            sudo snap alias microk8s.kubectl kubectl
                        '''

                        withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'gitlab-registry',
                                        usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                            sshCommand remote: remote, command: """
                                ./install_osm.sh -y \
                                    ${repo_base_url} \
                                    ${repo_key_name} \
                                    ${release} -r unstable \
                                    --charmed  \
                                    --registry ${USERNAME}:${PASSWORD}@${INTERNAL_DOCKER_REGISTRY} \
                                    --tag ${container_name}
                            """
                        }
                        prometheusHostname = "prometheus."+IP_ADDRESS+".nip.io"
                        prometheusPort = 80
                        osmHostname = "nbi."+IP_ADDRESS+".nip.io:443"
                    } else {
                        // Run -k8s installer here specifying internal docker registry and docker proxy
                        withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'gitlab-registry',
                                        usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                            sshCommand remote: remote, command: """
                                ./install_osm.sh -y \
                                    ${repo_base_url} \
                                    ${repo_key_name} \
                                    ${release} -r unstable \
                                    -d ${USERNAME}:${PASSWORD}@${INTERNAL_DOCKER_REGISTRY} \
                                    -p ${INTERNAL_DOCKER_PROXY} \
                                    -t ${container_name} \
                                    --nocachelxdimages
                            """
                        }
                        prometheusHostname = IP_ADDRESS
                        prometheusPort = 9091
                        osmHostname = IP_ADDRESS
                    }
                } // stage("Install")
///////////////////////////////////////////////////////////////////////////////////////
// Health check of installed OSM in remote vm
///////////////////////////////////////////////////////////////////////////////////////
                stage("OSM Health") {
                    stackName = "osm"
                    sshCommand remote: remote, command: """
                        /usr/share/osm-devops/installers/osm_health.sh -k -s ${stackName}
                    """
                } // stage("OSM Health")
///////////////////////////////////////////////////////////////////////////////////////
// Get juju data from installed OSM in remote vm
///////////////////////////////////////////////////////////////////////////////////////
                jujutempdir = sh(returnStdout: true, script: "mktemp -d").trim()
                jujudatafolder = jujutempdir + '/juju'
                homefolder = sshCommand remote: remote, command: 'echo ${HOME}'
                sshGet remote: remote, from: homefolder + '/.local/share/juju', into: jujutempdir, override: true
            } // if ( params.DO_INSTALL )


///////////////////////////////////////////////////////////////////////////////////////
// Execute Robot tests
///////////////////////////////////////////////////////////////////////////////////////
            stage_archive = false
            if ( params.DO_ROBOT ) {
                try {
                    stage("System Integration Test") {
                        if ( useCharmedInstaller ) {
                            tempdir = sh(returnStdout: true, script: "mktemp -d").trim()
                            sh(script: "touch ${tempdir}/hosts")
                            hostfile="${tempdir}/hosts"
                            sh """cat << EOF > ${hostfile}
127.0.0.1           localhost
${remote.host}      prometheus.${remote.host}.nip.io nbi.${remote.host}.nip.io
EOF"""
                        } else {
                            hostfile=null
                        }

                        jujuPassword=sshCommand remote: remote, command: """
                            echo `juju gui 2>&1 | grep password | cut -d: -f2`
                        """

                        run_robot_systest(
                            container_name,
                            params.ROBOT_TAG_NAME,
                            osmHostname,
                            prometheusHostname,
                            prometheusPort,
                            params.ROBOT_VIM,
                            params.ROBOT_PORT_MAPPING_VIM,
                            jujudatafolder,
                            params.KUBECONFIG,
                            params.CLOUDS,
                            hostfile,
                            jujuPassword,
                            params.ROBOT_PASS_THRESHOLD,
                            params.ROBOT_UNSTABLE_THRESHOLD
                        )
                    } // stage("System Integration Test")
                } finally {
                    stage("Archive Container Logs") {
                        // Archive logs to containers_logs.txt
                        archive_logs(remote)
                        if ( ! currentBuild.result.equals('FAILURE') ) {
                            stage_archive = keep_artifacts
                        } else {
                            println ("Systest test failed, throwing error")
                            error = new Exception("Systest test failed")
                            currentBuild.result = 'FAILURE'
                            throw error
                        }
                    }
                }
            } // if ( params.DO_ROBOT )

            if ( params.SAVE_ARTIFACTS_OVERRIDE || stage_archive ) {
                stage("Archive") {
                    sh "echo ${container_name} > build_version.txt"
                    archiveArtifacts artifacts: "build_version.txt", fingerprint: true

                    // Archive the tested repo
                    dir("${RELEASE_DIR}") {
                        ci_helper.archive(params.ARTIFACTORY_SERVER,RELEASE,GERRIT_BRANCH,'tested')
                    }
                    if ( params.DO_DOCKERPUSH ) {
                        stage("Publish to Dockerhub") {
                            parallelSteps = [:]
                            for (buildStep in containerList) {
                                def module = buildStep
                                def moduleName = buildStep.toLowerCase()
                                def dockerTag = params.DOCKER_TAG
                                def moduleTag = container_name

                                parallelSteps[module] = {
                                    dir("$module") {
                                        sh "docker tag opensourcemano/${moduleName}:${moduleTag} opensourcemano/${moduleName}:${dockerTag}"
                                        sh "docker push opensourcemano/${moduleName}:${dockerTag}"
                                    }
                                }
                            }
                            parallel parallelSteps
                        }

                        stage("Snap promotion") {
                            def snaps = ["osmclient"]
                            sh "snapcraft login --with ~/.snapcraft/config"
                            for (snap in snaps) {
                                channel="latest/"
                                if (BRANCH_NAME.startsWith("v")) {
                                    channel=BRANCH_NAME.substring(1)+"/"
                                } else if (BRANCH_NAME!="master") {
                                    channel+="/"+BRANCH_NAME.replaceAll('/','-')
                                }
                                track=channel+"edge\\*"
                                edge_rev=sh(returnStdout: true,
                                    script: "snapcraft revisions $snap | " +
                                    "grep \"$track\" | tail -1 | awk '{print \$1}'").trim()
                                print "edge rev is $edge_rev"
                                track=channel+"beta\\*"
                                beta_rev=sh(returnStdout: true,
                                    script: "snapcraft revisions $snap | " +
                                    "grep \"$track\" | tail -1 | awk '{print \$1}'").trim()
                                print "beta rev is $beta_rev"

                                if ( edge_rev != beta_rev ) {
                                    print "Promoting $edge_rev to beta in place of $beta_rev"
                                    beta_track=channel+"beta"
                                    sh "snapcraft release $snap $edge_rev $beta_track"
                                }
                            }
                        } // stage("Snap promotion")
                    } // if ( params.DO_DOCKERPUSH )
                } // stage("Archive")
            } // if ( params.SAVE_ARTIFACTS_OVERRIDE || stage_archive )
        } // dir(OSM_DEVOPS)
    } finally {
        if ( params.DO_INSTALL && server_id != null) {
            delete_vm = true
            if (error && params.SAVE_CONTAINER_ON_FAIL ) {
                delete_vm = false
            }
            if (!error && params.SAVE_CONTAINER_ON_PASS ) {
                delete_vm = false
            }

            if ( delete_vm ) {
                if (server_id != null) {
                    println("Deleting VM: $server_id")
                    sh """#!/bin/sh -e
                        for line in `grep OS ~/hive/robot-systest.cfg | grep -v OS_CLOUD` ; do export \$line ; done
                        openstack server delete ${server_id}
                    """
                } else {
                    println("Saved VM $server_id in ETSI VIM")
                }
            }
        }
        if ( http_server_name != null ) {
            sh "docker stop ${http_server_name} || true"
            sh "docker rm ${http_server_name} || true"
        }

        if ( devopstempdir != null ) {
            sh "rm -rf ${devopstempdir}"
        }

        if ( jujutempdir != null ) {
            sh "rm -rf ${jujutempdir}"
        }
    }
}
