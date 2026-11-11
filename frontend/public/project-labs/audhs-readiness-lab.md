# Kubernetes readiness exercise

Use a disposable cluster. Save the YAML in the current directory. These commands run in Bash. First check the context and confirm that it identifies your lab cluster.

```bash
kubectl config current-context
```

Create a new namespace. Continue only after namespace creation succeeds.

```bash
ns="audhs-probes-$(date +%s)"
kubectl create namespace "$ns"
kubectl -n "$ns" apply -f audhs-readiness-lab.yaml
kubectl -n "$ns" rollout status deploy/probe-lab --timeout=120s
```

Predict what happens to Pod readiness, restart count, and Service endpoint readiness when the marker file is removed. Save the prediction in the Kubernetes project notes before testing.

```bash
observe() {
  kubectl -n "$ns" get pods -l app=probe-lab
  kubectl -n "$ns" get endpointslice -l kubernetes.io/service-name=probe-lab -o jsonpath='{range .items[*].endpoints[*]}{.addresses}{" ready="}{.conditions.ready}{"\n"}{end}'
}
observe
kubectl -n "$ns" exec deploy/probe-lab -- rm /tmp/ready
kubectl -n "$ns" wait pod -l app=probe-lab --for=condition=Ready=false --timeout=60s
observe
kubectl -n "$ns" exec deploy/probe-lab -- wget -qO- http://127.0.0.1:8080/
kubectl -n "$ns" exec deploy/probe-lab -- touch /tmp/ready
kubectl -n "$ns" wait pod -l app=probe-lab --for=condition=Ready --timeout=60s
observe
```

EndpointSlice updates are asynchronous. Repeat observe after a few seconds if it still shows the previous state. Record your actual outputs in project evidence. Which observation tests the application directly? Which reports eligibility to receive ordinary Service traffic? Explain whether the restart count changed. The localhost request runs inside the Pod and does not exercise a Service request from another Pod.

### Transfer check from a client Pod

Predict whether a new request from another Pod to the Service will reach the server in each state: ready, unready, then ready again. Keep the namespace, single replica, Service selector and server process unchanged.

```bash
kubectl -n "$ns" run requester --image=busybox:1.36.1 --restart=Never --command -- sleep 600
kubectl -n "$ns" wait pod/requester --for=condition=Ready --timeout=60s
service_ip=$(kubectl -n "$ns" get service probe-lab -o jsonpath='{.spec.clusterIP}')
service_request() {
  kubectl -n "$ns" exec requester -- wget -T 3 -qO- "http://$service_ip/"
}
service_request
kubectl -n "$ns" exec deploy/probe-lab -- rm /tmp/ready
kubectl -n "$ns" wait pod -l app=probe-lab --for=condition=Ready=false --timeout=60s
observe
service_request
kubectl -n "$ns" exec deploy/probe-lab -- wget -T 3 -qO- http://127.0.0.1:8080/
kubectl -n "$ns" exec deploy/probe-lab -- touch /tmp/ready
kubectl -n "$ns" wait pod -l app=probe-lab --for=condition=Ready --timeout=60s
observe
service_request
```

Run each observation separately so a failed request does not prevent restoring the marker. Each request opens a fresh connection. Service routing may briefly lag the EndpointSlice update: record the first outcome and retry after a few seconds. If the ready-state request fails, resolve that baseline before interpreting an unready-state failure. This example uses an IPv4 Service address.

In project evidence, record Pod and EndpointSlice readiness, restart count, the localhost body and the separate client’s result in each state. Compare your predictions with those observations, then save your explanation or create a personal lesson draft from the saved findings.

In a verified single-node kind v0.33.0 run on Kubernetes v1.37.0, the same Pod remained running with zero restarts through all three states. Its localhost response remained `available`. New IPv4 ClusterIP requests from the separate client succeeded, failed, then succeeded after readiness and the endpoint converged. This exercise checks one replica and fresh connections; record your own run separately.

Remove only the namespace created for this exercise.

```bash
kubectl delete namespace "$ns"
```
