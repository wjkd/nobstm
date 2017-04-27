# No Bullsh*t Tiling Manager

A Python tiling script for window managers without native tiling support that represents windows as the leaves of a full binary tree (ie. like [bspwm](https://github.com/baskerville/bspwm))

The script has only been tested on openbox. I can't guarantee that it would work as it should so try at your own risk.

Bind it to a hotkey manager of your choice or make it autostart.

## Requirements

* x11 and an EWMH/NetWM compatible window manager
* wmctrl
* xdotool
