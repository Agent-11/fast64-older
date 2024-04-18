# Fast64

This requires Blender 3.2+.

Forked from [djoslin0/fast64-coop-mods](https://github.com/djoslin0/fast64-coop-mods).

![alt-text](/images/mario_running.gif)

This is a Blender plugin that allows one to export F3D display lists. It also has the ability to export assets for Super Mario 64 and Ocarina of Time decompilation projects. It supports custom color combiners / geometry modes / etc. It is also possible to use exported C code in homebrew applications.

This fork of Fast64 is intended for the use of creating assets for sm64coopdx. It contains new features, such as disabling vertex integer rounding in case exact precision is needed, the option to delete generated DynOS files (.bin, .lvl) when exporting Geolayouts and levels respectively, a new scrolling texture menu when choosing the "Scrolling Texture Manager" behavior for an object, a fix for persistent blocks clearing on custom level export and an updated Mario blend by Agent X that fixes a glaring inaccuracy with the cap in hand states.

Make sure to save often, as this plugin is prone to crashing when creating materials / undoing material creation. This is a Blender issue.

<https://developer.blender.org/T70574>


![alt-text](/images/mat_inspector.png)

### Credits
Thanks to anonymous_moose, Cheezepin, Rovert, and especially InTheBeef for testing.
Thanks to InTheBeef for LowPolySkinnedMario.

### Table of Contents
1. [ Super Mario 64 ](/fast64_internal/sm64/README.md)
2. [ Ocarina Of Time ](/fast64_internal/oot/README.md)

### Installation
Download the repository as a zip file. In Blender, go to Edit -> Preferences -> Add-Ons and click the "Install" button to install the plugin from the zip file. Find the Fast64 addon in the addon list and enable it. If it does not show up, go to Edit -> Preferences -> Save&Load and make sure 'Auto Run Python Scripts' is enabled.

### Tool Locations
The tools can be found in the properties sidebar under the 'Fast64' tab (toggled by pressing N).
The F3D material inspector can be found in the properties editor under the material tab.

### F3D Materials
Any exported mesh must use an F3D Material, which can be added by the 'Create F3D Material' button in the material inspector window. You CANNOT use regular blender materials. If you have a model with Principled BSDF materials, you can use the Principled BSDF to F3D conversion operator to automatically convert them. The image in the "Base Color" slot will be set as texture 0, while the image in the "Subsurface Color" slot will be set as texture 1.

### Vertex Colors
To use vertex colors, select a vertex colored texture preset and add two vertex color layers to your mesh named 'Col' and 'Alpha'. The alpha layer will use the greyscale value of the vertex color to determine alpha.

### Large Texture Mode
In F3D material properties, you can enable "Large Texture Mode". This will let you use textures up to 1024x1024 as long as each triangle in the mesh has UVs that can fit within a single tile load. Fast64 will categorize triangles into shared tile loads and load the portion of the texture when necessary.

### Decomp vs Homebrew Compatibility
There may occur cases where code is formatted differently based on the code use case. In the tools panel under the Fast64 File Settings subheader, you can toggle homebrew compatibility.

### Converting To F3D v5 Materials
A new optimized shader graph was introduced to decrease processing times for material creation and exporting. If you have a project that still uses old materials, you may want to convert them to v5. To convert an old project, click the "Recreate F3D Materials As V5" operator near the top of the Fast64 tab in 3D view. This may take a while depending on the number of materials in the project. Then go to the outliner, change the display mode to "Orphan Data" (broken heart icon), then click "Purge" in the top right corner. Purge multiple times until all of the old node groups are gone.

### Updater

Fast64 features an updater ([CGCookie/blender-addon-updater](https://github.com/CGCookie/blender-addon-updater)).

It can be found in the addon preferences:

![How the updater in the addon preferences looks, right after addon install](/images/updater_initially.png)

Click the "Check now for fast64 update" button to check for updates.

![Updater preferences after clicking the "check for updates" button](/images/updater_after_check.png)

Click "Install main / old version" and choose "Main" if it isn't already selected:

![Updater: install main](/images/updater_install_main.png)

Click OK, there should be a message "Addon successfully installed" and prompting you to restart Blender:

![Updater: successful install, must restart](/images/updater_success_restart.png)

Clicking the red button will close Blender. After restarting, fast64 will be up-to-date with the latest main revision.

### Fast64 Development
If you'd like to develop in VSCode, follow this tutorial to get proper autocomplete. Skip the linter for now, we'll need to make sure the entire project gets linted before enabling autosave linting because the changes will be massive.
https://b3d.interplanety.org/en/using-microsoft-visual-studio-code-as-external-ide-for-writing-blender-scripts-add-ons/

#### Formatting

We use [Black](https://black.readthedocs.io/en/stable/index.html).

To make VS Code use it, change the `python.formatting.provider` setting to "black". VS Code will ask you to install Black if not already installed.

To format the whole repo, run `black .` (or `python3 -m black .` depending on how it is installed) from the root of the repo.

The (minimal) configuration for Black is in `/pyproject.toml`.

#### Updater notes

Be careful if testing the updater when using git, it may mess up the .git folder in some cases.

Also see the extensive documentation in the https://github.com/CGCookie/blender-addon-updater README.

The "Update directly to main" button uses `bl_info["version"]` as the current version, and versions parsed from git tags as other versions. This means that to create a new version, the `bl_info` version should be bumped and a corresponding tag should be created (for example `"version": (1, 0, 2),` and a `v1.0.2` tag). This tag will then be available to update to, if it denotes a version that is more recent than the current version.

The "Install main / old version" button will install the latest revision from the `main` branch.
