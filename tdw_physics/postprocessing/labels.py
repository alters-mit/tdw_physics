import os, io
from pathlib import Path
import numpy as np
import h5py, json
from collections import OrderedDict
from PIL import Image


from tdw_physics.util import arr_to_xyz

#################
#### IMAGES #####
#################

def get_pass_mask(d, frame_num=0, img_key='_img'):
    assert img_key in ['_id', '_img', '_depth', '_normal', '_flow'], img_key
    frames = list(d['frames'].keys())
    frames.sort()
    img = d['frames'][frames[frame_num]]['images'][img_key][:]
    img = Image.open(io.BytesIO(img))
    return np.array(img)

def get_segment_map(d):
    return get_pass_mask(d, img_key='_id')

def get_hashed_segment_map(d, val=256):
    segmap = get_segment_map(d) # [H,W,3]
    out = np.zeros(segmap.shape[:2], dtype=np.int32)
    for c in range(segmap.shape[-1]):
        out += segmap[...,c] * (val ** c)
    return out

def get_object_masks(d, exclude_background=True):
    hashed_segmap = get_hashed_segment_map(d)
    obj_ids = list(np.unique(hashed_segmap))
    obj_ids.sort()
    masks = np.array(obj_ids).reshape((1,1,-1)) == hashed_segmap[...,None]
    return masks[...,1:] if exclude_background else masks

#################
#### LABELS #####
#################

def get_collisions(d, idx, env_collisions=False):
    fkeys = [k for k in d['frames'].keys()]
    return d['frames'][fkeys[idx]]['collisions' if not env_collisions else 'env_collisions']

def find_collisions_frames(d, cdata='contacts', env_collisions=False):
    n_frames = len([k for k in d['frames'].keys()])
    collisions = []
    for n in range(n_frames):
        contacts = get_collisions(d, n, env_collisions)[cdata]
        collisions.append(bool(len(contacts)))
    return np.where(collisions)[0]

def get_frames(d):
    frames = list(d['frames'].keys())
    frames.sort()
    return frames

def num_frames(d):
    return len(get_frames(d))

def get_labels(d, label_key='trial_end'):
    try:
        return list([np.array(d['frames'][fr]['labels'][label_key]) for fr in get_frames(d)])
    except KeyError:
        return None

def is_trial_valid(d, valid_key='trial_end'):
    labels = get_labels(d, valid_key)
    if labels is not None:
        return any(labels)
    else:
        return None

def is_trial_at_least(d, n=150):
    return num_frames(d) >= n

def is_trial_timeout(d):
    return is_trial_valid(d, 'trial_timeout')

def is_trial_complete(d):
    return is_trial_valid(d, 'trial_complete')

def does_trial_have_target(d):
    return is_trial_valid(d, 'has_target')

def does_trial_have_zone(d):
    return is_trial_valid(d, 'has_zone')

def does_target_contact_zone(d):
    return is_trial_valid(d, 'target_contacting_zone')

def does_target_move(d):
    return is_trial_valid(d, 'target_has_moved')

def does_target_miss_zone(d):
    return (does_target_move(d) and not does_target_contact_zone(d))

def does_target_hit_ground(d):
    return is_trial_valid(d, 'target_on_ground')

def final_target_displacement(d):
    disp = arr_to_xyz(get_labels(d, 'target_delta_position')[-1])
    return {k:round(float(v), 3) for k,v in disp.items()}

def get_valid_frames(d, label_key):
    return np.where(get_labels(d, label_key))[0]

def first_frame(d, label_key):
    valid_frames = get_valid_frames(d, label_key)
    return int(valid_frames[0]) if len(valid_frames) else None

def first_target_move_frame(d):
    return first_frame(d, 'target_has_moved')

def first_target_contact_zone_frame(d):
    return first_frame(d, 'target_contacting_zone')

def first_target_hit_ground_frame(d):
    return first_frame(d, 'target_on_ground')

########################
#####INFRASTRUCTURE#####
########################

TRIAL_LABELS = [
    num_frames,
    is_trial_valid,
    does_target_move,
    does_target_contact_zone,
    does_target_miss_zone,
    does_target_hit_ground,
    first_target_move_frame,
    first_target_contact_zone_frame,
    first_target_hit_ground_frame,
    final_target_displacement
]

def get_all_label_funcs():
    return TRIAL_LABELS

def get_labels_from(d, label_funcs, res=None):
    if res is None:
        res = OrderedDict()

    for func in label_funcs:
        try:
            res[func.__name__] = func(d)
        except AttributeError:
            print("%s is not a valid function", func)
        except KeyError:
            res[func.__name__] = None

    return res

def get_all_labels(d, res=None):
    return get_labels_from(d, label_funcs=get_all_label_funcs(), res=res)
