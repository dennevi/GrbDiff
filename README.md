# GrbDiff - Visualize changes in Gerber files

This is a wrapper for GerbV written in Python intended to make it easier for me to compare two versions of gerber files. I couldn\'t find a free and open-source diff-tool for gerber files so I threw togheter my own.

The main function of this script is to parse the filenames+extentions of the gerber files in order to automate which files to compare against each other. The second function is to generate png images of the layers and indicate where the differences are. After png images has been generated, it\'s much faster swiching between layers in a standard image viewer of your choice.

[![Screenshot](https://github.com/dennevi/GrbDiff/blob/main/screenshot.png?raw=true "Screenshot")](https://github.com/dennevi/GrbDiff/blob/main/screenshot.png?raw=true "Screenshot")

## Installation

Install [GerbV](http://gerbv.geda-project.org/). Binaries for Windows can be found [here](https://sourceforge.net/projects/gerbv-portable/files/).
<p>Install [Python3](https://www.python.org/downloads/). I recommend also installing pip and adding Python+pip to your PATH.
<p>Install these Python plugins (only needed for the png export):
- scikit-image
- imutils
- opencv-python

If you\'re unfamiliar with how to install python plugins on your system, try one of these commands in Command Promt in Windows or a Terminal in Linux:
- pip3 install scikit-image
- pip install scikit-image
- python3 -m pip install scikit-image
- python -m pip install scikit-image

Hopefully one of these works and then use that one to install imutils and opencv-python as well. If it doesn\'t work you probably don\'t have pip in your PATH or you don\'t have it installed at all. You\'ll figure it out. If you don\'t mange to get it to work, maybe https://gerbercompare.com/ is a better choice for you.

## Usage
- Run GrbDiff.py using Python
- Select your two gerbers. If you select a zip-file, the gerber files should not be placed in folder in the zip file. If you select a gerber-file, all files in that folder will be opened.
- Select where GerbV (or GerbVPortable) is located.
- Select an export png dir if you plan on exporting to png. I prefer to export to png since it\'s very quick and easy to switch between different layers in an image viewer.
- Use \"Diff in GerbV\" to view single layer from both gerber files in GerbV. In GerbV you can select different modes for viewing. \"Fast, with XOR\" is often a good mode to see differences between layers.
- Use \"Open Gerber in GerbV\" to open the entire board in GerbV with the color template selected (\"GerbV View Gerber template\")
- \"Export png\" exports all layers of both gerbers, and also a combined image of every layer. The differences between the layers are calculated and the differences are marked on the exported images. For this to work both gerber files must have the exact same resolution. To increase the chance of getting the same resolution on the png export the outline of the pcb is incuded in every layer.
- The DPI of the png export can be increased (or decreased) from the default 300 DPI, but if you go to high you may run out of memory for the calculation of the differences between the layers. The error will say "Unable to allocate XXX. MiB for an array...". I coundn\'t go higher than 450 DPI when I tried this.

### Use GrbDiff as a difftool in git or elsewhere
Normally GrbDiff will open the same files as last time the application were used. The filepaths are saved in settings.ini. You can supply the filepaths as arguments instead. This is useful if you\'d like to invoke GrbDiff as a difftool directly from git. How this is done exactly is not described here.
<p>Example:
<br>`
python GrbDiff.py "C:\gerber1.zip" "C:\gerber2.zip"
`
<p>If the gerber files are located in the same directory (or temp directory), it may be a bad idea for the application to try to find other files in the same directory. In this case you can use the \"-s\" argument to tell GrbDiff to only compare the two files supplied.
<p>Example:
<br>`
python GrbDiff.py -s "C:\temp\SDU-404-B-L1.gtl" "C:\temp\SDU-404-C-L1.gtl"
`
## License, credits and how you could help
Do what you like with it I guess. I\'m happy if it helps you in any way, and even happier if someone want\'s to improve this in the future. In this project or in a fork.

A code snippet is borrowed from \"borrowed\" from Alison Américo: [image-difference](https://github.com/alisonamerico/image-difference/blob/master/image_diff.py)

This script is written by Albin Dennevi. I\'m not a software developer and I don\'t have the time to do much more work on this. The code is probably riddled with bugs and could use much improvement. If you make some improvements, please issue a pull request.

One simple thing that anyone could improve much on is to make better color templates. Have a look at the source, it\'s easy to see how this is done. If you need more/other layers then the layers that I\'ve defined it\'s also easy to add more.

My mail is my firstname + a in a circle + my lastname + dot + com
