# Changelog

## 0.4.1

- Added `mass_scale` parameter to `RigidbodyDataset.get_add_physics_object()`

## 0.4.0

- Refactored for TDW v1.9.0 (`tdw_physics` now requires TDW v1.9.0 or newer)
- Removed `physics_info_calculator.py`
- Moved `PhysicsInfo` class and `PHYSICS_INFO` dictionary to `tdw_physics.physics_info`

## 0.3.1

- `tdw_physics` now requires TDW v1.8
- Fixed the names of some of the scenes to match those in TDW v1.8
- Fixed code examples in the README 

## 0.3.0

- Added a function to reshape the `_depth` pass in order to stay compatible with TDW v1.7.15 (the `_depth` pass is now far more accurate).

## 0.2.1

- Removed some code made redundant by TDW v1.7
- Fixed: Controllers automatically launch the build (which doesn't work on headless servers).

## 0.2.0

- Updated documentation for TDW public release.
  - Expanded system requirements section.
- Updated URLs custom model libraries to TDW v1.6 URLs.

## 0.1.1

### Controllers

- `squishing.py`: In trials in which one object is dropped onto another, the "dropped" object is a solid object instead of a squishy cloth object.

## 0.1.2

- Added optional `launch_build` parameter to each controller constructor.