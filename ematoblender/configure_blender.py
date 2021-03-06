__author__ = 'Kristy'

"""
Configure blender to look in this directory for scripts,
by setting the UserPreferencesFilePaths.script_directory
to the relevant place within the Ematoblender package.

Save the old User Preference settings in case a restore is required.
Only one backup is performed (initial state before Ematoblender settings are applied).

This is likely to be run from the commandline:
use "blender --factory-startup  --background --python PATH_TO_FILE/configure_blender.py" to set the UPs
use "blender --factory-startup --background --python PATH_TO_FILE/configure_blender.py --restore" to undo this
"""

import bpy
import os
import sys
from shutil import copy2, move


class UserPrefBackup(object):
    old_up_fp = bpy.utils.user_resource('CONFIG') + os.sep + 'old_userpref.blend'
    curr_up_fp = bpy.utils.user_resource('CONFIG') + os.sep + 'userpref.blend'

    @staticmethod
    def set_ematoblender_ups(loc):
        """Set the specific UPs needed for Ematoblender."""
        print('Gathering user preferences from', UserPrefBackup.curr_up_fp)

        # copy and rename the current UPs
        if not os.path.exists(UserPrefBackup.old_up_fp) and os.path.exists(UserPrefBackup.curr_up_fp):
            print('Copying old preferences to ', UserPrefBackup.old_up_fp)
            copy2(UserPrefBackup.curr_up_fp, UserPrefBackup.old_up_fp)
        else:
            print('Not copying old settings, as a copy already exists.')

        # change the UPs by adding the dir to UserPreferencesFilePaths.script_directory
        script_target = loc
        bpy.context.user_preferences.filepaths.script_directory = script_target
        bpy.ops.wm.save_userpref()

    @staticmethod
    def restore_old_ups():
        """Restore the UPs previously copied as a backup."""
        if os.path.exists(UserPrefBackup.old_up_fp):
            print('Resoring User Preferences from', UserPrefBackup.old_up_fp)
            move(UserPrefBackup.old_up_fp, UserPrefBackup.curr_up_fp)
        else:
            print("Old user preferences file does not exist")
            raise FileNotFoundError


if __name__ == "__main__":
    args = sys.argv[1:]
    if '--restore' in args:
        UserPrefBackup.restore_old_ups()
    else:
        UserPrefBackup.set_ematoblender_ups(
            os.path.abspath(
                os.path.normpath(
                    os.path.dirname(__file__) + '/scripts'
                )
            )
        )
