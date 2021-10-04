#! /bin/bash
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# set -eux

JUJU_AGENT_VERSION=2.8.9
K8S_CLOUD_NAME="k8s-cloud"
KUBECTL="microk8s.kubectl"
MICROK8S_VERSION=1.19
OSMCLIENT_VERSION=10.0
IMAGES_OVERLAY_FILE=~/.osm/images-overlay.yaml
PATH=/snap/bin:${PATH}

MODEL_NAME=osm

OSM_BUNDLE=cs:osm-66
OSM_HA_BUNDLE=cs:osm-ha-51
TAG=10

function check_arguments(){
    while [ $# -gt 0 ] ; do
        case $1 in
            --bundle) BUNDLE="$2" ;;
            --overlay) OVERLAY="$2" ;;
            --k8s) KUBECFG="$2" ;;
            --vca) CONTROLLER="$2" ;;
            --lxd) LXD_CLOUD="$2" ;;
            --lxd-cred) LXD_CREDENTIALS="$2" ;;
            --microstack) MICROSTACK=y ;;
            --ha) BUNDLE=$OSM_HA_BUNDLE ;;
            --tag) TAG="$2" ;;
            --registry) REGISTRY_INFO="$2" ;;
            --only-vca) ONLY_VCA=y ;;
        esac
        shift
    done

    # echo $BUNDLE $KUBECONFIG $LXDENDPOINT
}

function install_snaps(){
    if [ ! -v KUBECFG ]; then
        sudo snap install microk8s --classic --channel=${MICROK8S_VERSION}/stable
        sudo cat /var/snap/microk8s/current/args/kube-apiserver | grep advertise-address || (
                echo "--advertise-address $DEFAULT_IP" | sudo tee -a /var/snap/microk8s/current/args/kube-apiserver
                microk8s.stop
                microk8s.start
            )
        sudo usermod -a -G microk8s `whoami`
        mkdir -p ~/.kube
        sudo chown -f -R `whoami` ~/.kube
        KUBEGRP="microk8s"
        sg ${KUBEGRP} -c "microk8s status --wait-ready"
        KUBECONFIG=~/.osm/microk8s-config.yaml
        sg ${KUBEGRP} -c "microk8s config" | tee ${KUBECONFIG}
    else
        KUBECTL="kubectl"
        sudo snap install kubectl --classic
        export KUBECONFIG=${KUBECFG}
        KUBEGRP=$(id -g -n)
    fi
    sudo snap install juju --classic --channel=2.8/stable
}

