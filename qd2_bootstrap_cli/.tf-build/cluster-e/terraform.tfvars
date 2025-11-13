cluster_name = "cluster-e"
count_cp     = 1
count_worker = 2
image_name   = "ubuntu22.04"
flavor_name  = "C2_R4_D30"
keypair_name = "kubeone-keypair"
network_uuid = "f861a33e-1612-4e96-879d-a321c135cac8"

auth_url     = "http://10.4.16.11:5000/v3"
region       = "RegionOne"
user_name    = "admin"
tenant_id    = "ff3d68b2864d4b8cb72ad021f507df0b"
domain_name  = "Default"
# password via ENV: TF_VAR_password
