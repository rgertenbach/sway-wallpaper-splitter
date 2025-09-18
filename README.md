# Sway Wallpaper Splitter

A simple tool to scale and cut wallpapers for swaybg, especially useful for
multi monitor setups.

![Wallpaper splitter in use](https://i.imgur.com/ya4NxvI.png)

If the image is zoomed in more than the original resolution the monitor setup
will be orange.\
If the image doesn't cover all screens fully the monitor setup will be red.

Usage:

1.  Launch the program with `./sway-wallpaper-splitter.py my-wp.jpg target_dir`
    *   `my-wp.jpg` is the path to to a wallpaper.
    *   `target_dir` is the directory path where the cut files are stored.
2.  Scale the image with the scroll wheel and move it around with drag and drop.
    *   Right click to reset the size to the original and cycle through scaling
        the image to fit the width and the height of the desktop setup.
    *   You can drag with Shift to move along a single axis.
    *   Middle click resets the location of the wallpaper to start at the top
        left corner of the desktop.
3.  Confirm your selection with the space bar.
4.  The program will outpuot the split pictures into `target_dir` as pngs.
    The names will be the output they are for (e.g. DP-1.png).

Dependencies:

*   Python3
*   [PySide6](https://pypi.org/project/PySide6)
*   [pillow](https://pypi.org/project/pillow)