function bootstrap_k8s_lxd(){
    [ -v CONTROLLER ] && ADD_K8S_OPTS="--controller ${CONTROLLER}" && CONTROLLER_NAME=$CONTROLLER
    [ ! -v CONTROLLER ] && ADD_K8S_OPTS="--client" && BOOTSTRAP_NEEDED="yes" && CONTROLLER_NAME="osm-vca"

    if [ -v BOOTSTRAP_NEEDED ]; then
        CONTROLLER_PRESENT=$(juju controllers 2>/dev/null| grep ${CONTROLLER_NAME} | wc -l)
        if [ $CONTROLLER_PRESENT -ge 1 ]; then
            cat << EOF
Threre is already a VCA present with the installer reserved name of "${CONTROLLER_NAME}".
You may either explicitly use this VCA with the "--vca ${CONTROLLER_NAME}" option, or remove it
using this command:

   juju destroy-controller --release-storage --destroy-all-models -y ${CONTROLLER_NAME}

Please retry the installation once this conflict has been resolved.
EOF
            exit 1
        fi
    else
        CONTROLLER_PRESENT=$(juju controllers 2>/dev/null| grep ${CONTROLLER_NAME} | wc -l)
        if [ $CONTROLLER_PRESENT -le 0 ]; then
            cat << EOF
Threre is no VCA present with the name "${CONTROLLER_NAME}".  Please specify a VCA
that exists, or remove the --vca ${CONTROLLER_NAME} option.

Please retry the installation with one of the solutions applied.
EOF
            exit 1
        fi
    fi

    if [ -v KUBECFG ]; then
        cat $KUBECFG | juju add-k8s $K8S_CLOUD_NAME $ADD_K8S_OPTS
        [ -v BOOTSTRAP_NEEDED ] && juju bootstrap $K8S_CLOUD_NAME $CONTROLLER_NAME \
            --config controller-service-type=loadbalancer \
            --agent-version=$JUJU_AGENT_VERSION
    else
        sg ${KUBEGRP} -c "echo ${DEFAULT_IP}-${DEFAULT_IP} | microk8s.enable metallb"
        sg ${KUBEGRP} -c "microk8s.enable ingress"
        sg ${KUBEGRP} -c "microk8s.enable storage dns"
        TIME_TO_WAIT=30
        start_time="$(date -u +%s)"
        while true
        do
            now="$(date -u +%s)"
            if [[ $(( now - start_time )) -gt $TIME_TO_WAIT ]];then
                echo "Microk8s storage failed to enable"
                sg ${KUBEGRP} -c "microk8s.status"
                exit 1
            fi
            storage_status=`sg ${KUBEGRP} -c "microk8s.status -a storage"`
            if [[ $storage_status == "enabled" ]]; then
                break
            fi
            sleep 1
        done

        [ ! -v BOOTSTRAP_NEEDED ] && sg ${KUBEGRP} -c "microk8s.config" | juju add-k8s $K8S_CLOUD_NAME $ADD_K8S_OPTS
        [ -v BOOTSTRAP_NEEDED ] && sg ${KUBEGRP} -c \
            "juju bootstrap microk8s $CONTROLLER_NAME --config controller-service-type=loadbalancer --agent-version=$JUJU_AGENT_VERSION" \
            && K8S_CLOUD_NAME=microk8s
    fi

    if [ -v LXD_CLOUD ]; then
        if [ ! -v LXD_CREDENTIALS ]; then
            echo "The installer needs the LXD server certificate if the LXD is external"
            exit 1
        fi
    else
        LXDENDPOINT=$DEFAULT_IP
        LXD_CLOUD=~/.osm/lxd-cloud.yaml
        LXD_CREDENTIALS=~/.osm/lxd-credentials.yaml
        # Apply sysctl production values for optimal performance
        sudo cp /usr/share/osm-devops/installers/60-lxd-production.conf /etc/sysctl.d/60-lxd-production.conf
        sudo sysctl --system
        # Install LXD snap
        sudo apt-get remove --purge -y liblxc1 lxc-common lxcfs lxd lxd-client
        sudo snap install lxd
        # Configure LXD
        sudo usermod -a -G lxd `whoami`
        cat /usr/share/osm-devops/installers/lxd-preseed.conf | sed 's/^config: {}/config:\n  core.https_address: '$LXDENDPOINT':8443/' | sg lxd -c "lxd init --preseed"
        sg lxd -c "lxd waitready"
        DEFAULT_MTU=$(ip addr show $DEFAULT_IF | perl -ne 'if (/mtu\s(\d+)/) {print $1;}')
        sg lxd -c "lxc profile device set default eth0 mtu $DEFAULT_MTU"
        sg lxd -c "lxc network set lxdbr0 bridge.mtu $DEFAULT_MTU"

        cat << EOF > $LXD_CLOUD
clouds:
  lxd-cloud:
    type: lxd
    auth-types: [certificate]
    endpoint: "https://$LXDENDPOINT:8443"
    config:
      ssl-hostname-verification: false
EOF
        openssl req -nodes -new -x509 -keyout ~/.osm/client.key -out ~/.osm/client.crt -days 365 -subj "/C=FR/ST=Nice/L=Nice/O=ETSI/OU=OSM/CN=osm.etsi.org"
        local server_cert=`cat /var/snap/lxd/common/lxd/server.crt | sed 's/^/        /'`
        local client_cert=`cat ~/.osm/client.crt | sed 's/^/        /'`
        local client_key=`cat ~/.osm/client.key | sed 's/^/        /'`

        cat << EOF > $LXD_CREDENTIALS
credentials:
  lxd-cloud:
    lxd-cloud:
      auth-type: certificate
      server-cert: |
$server_cert
      client-cert: |
$client_cert
      client-key: |
$client_key
EOF
        lxc config trust add local: ~/.osm/client.crt
    fi

    juju add-cloud -c $CONTROLLER_NAME lxd-cloud $LXD_CLOUD --force
    juju add-credential -c $CONTROLLER_NAME lxd-cloud -f $LXD_CREDENTIALS
    sg lxd -c "lxd waitready"
    juju controller-config features=[k8s-operators]
}

