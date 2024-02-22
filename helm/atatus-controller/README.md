```bash
helm upgrade --install  atatus-controller ../atatus-controller --create-namespace --namespace  atatus-controller --set image.tag=chernyenkocomua/atatus-controller:v0.6 -f values.yaml
```
