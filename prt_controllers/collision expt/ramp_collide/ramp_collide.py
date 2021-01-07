import os
import shutil
from time import sleep
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.output_data import Collision
from tdw.output_data import Images


"""
    - Listen for collisions between objects.
    - Adjust the friction values of objects.
    """


class DropObject(Controller):
    def trial(self, m_o, s_o, b_o, output_directory, nimages):
        """
            Collide a chair with a fridge.
            
            :param m_c: mass of the chair.
            :param s_c: The static friction of the chair.
            :param b_c: The bounciness of the chair.
            """
        
        # Destroy all objects currently in the scene.
        self.communicate({"$type": "destroy_all_objects"})

        # Set screen size
        self.communicate({"$type": "set_screen_size", "height": 480, "width": 640})

        # Create the avatar.
        self.communicate({"$type": "create_avatar",
                         "type": "A_Img_Caps_Kinematic",
                         "id": "a"})
            
        # Teleport the avatar to the valid position.
        # Enable image capture.
        self.communicate([{"$type": "teleport_avatar_to",
                           "avatar_id": "a",
                           "position": {"x": -1.5, "y": 2.5, "z": 7}},
                           {"$type": "set_pass_masks",
                           "avatar_id": "a",
                           "pass_masks": ["_img", "_id"]},
                           {"$type": "send_images",
                           "frequency": "always"},
                           ])
                                 
        # place the ramp
        ramp_id = self.add_object("ramp_with_platform_30",
                                   position={"x": -2.1, "y": 0, "z":0})
        self.communicate([{"$type": "scale_object",
                           "id": ramp_id,
                           "scale_factor": (1,1,1)}
                           ])
        self.communicate([{"$type": "set_kinematic_state",
                         "id": ramp_id,
                         "is_kinematic": True,
                         "use_gravity": False}])
        self.communicate([{"$type": "set_visual_material",
                           "old_material_index": 1,
                           "new_material_name": "3d_mesh_technical_fabric",
                           "object_name": "ramp_with_platform_30",
                           "id": ramp_id}])
         
        # place the elevated platform
        platform_id = self.add_object("fridge_box",
                                   position={"x": 1.5, "y": 0, "z":0})
        self.communicate({"$type": "set_kinematic_state",
                      "id": platform_id,
                      "is_kinematic": True,
                      "use_gravity": False})
         
        # place a collider object on the ramp (salt_mill_max_2013,b05_fire_extinguisher)
        collider_id = self.add_object("b05_fire_extinguisher",
                                   position={"x": -4, "y": 0, "z": 0})
        # Set the scale, mass, and friction of the object.
        self.communicate({"$type": "scale_object",
                      "id": collider_id,
                      "scale_factor": {"x":2, "y":2, "z":2}})
        self.communicate({"$type": "set_mass",
                      "id": collider_id,
                      "mass": 1})
        self.communicate({"$type": "set_physic_material",
                      "id": collider_id,
                      "static_friction": 0.5,
                      "bounciness": 0.5})
        #self.communicate({"$type":"set_color",
        #               "color":{"r":1, "g":0, "b":1, "a":1},
        #               "id": collider_id})
        #self.communicate({"$type": "nudge_onto_surface",
        #               "id": collider_id,
        #               "is_circle": True,
        #               "nudge_step": .05,
        #               "surface_object_id": ramp_id})
                         
        # place the basket on the ramp (bucketnew, bowl_wood_a_01)
        if 0:
            basket_id = self.add_object("bowl_wood_a_01",
                                        position={"x": 0.1, "y": 1, "z":0})
            self.communicate({"$type": "set_kinematic_state",
                              "id": basket_id,
                              "is_kinematic": True,
                              "use_gravity": False})

        # Create the object.
        # b04_geosphere001, chair_billiani_doll, b04_orange_00, b05_1_(1), b05_baseballnew_v03_12, b05_geosphere001, base-ball, prim_sphere
        object_id = self.add_object("b04_geosphere001",
                                    position={"x": 0.2, "y": 1, "z":0})
        # Set the scale, mass, and friction of the object.
        self.communicate({"$type": "scale_object",
                         "id": object_id,
                         "scale_factor": {"x":10, "y":10, "z":10}})
        self.communicate({"$type": "set_mass",
                         "id": object_id,
                         "mass": m_o})
        self.communicate({"$type": "set_physic_material",
                         "id": object_id,
                         "static_friction": s_o,
                         "bounciness": b_o})
        self.communicate({"$type":"set_color",
                         "color":{"r":0.5, "g":1, "b":0, "a":1},
                         "id": object_id})

        # nudge the ball onto the surface of the platform
        # self.communicate({"$type": "nudge_onto_surface",
        #                  "id": object_id,
        #                  "is_circle": False,
        #                  "nudge_step": 1.0,
        #                  "surface_object_id": ramp_id})

        # apply force to the ball
        self.communicate([{"$type": "apply_force_to_object",
                         "force": {"x": -8, "y": -0.1, "z": 0.5},
                         "id": object_id}])
           
        # Create the output directory.
        if os.path.exists(output_directory):
            shutil.rmtree(output_directory)
            sleep(0.5)
            os.mkdir(output_directory)

        # Capture n images.
        for i in range(nimages):
            # Look at the object.
            resp = self.communicate({"$type": "look_at_position",
                                    "avatar_id": "a",
                                    "position": {"x": -1.5, "y": 1, "z": 0}})
            images = Images(resp[0])
            frame = resp[-1]
            # Save the image.
            TDWUtils.save_images(images, frame, output_directory=output_directory)

    def run(self):
        self.start()
        
        # Create the room.
        self.communicate(TDWUtils.create_empty_room(20, 20, 1))
            
        # Run a trial.
        # self.trial(1.5, 0.05, 0.2, "./fall_roll_ramp_collide_output/images output/basket/run1_m1.5_s0.05_b0.2_blue", 200)
        self.trial(1.25, 0.05, 0.1, "./output/images output/collision2", 200)

        # Run a trial with different friction and bounciness parameters.
        # self.trial(1.5, 0.05, 0.9, "./fall_roll_ramp_collide_output/images output/basket/run2_m1.5_s0.05_b0.9_blue", 200)
        # self.trial(1.2, 0.05, 0.9, "./fall_roll_ramp_collide_output/images output/test4", 200)

if __name__ == "__main__":
    DropObject().run()