function wait_for_port(){
    SERVICE=$1
    INDEX=$2
    TIME_TO_WAIT=30
    start_time="$(date -u +%s)"
    while true
    do
        now="$(date -u +%s)"
        if [[ $(( now - start_time )) -gt $TIME_TO_WAIT ]];then
            echo "Failed to expose external ${SERVICE} interface port"
            exit 1
        fi

        if [ $(sg ${KUBEGRP} -c "${KUBECTL} get ingresses.networking -n osm -o json | jq -r '.items[$INDEX].metadata.name'") == ${SERVICE} ] ; then
            break
        fi
        sleep 1
    done
}

function deploy_charmed_osm(){
    if [ -v REGISTRY_INFO ] ; then
        registry_parts=(${REGISTRY_INFO//@/ })
        if [ ${#registry_parts[@]} -eq 1 ] ; then
            # No credentials supplied
            REGISTRY_USERNAME=""
            REGISTRY_PASSWORD=""
            REGISTRY_URL=${registry_parts[0]}
        else
            credentials=${registry_parts[0]}
            credential_parts=(${credentials//:/ })
            REGISTRY_USERNAME=${credential_parts[0]}
            REGISTRY_PASSWORD=${credential_parts[1]}
            REGISTRY_URL=${registry_parts[1]}
        fi
        # Ensure the URL ends with a /
        case $REGISTRY_URL in
            */) ;;
            *) REGISTRY_URL=${REGISTRY_URL}/
        esac
    fi

    echo "Creating OSM model"
    if [ -v KUBECFG ]; then
        juju add-model $MODEL_NAME $K8S_CLOUD_NAME
    else
        sg ${KUBEGRP} -c "juju add-model $MODEL_NAME $K8S_CLOUD_NAME"
    fi
    echo "Deploying OSM with charms"
    images_overlay=""
    if [ -v REGISTRY_URL ]; then
       [ ! -v TAG ] && TAG='latest'
    fi
    [ -v TAG ] && generate_images_overlay && images_overlay="--overlay $IMAGES_OVERLAY_FILE"

    if [ -v OVERLAY ]; then
        extra_overlay="--overlay $OVERLAY"
    fi

    if [ -v BUNDLE ]; then
        juju deploy -m $MODEL_NAME $BUNDLE --overlay ~/.osm/vca-overlay.yaml $images_overlay $extra_overlay
    else
        juju deploy -m $MODEL_NAME $OSM_BUNDLE --overlay ~/.osm/vca-overlay.yaml $images_overlay $extra_overlay
    fi

    if [ ! -v KUBECFG ]; then
        API_SERVER=${DEFAULT_IP}
    else
        API_SERVER=$(kubectl config view --minify | grep server | cut -f 2- -d ":" | tr -d " ")
        proto="$(echo $API_SERVER | grep :// | sed -e's,^\(.*://\).*,\1,g')"
        url="$(echo ${API_SERVER/$proto/})"
        user="$(echo $url | grep @ | cut -d@ -f1)"
        hostport="$(echo ${url/$user@/} | cut -d/ -f1)"
        API_SERVER="$(echo $hostport | sed -e 's,:.*,,g')"
    fi
    # Expose OSM services
    juju config -m $MODEL_NAME nbi site_url=https://nbi.${API_SERVER}.nip.io
    juju config -m $MODEL_NAME ng-ui site_url=https://ui.${API_SERVER}.nip.io
    juju config -m $MODEL_NAME grafana site_url=https://grafana.${API_SERVER}.nip.io
    juju config -m $MODEL_NAME prometheus site_url=https://prometheus.${API_SERVER}.nip.io

    echo "Waiting for deployment to finish..."
    check_osm_deployed
    echo "OSM with charms deployed"
}

function check_osm_deployed() {
    TIME_TO_WAIT=600
    start_time="$(date -u +%s)"
    total_service_count=14
    previous_count=0
    while true
    do
        service_count=$(juju status -m $MODEL_NAME | grep kubernetes | grep active | wc -l)
        echo "$service_count / $total_service_count services active"
        if [ $service_count -eq $total_service_count ]; then
            break
        fi
        if [ $service_count -ne $previous_count ]; then
            previous_count=$service_count
            start_time="$(date -u +%s)"
        fi
        now="$(date -u +%s)"
        if [[ $(( now - start_time )) -gt $TIME_TO_WAIT ]];then
            echo "Timed out waiting for OSM services to become ready"
            exit 1
        fi
        sleep 10
    done
}

function create_overlay() {
    sudo snap install jq
    sudo snap install yq
    local HOME=/home/$USER
    local vca_user=$(cat $HOME/.local/share/juju/accounts.yaml | yq e .controllers.$CONTROLLER_NAME.user - )
    local vca_secret=$(cat $HOME/.local/share/juju/accounts.yaml | yq e .controllers.$CONTROLLER_NAME.password - )
    local vca_host=$(cat $HOME/.local/share/juju/controllers.yaml | yq e .controllers.$CONTROLLER_NAME.api-endpoints[0] - | cut -d ":" -f 1)
    local vca_port=$(cat $HOME/.local/share/juju/controllers.yaml | yq e .controllers.$CONTROLLER_NAME.api-endpoints[0] - | cut -d ":" -f 2)
    local vca_pubkey=\"$(cat $HOME/.local/share/juju/ssh/juju_id_rsa.pub)\"
    local vca_cloud="lxd-cloud"
    # Get the VCA Certificate
    local vca_cacert=$(cat $HOME/.local/share/juju/controllers.yaml | yq e .controllers.$CONTROLLER_NAME.ca-cert - | base64 | tr -d \\n)

    # Calculate the default route of this machine
    local DEFAULT_IF=`ip route list match 0.0.0.0 | awk '{print $5}'`

    # Generate a new overlay.yaml, overriding any existing one
    cat << EOF > /tmp/vca-overlay.yaml
applications:
  lcm:
    options:
      vca_user: $vca_user
      vca_secret: $vca_secret
      vca_host: $vca_host
      vca_port: $vca_port
      vca_pubkey: $vca_pubkey
      vca_cacert: $vca_cacert
      vca_cloud: $vca_cloud
      vca_k8s_cloud: $K8S_CLOUD_NAME
  mon:
    options:
      vca_user: $vca_user
      vca_secret: $vca_secret
      vca_host: $vca_host
      vca_cacert: $vca_cacert
EOF
    mv /tmp/vca-overlay.yaml ~/.osm/
    OSM_VCA_HOST=$vca_host
}

function generate_images_overlay(){
    echo "applications:" > /tmp/images-overlay.yaml

    charms_with_resources="nbi lcm mon pol ng-ui ro pla keystone"
    for charm in $charms_with_resources; do
        cat << EOF > /tmp/${charm}_registry.yaml
registrypath: ${REGISTRY_URL}opensourcemano/${charm}:$TAG
EOF
        if [ ! -z "$REGISTRY_USERNAME" ] ; then
            echo username: $REGISTRY_USERNAME >> /tmp/${charm}_registry.yaml
            echo password: $REGISTRY_PASSWORD >> /tmp/${charm}_registry.yaml
        fi

        cat << EOF >> /tmp/images-overlay.yaml
  ${charm}:
    resources:
      image: /tmp/${charm}_registry.yaml

EOF
    done

    mv /tmp/images-overlay.yaml $IMAGES_OVERLAY_FILE
}

function refresh_osmclient_snap() {
    osmclient_snap_install_refresh refresh
}

function install_osm_client_snap() {
    osmclient_snap_install_refresh install
}

function osmclient_snap_install_refresh() {
    channel_preference="stable candidate beta edge"
    for channel in $channel_preference; do
        echo "Trying to install osmclient from channel $OSMCLIENT_VERSION/$channel"
        sudo snap $1 osmclient --channel $OSMCLIENT_VERSION/$channel 2> /dev/null && echo osmclient snap installed && break
    done
}
function install_osmclient() {
    snap info osmclient | grep -E ^installed: && refresh_osmclient_snap || install_osm_client_snap
}

function add_local_k8scluster() {
    osm --all-projects vim-create \
      --name _system-osm-vim \
      --account_type dummy \
      --auth_url http://dummy \
      --user osm --password osm --tenant osm \
      --description "dummy" \
      --config '{management_network_name: mgmt}'
    tmpfile=$(mktemp --tmpdir=${HOME})
    cp ${KUBECONFIG} ${tmpfile}
    osm --all-projects k8scluster-add \
      --creds ${tmpfile} \
      --vim _system-osm-vim \
      --k8s-nets '{"net1": null}' \
      --version '1.19' \
      --description "OSM Internal Cluster" \
      _system-osm-k8s
    rm -f ${tmpfile}
}

function install_microstack() {
    sudo snap install microstack --classic --beta
    sudo microstack.init --auto
    wget https://cloud-images.ubuntu.com/releases/16.04/release/ubuntu-16.04-server-cloudimg-amd64-disk1.img -P ~/.osm/
    microstack.openstack image create \
    --public \
    --disk-format qcow2 \
    --container-format bare \
    --file ~/.osm/ubuntu-16.04-server-cloudimg-amd64-disk1.img \
    ubuntu1604
    ssh-keygen -t rsa -N "" -f ~/.ssh/microstack
    microstack.openstack keypair create --public-key ~/.ssh/microstack.pub microstack
    export OSM_HOSTNAME=`juju status -m $MODEL_NAME --format json | jq -rc '.applications."nbi".address'`
    osm vim-create --name microstack-site \
    --user admin \
    --password keystone \
    --auth_url http://10.20.20.1:5000/v3 \
    --tenant admin \
    --account_type openstack \
    --config='{security_groups: default,
        keypair: microstack,
        project_name: admin,
        user_domain_name: default,
        region_name: microstack,
        insecure: True,
        availability_zone: nova,
    version: 3}'
}

DEFAULT_IF=`ip route list match 0.0.0.0 | awk '{print $5}'`
DEFAULT_IP=`ip -o -4 a |grep ${DEFAULT_IF}|awk '{split($4,a,"/"); print a[1]}'`

check_arguments $@
mkdir -p ~/.osm
install_snaps
bootstrap_k8s_lxd
create_overlay
if [ -v ONLY_VCA ]; then
    HOME=/home/$USER
    vca_user=$(cat $HOME/.local/share/juju/accounts.yaml | yq e .controllers.$CONTROLLER_NAME.user - )
    vca_secret=$(cat $HOME/.local/share/juju/accounts.yaml | yq e .controllers.$CONTROLLER_NAME.password - )
    vca_host=$(cat $HOME/.local/share/juju/controllers.yaml | yq e .controllers.$CONTROLLER_NAME.api-endpoints[0] - | cut -d ":" -f 1)
    vca_port=$(cat $HOME/.local/share/juju/controllers.yaml | yq e .controllers.$CONTROLLER_NAME.api-endpoints[0] - | cut -d ":" -f 2)
    vca_pubkey=\"$(cat $HOME/.local/share/juju/ssh/juju_id_rsa.pub)\"
    vca_cloud="lxd-cloud"
    vca_cacert=$(cat $HOME/.local/share/juju/controllers.yaml | yq e .controllers.$CONTROLLER_NAME.ca-cert - | base64 | tr -d \\n)
    hostname=`cat /etc/hostname`

    echo "Use the following command to register the installed VCA to your OSM:"
    echo -e "  osm vca-add --endpoints $vca_host:$vca_port \ \n         --user $vca_user \ \n         --secret $vca_secret \ \n         --cacert $vca_cacert \ \n         --lxd-cloud lxd-cloud \ \n         --lxd-credentials lxd-cloud \ \n         --k8s-cloud microk8s \ \n         --k8s-credentials microk8s\ \n         $hostname-vca"
else
    deploy_charmed_osm
    install_osmclient
    export OSM_HOSTNAME=$(juju config -m $MODEL_NAME nbi site_url | sed "s/http.*\?:\/\///"):443
    sleep 10
    add_local_k8scluster
    if [ -v MICROSTACK ]; then
        install_microstack
    fi

    echo "Your installation is now complete, follow these steps for configuring the osmclient:"
    echo
    echo "1. Create the OSM_HOSTNAME environment variable with the NBI IP"
    echo
    echo "export OSM_HOSTNAME=$OSM_HOSTNAME"
    echo
    echo "2. Add the previous command to your .bashrc for other Shell sessions"
    echo
    echo "echo \"export OSM_HOSTNAME=$OSM_HOSTNAME\" >> ~/.bashrc"
    echo
    echo "DONE"
fi

