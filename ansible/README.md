```bash
az login --use-device-code
```

```bash
# Install Ansible
mkdir -p ~/venvs
# .venv path of Ansible for Azure
python3 -m venv ~/venvs/ansible-azure
source ~/venvs/ansible-azure/bin/activate

python -m pip install --upgrade pip
pip install ansible-core
ansible-galaxy collection install azure.azcollection
pip install -r ~/.ansible/collections/ansible_collections/azure/azcollection/requirements.txt

export ANSIBLE_AZURE_AUTH_SOURCE=cli
```

```bash
az provider list --query "[?namespace=='Microsoft.Network'].[namespace,registrationState]" -o table
az provider register --namespace Microsoft.Network --wait

az provider list --query "[?namespace=='Microsoft.Compute'].[namespace,registrationState]" -o table
az provider register --namespace Microsoft.Compute --wait
```

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -C "azure-k8s-lab"

# check ssh key
ls -l ~/.ssh/id_rsa ~/.ssh/id_rsa.pub

chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# login VM
ssh azureuser@<public-ip> -i ~/.ssh/id_rsa
```


```bash
source ~/venvs/ansible-azure/bin/activate
export AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
cd /mnt/g/YOLO-Waste-Detection/ansible
ansible-playbook playbooks/azure_infra.yml
```


