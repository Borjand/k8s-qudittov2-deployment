
# qd2_bootstrap – Quditto deployment and K8s cluster management CLI application

This repository provides all the necessary configuration and instructions to:
1. Provision virtual machines on OpenStack (optional).
2. Bootstrap and manage Kubernetes clusters using KubeOne.
3. Deploy the Quditto platform on an existing Kubernetes cluster.


## 1. Prerequisites

Before starting, ensure you have the following tools installed on your management machine:

| Tool | Purpose |
|------|----------|
| Terraform | Infrastructure provisioning |
| KubeOne | Kubernetes lifecycle management |
| kubectl | Cluster access |
| OpenStack client | Optional, for debugging or inspecting OpenStack resources |

You also need access to an OpenStack tenant with:
- A valid keypair file  
- A flavor
- A network UUID
- Credentials (auth URL, user, project, domain)

## 2. (Optional) Provisioning OpenStack Virtual Machines

This application supports the creation og  virtual machines directly in OpenStack using Terraform as the underlying engine that provisions and manages OpenStack infrastructure resources.

### Steps
1. Write an OpenStack infrastructure descriptor (example: `os-infra.yaml`).
2. Run:
   ```
   qd2_bootstrap infra up -f os-infra.yaml
   ```
3. The tool will:
   - Create networks, VMs, security groups, and keypairs required for Kubernetes.
   - Output the resulting infrastructure description that can be referenced in `os-infra.yaml`. At execution time, once the infrastructure creation finishes, the command returns the list of provisioned machine IPs (one control-plane node and two worker nodes in this example).
The output looks like this:
```
Outputs:

control_plane_ip = "<control-plane-ip>"
worker_ips = [
  "<worker-ip-1>",
  "<worker-ip-2>",
  ...
]
```

### Example of infrastructure descriptor yaml
```
# os-infra.yaml

namespace: default

infraSetup:
  clusterName: "cluster-example"
  countCp: 1
  countWorker: 2

  imageName: "ubuntu22.04"
  flavorName: "C2_R4_D30"
  keypairName: "<openstack-keypair-name>"
  networkUuid: "<openstack-network-uuid>"

  openstack:
    authUrl: "<openstack-auth-url>"          # e.g., http://<host>:5000/v3
    region: "<openstack-region>"             # e.g., RegionOne
    userName: "<openstack-username>"         # e.g., admin
    password: "<openstack-password>"         # user password
    tenantId: "<openstack-tenant-id>"        # project UUID
    domainName: "<openstack-domain-name>"    # e.g., Default

```

## 3. Provision Kubernetes with KubeOne

The qd2_bootstrap CLI automates the full lifecycle of Kubernetes clusters using KubeOne underneath. It supports the deployment of  Kubeadm-based Kubernetes clusters in two different ways:


### 3.1.1. Option 1 — Using pre-existing machines

If the user already has virtual machines provisioned, the cluster can be deployed by referencing these hosts directly. An example of the cluster descriptor needed to proceed with the deployment is provided below:

```
# cluster-on-existing-machines.yaml

clusterSetup:
  name: "cluster-d"
  kubernetesVersion: "1.31.0"

  ssh:
    user: "ubuntu"
    privateKeyFile: "<path-to-private-key>"

  networking:
    podSubnet: "10.50.0.0/16"
    serviceSubnet: "10.96.0.0/12"

  apiEndpoint:
    host: "<control-plane-ip>"
    port: 6443

  cni:
    external: true           # CNI will be installed using Helm

  existingHosts:
    controlPlane:
      - privateAddress: "<cp-node-ip>"
    workers:
      - privateAddress: "<worker-node-1-ip>"
      - privateAddress: "<worker-node-2-ip>"

  helmReleases:
    - chart: "flannel"
      repoURL: "https://flannel-io.github.io/flannel/"
      namespace: "kube-system"
      version: "v0.27.0"
      values:
        podCidr: "10.50.0.0/16"
        backend: "vxlan"
```

Then, deploy the cluster through the qd2_bootstrap cli as shown next:

```
qd2_bootstrap cluster up -f cluster-on-existing-machines.yaml
```




###  3.1.2. Option 2 — Using infrastructure automatically provisioned by the CLI

