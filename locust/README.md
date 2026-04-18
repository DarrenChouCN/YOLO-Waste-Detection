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
locust -f locustfile.py --host http://4.194.51.69:30080

locust -f locustfile.py --host http://4.194.51.69:30080 --csv locust_result
```

# http://52.237.109.35:30080/docs
# http://4.193.181.73:30080/docs