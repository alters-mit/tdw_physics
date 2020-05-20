from argparse import ArgumentParser
import json
import pkg_resources
from pathlib import Path
from enum import Enum
from tdw.controller import Controller
from tdw.output_data import Volumes


class Material(Enum):
    """
    Semantic material types.
    """

    ceramic = 0
    concrete = 1
    fabric = 2
    glass = 3
    leather = 4
    metal = 5
    plastic = 6
    rubber = 7
    stone = 8
    wood = 9
    paper = 10
    organic = 11


BOUNCINESS = {Material.ceramic: 0.625,
              Material.concrete: 0.2,
              Material.fabric: 0.05,
              Material.glass: 0.5,
              Material.leather: 0.1,
              Material.metal: 0.35,
              Material.organic: 0.1,
              Material.paper: 0.05,
              Material.plastic: 0.7,
              Material.rubber: 0.7,
              Material.stone: 0.2,
              Material.wood: 0.58}

DENSITY = {Material.ceramic: 218,
           Material.concrete: 200,
           Material.fabric: 42,
           Material.glass: 250,
           Material.leather: 860,
           Material.metal: 845,
           Material.organic: 100,
           Material.paper: 70,
           Material.plastic: 145,
           Material.rubber: 119,
           Material.stone: 246,
           Material.wood: 690}

STATIC_FRICTION = {Material.ceramic: 0.47,
                   Material.concrete: 0.56,
                   Material.fabric: 0.48,
                   Material.glass: 0.65,
                   Material.leather: 0.47,
                   Material.metal: 0.52,
                   Material.organic: 0.47,
                   Material.paper: 0.47,
                   Material.plastic: 0.48,
                   Material.rubber: 0.47,
                   Material.stone: 0.48,
                   Material.wood: 0.4}

DYNAMIC_FRICTION = {Material.ceramic: 0.47,
                    Material.concrete: 0.49,
                    Material.fabric: 0.48,
                    Material.glass: 0.45,
                    Material.leather: 0.47,
                    Material.metal: 0.43,
                    Material.organic: 0.47,
                    Material.paper: 0.47,
                    Material.plastic: 0.44,
                    Material.rubber: 0.47,
                    Material.stone: 0.48,
                    Material.wood: 0.35}

"""
Load an object and get a "best-guess" at its physics values.
"""


class PhysicsInfoCalculator(Controller):
    def __init__(self):
        super().__init__()

        self.p = Path(pkg_resources.resource_filename(__name__, "data/physics_info.json"))
        self.data = json.loads(self.p.read_text(encoding="utf-8"))

        self.communicate([{"$type": "load_scene"},
                          {"$type": "create_empty_environment"}])

    def calculate(self, name: str, mat: str, lib: str) -> None:
        """
        Calculate the physics info for an object and add it to the .json file.

        :param name: The name of the object.
        :param mat: The semantic material.
        :param lib: The model library filename.
        """

        # Add the object.
        self.add_object(name, library=lib)
        # Get volume data.
        resp = self.communicate({"$type": "send_volumes"})
        volume = Volumes(resp[0]).get_volume(0)
        mat = Material[mat]

        object_info = {"name": name,
                       "mass": volume * DENSITY[mat],
                       "bounciness": BOUNCINESS[mat],
                       "static_friction": STATIC_FRICTION[mat],
                       "dynamic_friction": DYNAMIC_FRICTION[mat],
                       "library": lib}

        print(json.dumps(object_info, sort_keys=True, indent=2))

        self.data.update({name: object_info})
        self.p.write_text(json.dumps(self.data, sort_keys=True, indent=2), encoding="utf-8")
        # Destroy the object.
        self.communicate([{"$type": "destroy_all_objects"},
                          {"$type": "unload_asset_bundles"}])


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--name", type=str, help="The name of the model.")
    parser.add_argument("--lib", type=str, default="models_full.json", help="The model library")
    parser.add_argument("--mat", type=str, help="The semantic material.")
    args = parser.parse_args()

    p = PhysicsInfoCalculator()
    p.calculate(name=args.name, mat=args.mat, lib=args.lib)
    p.communicate({"$type": "terminate"})