In this mode, qd2_bootstrap will:

1. Provision the required VMs in OpenStack using your infra.yaml.

2. Use the Terraform outputs automatically to assemble the KubeOne cluster descriptor.

3. Deploy Kubernetes on top of the freshly created nodes.

Next, we provide an example cluster descriptor using infra outputs (cluster-from-infra.yaml)

```
clusterSetup:
  name: "cluster-e"
  kubernetesVersion: "1.31.0"

  ssh:
    user: ubuntu
    privateKeyFile: "<path-to-private-key>"

  # If fromInfra is used, the control-plane IP will be auto-filled
  apiEndpoint:
    host: ""
    port: 6443

  networking:
    podSubnet: "10.50.0.0/16"
    serviceSubnet: "10.96.0.0/12"

  cni:
    external: true

  fromInfra:
    workdir: "./.tf-build/cluster-e"

  helmReleases:
    - chart: flannel
      repoURL: https://flannel-io.github.io/flannel/
      namespace: kube-system
      version: v0.27.0
      values:
        podCidr: "10.50.0.0/16"
        backend: "vxlan"
```

Then, it is possible to proceed with the infrastructure VMs provisioning and deploy cluster deployments over them with:
```
qd2_bootstrap cluster up \
  -f cluster-from-infra.yaml \
  --provision-infra os-infra.yaml \
  --use-infra-tfstate \
  --wait-ssh \
  --ssh-timeout 600
```

**Note that in this case, the descriptor containing the OpenStack specifications as indicated in [Section 2](#2-optional-provisioning-openstack-virtual-machines) is needed**

### 3.2. Checking Cluster Status
After deploying the Kubernetes cluster (either using existing hosts or machines provisioned through the infrastructure workflow), you can verify its health using the cli:

```
qd2_bootstrap cluster status \
  --kubeconfig <path-to-kubeconfig>
```
This command checks:

* Control plane reachability

* Node readiness (control-plane + workers)

* Core Kubernetes components (kube-apiserver, scheduler, controller-manager, etc.)

* CNI readiness (once installed)

If everything is healthy, the output will confirm that the cluster is operational.

## 4. Deploying a Custom Quditto Topology on an Existing Cluster

Once a Kubernetes cluster is up and reachable (either created via qd2_bootstrap cluster up or managed externally), you can deploy a Quditto setup described as a high-level specification.

### 4.1. Example Quditto deployment spec (quditto-spec.yaml):
```
namespace: default

charts:
  repo: "https://borjand.github.io/k8s-qudittov2-deployment/"

qudittoSetup:
  qcontroller:
    nodek8s: cluster-e-worker-1
    chart: "qcontroller-v2"
    version: "0.1.0"
    values:
      l2sm:
        enabled: false

  qorchestrator:
    nodek8s: cluster-e-worker-1
    chart: "qorchestrator-v2"
    version: "0.1.0"
    values:
      l2sm:
        enabled: false

  qnodes:
    - name: qnode-a
      nodek8s: cluster-e-worker-1
      chart: "qnode-v2"
      version: "0.1.0"
      values:
        l2sm:
          enabled: false

    - name: qnode-b
      nodek8s: cluster-e-worker-2
      chart: "qnode-v2"
      version: "0.1.0"
      values:
        l2sm:
          enabled: false
```

Notes:

```namespace```: Kubernetes namespace where all Quditto components will be deployed.

```charts.repo```: Helm repository hosting the Quditto Helm charts.

```nodek8s```: must match the Kubernetes node name where the component should be scheduled (for example, as seen via kubectl get nodes -o wide).

```values```: passed as Helm values for each chart, allowing you to tune features such as l2sm.enabled.

### 4.2 Deploy Quditto

Once the spec file is ready, deploy Quditto onto the target cluster with:

```
qd2_bootstrap quditto deploy \
  -f quditto-spec.yaml \
  --kubeconfig <path-to-kubeconfig-for-target-cluster>
```

```--kubeconfig``` should point to the kubeconfig file for the cluster where you want to deploy Quditto (for example, the kubeconfig generated after deploying the cluster as in [Section 3](#3-provision-kubernetes-with-kubeone).




