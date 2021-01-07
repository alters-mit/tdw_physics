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
                           "position": {"x": 4, "y": 2.5, "z": 5}},
                           {"$type": "set_pass_masks",
                           "avatar_id": "a",
                           "pass_masks": ["_img", "_id"]},
                           {"$type": "send_images",
                           "frequency": "always"},
                           ])
         
        # Create the fridge and the chair.
        # b04_kenmore_refr_70419, b03_ka90ivi20r_2013__vray, b05_amati_red_violin
        static_id = self.add_object("b05_amati_red_violin",
                                    position={"x": -3, "y": 0, "z":1})
        throw_id = self.add_object("b03_dumbbell_vray",
                                   position={"x": 1, "y": 1.5, "z": -1})

        # Set the mass of the fridge and the chair.
        self.communicate([{"$type": "set_mass",
                          "id": static_id,
                          "mass": 40},
                          {"$type": "set_mass",
                          "id": throw_id,
                          "mass": 20}
                          ])

        # Apply a force to the chair.
        self.communicate({"$type": "apply_force_to_object",
              "force": {"x": -250, "y": -10, "z": 0},
              "id": throw_id})

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
        self.trial("./output/images output/nocollision2_2", 200)

if __name__ == "__main__":
    DropObject().run()




