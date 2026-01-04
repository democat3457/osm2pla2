import json
import uuid
from dataclasses import dataclass, field
from .coords import Vec2D

@dataclass
class Pla2Object:
    type: str
    nodes: list[Vec2D]
    display_name: str = ""
    layer: float = 0.0
    tags: list[str] = field(default_factory=list)

class Pla2ObjectCollection:
    def __init__(self, namespace):
        self.namespace = namespace
        self._collection: list[Pla2Object] = []
    
    def add(self, obj: Pla2Object):
        if obj not in self._collection:
            self._collection.append(obj)
    
    def __len__(self):
        return len(self._collection)

    def to_json(self, fp):
        return json.dump([
            {
                "namespace": self.namespace,
                "id": str(uuid.uuid4()),
                "display_name": o.display_name,
                "description": "",
                "tags": o.tags,
                "layer": o.layer,
                "type": o.type,
                "nodes": [n.tup for n in o.nodes]
            }
            for o in self._collection
        ], fp, indent=2)
