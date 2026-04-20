```bash
mkdir locust
cd locust
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install locust
```

```bash
source .venv/bin/activate
locust -f locustfile.py --host http://20.212.211.0:30080

locust -f locustfile.py --host http://4.193.105.141:30080 --csv locust_result
```

```bash
kubectl describe node master | grep Taints
kubectl get nodes
kubectl taint nodes <master-node-name> node-role.kubernetes.io/control-plane-
kubectl get pods -o wide -w
```