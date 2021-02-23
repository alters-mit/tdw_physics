import os, io, glob
from pathlib import Path
import numpy as np
import h5py, json
from collections import OrderedDict
from PIL import Image


from tdw_physics.util import arr_to_xyz

def round_float(x, places=3):
    return round(float(x), places)

#################
#### STATIC #####
#################

def get_static_val(d, key='object_ids'):
    try:
        return np.array(d['static'][key])
    except KeyError:
        return None

def get_object_ids(d):
    return list(d['static']['object_ids'])

def avg_label(label_list):
    if len(label_list) == 0:
        return None
    elif all([label is None for label in label_list]):
        return None
    elif any([label is None for label in label_list]):
        label_list = [label if label is not None else np.NaN
                      for label in label_list]

    if isinstance(label_list[0], (bool, int, float)):
        return round(float(np.nanmean(label_list)), 3)
    elif isinstance(label_list[0], list):
        res = np.nanmean(np.stack([np.array(label) for label in label_list], 0), axis=0)
        return list(map(round_float, list(res)))
    elif isinstance(label_list[0], dict):
        res = {k: np.nanmean([label_list[i][k] for i in range(len(label_list))], axis=0)
               for k in label_list[0].keys()}
        return {k: round_float(v) for k,v in res.items()}
    elif isinstance(label_list[0], str):
        label_list = sorted(label_list)
        if all([label == label_list[0] for label in label_list]):
            return str(label_list[0])
        else:
            return str(label_list[0]) + '-' + str(label_list[-1])
    else:
        return None

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

def get_segment_map(d, frame_num=0):
    return get_pass_mask(d, frame_num=frame_num, img_key='_id')

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

def get_object_binary_mask(d, obj_id, frame_num=0):
    obj_ids = get_object_ids(d)
    inds = [i for i,oid in enumerate(obj_ids) if obj_id == oid]
    if len(inds) == 0:
        return None
    ind = inds[0]
    seg_colors = get_static_val(d, key='object_segmentation_colors')
    color = seg_colors[ind,:] # [3]

    segmap = get_segment_map(d, frame_num=frame_num)
    obj_mask = (segmap == color).max(axis=-1) # [H,W] <bool>

    return obj_mask

def get_object_mask_at_frame(d, object_key='target_id', frame_num=0):
    obj_id = get_static_val(d, object_key)
    return get_object_binary_mask(d, obj_id, frame_num)

def get_initial_target_mask(d):
    return get_object_mask_at_frame(d, 'target_id', 0)

def get_final_target_mask(d):
    return get_object_mask_at_frame(d, 'target_id', -1)

def get_zone_mask(d):
    return get_object_mask_at_frame(d, 'zone_id', 0)

def get_probe_mask(d):
    return get_object_mask_at_frame(d, 'probe_id', 0)

def object_visible_area(d, object_key='target_id', frame_num=0):
    obj_mask = get_object_mask_at_frame(d, object_key, frame_num)
    obj_area = obj_mask.sum()
    total_area = np.prod(obj_mask.shape)
    relative_area = float(obj_area) / float(total_area)
    return round(float(relative_area),3)

def silhouette_centroid(foreground):
    H,W = foreground.shape
    him = np.tile(np.linspace(-1.,1.,H)[:,None], [1,W])
    wim = np.tile(np.linspace(-1.,1.,W)[None,:], [H,1])
    hwim = np.stack([him, wim], -1) # [H,W,2]
    return np.sum(hwim * foreground[...,None], axis=(0,1)) / np.sum(foreground)

def get_mask_centroid(d, object_key='target_id', frame_num=0):
    obj_mask = get_object_mask_at_frame(d, object_key, frame_num)
    obj_centroid = silhouette_centroid(obj_mask.astype(float))
    return obj_centroid

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
    try:
        disp = arr_to_xyz(get_labels(d, 'target_delta_position')[-1])
        return {k:round(float(v), 3) for k,v in disp.items()}
    except TypeError:
        return None

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

def target_visible_area(d):
    return object_visible_area(d, 'target_id', 0)

def zone_visible_area(d):
    return object_visible_area(d, 'zone_id', 0)

def probe_visible_area(d):
    return object_visible_area(d, 'probe_id', 0)

def is_target_visible(d, thresh=0.025):
    try:
        return bool(target_visible_area(d) > thresh)
    except:
        return None

def is_zone_visible(d, thresh=0.025):
    try:
        return bool(zone_visible_area(d) > thresh)
    except:
        return None

def is_probe_visible(d, thresh=0.025):
    try:
        return bool(probe_visible_area(d) > thresh)
    except:
        return None

def target_mask_initial_centroid(d):
    centroid = get_mask_centroid(d, 'target_id', 0)
    return [float(centroid[0]), float(centroid[1])]

def target_mask_final_centroid(d):
    centroid = get_mask_centroid(d, 'target_id', -1)
    return [float(centroid[0]), float(centroid[1])]

def final_target_mask_displacement(d):
    c_init = target_mask_initial_centroid(d)
    c_final = target_mask_final_centroid(d)
    _round  = lambda x,y: round(float(x-y),3)
    return [_round(c_final[0], c_init[0]),
            _round(c_final[1], c_init[1])]

########################
#####INFRASTRUCTURE#####
########################
"""all data processing statistics are described with two functions
    (f, g)
where:
   -- g takes an hdf5 and produces a per-trial statistic

and

   -- f takes the outcomes of the per-trial statistics and returns a final summary scalar
"""

# set of funcs 'g' as defined above
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
    final_target_displacement,
    final_target_mask_displacement,
    target_visible_area,
    zone_visible_area,
    probe_visible_area
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
            print("%s is not a valid function on this dataset" % func)
        except KeyError:
            res[func.__name__] = None

    return res

def get_all_labels(d, res=None):
    return get_labels_from(d, label_funcs=get_all_label_funcs(), res=res)

def get_across_trial_stats_from(paths, funcs, agg_func=avg_label):
    fs = [h5py.File(path, mode='r') for path in paths]
    stats = {
        func.__name__ + '/' + agg_func.__name__: \
        agg_func(list(map(func, fs))) for func in funcs}

    for f in fs:
        f.close()

    return stats

if __name__ == '__main__':

    # filename = '/Users/db/neuroailab/physion/stimuli/scratch/domi_22/0001.hdf5'
    paths = glob.glob('/Users/db/neuroailab/physion/stimuli/scratch/domi_25/*.hdf5')
    res = get_across_trial_stats_from(paths, get_all_label_funcs(), avg_label)
    res_str = json.dumps(res, indent=4)
    print(res_str)

    # fs = [h5py.File(path, mode='r') for path in paths]
    # stats = {func.__name__: avg_label(list(map(func, fs)))
    #          for func in get_all_label_funcs()}
    # print(stats)
    # for f in fs:
    #     f.close()

    # f = h5py.File(filename)

    # res = get_all_labels(f)
    # for k,v in res.items():
    #     print (k, v)

    # f.close()
