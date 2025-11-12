# Mapping helpers that turn domain params into chart values.

def values_from_params(nodek8s: str) -> dict:
    """
    Convert domain-level placement (nodek8s) into the Helm values shape expected by your charts.
    You requested the following structure:
      placement:
        nodeSelector: {}
        useNodeName: true
        nodeName: "<nodek8s>"
    """
    return {
        "placement": {
            "nodeSelector": {},
            "useNodeName": True,
            "nodeName": nodek8s,
        }
    }
