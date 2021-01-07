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
    def trial(self, output_directory, nimages):
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
         
        # place the elevated platform
        platform_id = self.add_object("fridge_box",
                                   position={"x": 1, "y": 0, "z":0})
        self.communicate({"$type": "set_kinematic_state",
                      "id": platform_id,
                      "is_kinematic": True,
                      "use_gravity": False})
                      
        # place a table
        table_id = self.add_object("quatre_dining_table",
                                   position={"x": -4, "y": 0, "z": -1})
        self.communicate({"$type": "rotate_object_by",
                         "angle": -45,
                         "id": table_id})
        
        # place an object on the ground (b05_microsoft_surface_rt,big_glass_bowl_water,b05_seamodel5_(2015))
        collider_id = self.add_object("b05_seamodel5_(2015)",
                                   position={"x": -1, "y": 0, "z": 0})
        self.communicate({"$type": "scale_object",
                          "id": collider_id,
                          "scale_factor": {"x":1, "y":1, "z":1}})
        
        # Create the falling object. (piano_max2017, villaverde_-_murano_luna_chandelier)
        object_id = self.add_object("piano_max2017",
                                    position={"x": -1, "y": 2.5, "z":0})
        # Set the scale, mass, and friction of the object.
        self.communicate({"$type": "scale_object",
                         "id": object_id,
                         "scale_factor": {"x":1, "y":1, "z":1}})
        # self.communicate({"$type":"set_color",
        #                  "color":{"r":0, "g":0, "b":1, "a":1},
        #                  "id": object_id})

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
        self.trial("./output/images output/collision2", 200)

if __name__ == "__main__":
    DropObject().run()




