import os
import shutil
import ntpath
import fnmatch
import subprocess
import tempfile
import time
import sys
from configparser import ConfigParser
from tkinter import *
from tkinter.ttk import *
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import askdirectory
from tkinter import messagebox
from zipfile import ZipFile

# Definition of all layers to be recognized.
# https://www.pcbway.com/helpcenter/technical_support/Gerber_File_Extention_from_Different_Software.html
# Specify layer name, an array of patterns to look for, one pattern to dismiss.
# When opening gerber files, the application will begin to look for the first pattern in the first layer. Then the
# second pattern of the first layer and so on. As soon as a layer has been found, that file will not be tagged for
# another layer even if it happens to match a filter on a sequent layer.
# It's important that the last layer is the outline of the pcb, since this is included in all layers when exporting
# to png.
filetypes = [
               ['Top Solder Paste', ['*.gtp', '*-F?Paste.*', '*.crc', '*.tsp', '*.stp', '*.toppaste.gbr', '*.creammask_top.gbr', '*.tcream.ger'], ''],
               ['Top Silk Screen', ['*.gto', '*-F?SilkS.*', '*.plc', '*.tsk', '*.sst', '*.silkscreen_top.gbr', '*.topsilk.gbr', '*.topsilkscreen.ger', 'to'], ''],
               ['Top Solder Mask', ['*.gts', '*-F?Mask.*', '*.stc', '*.tsm', '*.smt', '*.topmask.gbr', '*.soldermask_top.gbr', '*.topsoldermask.ger', 'ts'], ''],
               ['Copper Layer L1', ['*.gtl', '*-L1.*', '*.g1', '*-F?Cu*', '*.cmp', '*.top', '*.top.gbr', '*.copper_l1.gbr', '*.toplayer.ger', 'tl'], '*.pos'],
               ['Copper Layer L2', ['*.g1', '*.g2', '*-L2.*', '*-In1?Cu*', '*-Inner1?Cu*', '*.ly1', '*.ly2', '*.in1', '*.internalplane1.ger', '*.gbl', '*-B?Cu*', '*.sol', '*.bot', '*.copper_l2.gbr', '*.bottomlayer.ger', 'l2', 'bl'], '*.pos'],
               ['Copper Layer L3', ['*.g2', '*.g3', '*-L3.*', '*-In2?Cu*', '*-Inner2?Cu*', '*.ly2', '*.ly3', '*.in2', '*.internalplane2.ger', '*.gbl', '*-B?Cu*', '*.sol', '*.bot', '*.copper_l3.gbr', '*.bottomlayer.ger', 'l3', 'bl'], '*.pos'],
               ['Copper Layer L4', ['*.g3', '*.g4', '*-L4.*', '*-In3?Cu*', '*-Inner3?Cu*', '*.ly3', '*.ly4', '*.in3', '*.internalplane3.ger', '*.gbl', '*-B?Cu*', '*.sol', '*.bot', '*.copper_l4.gbr', '*.bottomlayer.ger', 'l4', 'bl'], '*.pos'],
               ['Copper Layer L5', ['*.g4', '*.g5', '*-L5.*', '*-In4?Cu*', '*-Inner4?Cu*', '*.ly4', '*.ly5', '*.in4', '*.internalplane4.ger', '*.gbl', '*-B?Cu*', '*.sol', '*.bot', '*.copper_l5.gbr', '*.bottomlayer.ger', 'l5', 'bl'], '*.pos'],
               ['Copper Layer L6', ['*.g5', '*.g6', '*-L6.*', '*.gbl', '*-B?Cu*', '*.sol', '*.bot', '*.bottom.gbr', '*.copper_l6.gbr', '*.bottomlayer.ger', 'bl'], '*.pos'],
               ['Bottom Solder Mask', ['*.gbs', '*-B?Mask.*', '*.sts', '*.bsm', '*.smb', '*.bottommask.gbr', '*.soldermask_bottom.gbr', '*.bottomsoldermask.ger', 'bs'], ''],
               ['Bottom Silk Screen', ['*.gbo', '*-B?SilkS.*', '*.pls', '*.bsk', '*.ssb', '*.silkscreen_bottom.gbr', '*.bottomsilk.gbr', '*.bottomsilkscreen.ger'], ''],
               ['Bottom Solder Paste', ['*.gbp', '*-B?Paste.*', '*.crs', '*.bsp', '*.spb', '*.bottompaste.gbr', '*.creammask_bottom.gbr', '*.bcream.ger'], ''],
               ['Plated Drill File', ['*-PTH.drl', '*.drl', '*.txt', '*.xln', '*.exc', '*.drd', '*.tap', '*.fab.gbr', '*.plated-drill.cnc', 'drl'], '*NPTH*'],
               ['Non-Plated Drill File', ['*NPTH.drl', '*.holes_npth.xln'], ''],
               ['Eco1 Layer', ['*-User?Eco1.*', '*-Eco1?User.*', 'vcut'], ''],
               ['Outline of PCB', ['*.gm1', '*-Edge?Cuts.*', '*.gko', '*.gm3', '*.dim', '*.gml', '*.fab', '*.out.gbr', '*.board_outline.gbr', '*.boardout.ger', 'ko'], ''],
            ]

# Color templates for viewing all layers at the same time in GerbV
# Specify template name, background color, an array with color for each layer and a corresponding layer index in the
# 'filetypes'-array. The order of the "layers" in this array will be the order of the layers in GerbV. The order is
# important since the first layer will be drawn on top of all sequent layers, and so on.
pcb_color_template = [
                        ['Green Copper Layers on Black background', '#000000',
                            [
                                ['#CAFD34FF', 15],  # Outline of PCB
                                ['#00C3C3B1', 14],  # Eco1 Layer
                                ['#FFFF00C8', 12],  # Plated Drill File
                                ['#FF00E4C8', 13],  # Non-Plated Drill File
                                ['#FCFCFCB1', 1],   # Top Silk Screen
                                ['#B6000B64', 0],   # Top Solder Paste
                                ['#00027EA6', 2],   # Top Solder Mask
                                ['#FCFCFCB1', 10],  # Bottom Silk Screen
                                ['#B6000B64', 11],  # Bottom Solder Paste
                                ['#00027EA6', 9],   # Bottom Solder Mask
                                ['#00690BAF', 3],   # Copper Layer L1
                                ['#00690BAF', 4],   # Copper Layer L2
                                ['#00690BAF', 5],   # Copper Layer L3
                                ['#00690BAF', 6],   # Copper Layer L4
                                ['#00690BAF', 7],   # Copper Layer L5
                                ['#00690BAF', 8],   # Copper Layer L6
                            ]
                        ],
                        ['Pastel Colors on Black background', '#000000',
                             [
                                 ['#CAFD34FF', 15],  # Outline of PCB
                                 ['#00C3C3B1', 14],  # Eco1 Layer
                                 ['#F1FFB7B1', 12],  # Plated Drill File
                                 ['#FFCAE1B1', 13],  # Non-Plated Drill File
                                 ['#FCFCFCB1', 1],  # Top Silk Screen
                                 ['#B6000B64', 0],  # Top Solder Paste
                                 ['#00027EA6', 2],  # Top Solder Mask
                                 ['#FCFCFCB1', 10],  # Bottom Silk Screen
                                 ['#B6000B64', 11],  # Bottom Solder Paste
                                 ['#00027EA6', 9],  # Bottom Solder Mask
                                 ['#FF7F73B1', 3],  # Copper Layer L1
                                 ['#C100E0B1', 4],  # Copper Layer L2
                                 ['#75F267B1', 5],  # Copper Layer L3
                                 ['#00C3C3B1', 6],  # Copper Layer L4
                                 ['#D11B68B1', 7],  # Copper Layer L5
                                 ['#FFC533B1', 8],  # Copper Layer L6
                             ]
                         ],
                     ]

# Color templates for exporting the gerbers to png.
png_color_template = [
                       ['Green Copper Layers on White background',  # Template Name
                        '#FFFFFF',    # Background
                        '#00690B',    # Gerber 1 color
                        '#00690B',    # Gerber 2 color
                        '#00FF0880',  # Gerber 1 color on the combined picture
                        '#0000A7FF',  # Gerber 2 color on the combined picture
                       ],
                       ['Green and Blue Copper Layers on White background',  # Template Name
                        '#FFFFFF',    # Background
                        '#00690B',    # Gerber 1 color
                        '#000080',    # Gerber 2 color
                        '#00FF0880',  # Gerber 1 color on the combined picture
                        '#0000A7FF',  # Gerber 2 color on the combined picture
                       ],
                     ]

# Color templates for "diff" of a particular layer in GerbV.
diff_gerbv_args = [
                ["Red and Blue on Black", "--background=#000000", "--foreground=#ff000055", "--foreground=#0000ff"],
                ["Yellow and Blue on White", "--background=#ffffff", "--foreground=#ffff0064", "--foreground=#0000ff64"],
             ]

# Write Settings file
def write_settings_file():
    settings_object.write(open('settings.ini', 'w'))

# Read Settings file. Create it if it doesn't exist.
settings_object = ConfigParser()
if not os.path.exists('settings.ini'):
    settings_object['PATHS'] = {'gerbv_path': '', 'grb_file1': '', 'grb_file2': '', 'png_export_path': ''}
    settings_object['TEMPLATES'] = {'diff_color_combobox': 0, 'png_color_combobox': 0, 'gerber_color_combobox': 0}
    settings_object['OTHER'] = {'png_export_dpi': '300'}
    write_settings_file()
else:
    # Read File
    settings_object.read('settings.ini')
settings_paths = settings_object['PATHS']
settings_templates = settings_object['TEMPLATES']
settings_other = settings_object['OTHER']

# Check if files are supplied as arguments
gerber1_arg = ''
gerber2_arg = ''
single_gerber = False
arguments = sys.argv
if(len(arguments)>1):
    for a in list(arguments):
        print('Got argument:', a)
        if(a=='-s'):
            print('Argument -s found. Will not look for other gerber files in same folder.')
            single_gerber = True
            arguments.remove(a)

    if (len(arguments) > 1):
        gerber1_arg = arguments[1]
        print('First file to compare with:', gerber1_arg)
        arguments.pop(1)

    if (len(arguments) > 1):
        gerber2_arg = arguments[1]
        print('Second file to compare with:', gerber2_arg)
        arguments.pop(1)
else:
    print('No arguments supplied.')

# create root window
root = Tk()

# root window title and dimension
root.title("GrbDiff - Visualize changes in Gerber files")
root.geometry('1200x820')

# Create A Main frame
main_frame = Frame(root)
main_frame.pack(fill=BOTH,expand=1)

# Create Frame for X Scrollbar
sec = Frame(main_frame)
sec.pack(fill=X,side=BOTTOM)

# Create A Canvas
my_canvas = Canvas(main_frame)
my_canvas.pack(side=LEFT,fill=BOTH,expand=1)

# Add A Scrollbars to Canvas
x_scrollbar = Scrollbar(sec,orient=HORIZONTAL,command=my_canvas.xview)
x_scrollbar.pack(side=BOTTOM,fill=X)
y_scrollbar = Scrollbar(main_frame,orient=VERTICAL,command=my_canvas.yview)
y_scrollbar.pack(side=RIGHT,fill=Y)

# Configure the canvas
my_canvas.configure(xscrollcommand=x_scrollbar.set)
my_canvas.configure(yscrollcommand=y_scrollbar.set)
my_canvas.bind("<Configure>",lambda e: my_canvas.config(scrollregion= my_canvas.bbox(ALL))) 

# Create Another Frame INSIDE the Canvas
second_frame = Frame(my_canvas)

# Add that New Frame a Window In The Canvas
my_canvas.create_window((0,0),window= second_frame, anchor="nw")

row=1
dpi_entry_variable = StringVar()  # Declaration

# Add headlines
second_frame.grid_rowconfigure(row, minsize=15)
row = row + 1
headline_layername = Label(second_frame, text="Layer Name", font='bold')
headline_layername.grid(column=1, row=row, sticky=W, padx=10)
headline_gerber1 = Label(second_frame, text="Gerber 1", font='bold')
headline_gerber1.grid(column=2, row=row, sticky=W, padx=10)
headline_gerber2 = Label(second_frame, text="Gerber 2", font='bold')
headline_gerber2.grid(column=3, row=row, sticky=W, padx=10)
headline_difflayer = Label(second_frame, text="Diff Layer", font='bold')
headline_difflayer.grid(column=4, row=row, sticky=W, padx=10)
row = row + 1

layernames = []
firstgerbers = []
secondgerbers = []
diffbutton = []

global gerber1_path
gerber1_path = ''
global gerber2_path
gerber2_path = ''

def diff_gerbers(x):
    if(not gerbv_path["text"]):
        messagebox.showwarning("No GerbV", f"You must first select a GerbV binary.")
        
    print("Color template for diff of gerbers:", diff_gerbv_args[diff_color_combobox.current()][0])
    print(x, filetypes[x][0])
    if (firstgerbers[x].get() == "---"):
        messagebox.showwarning("Info", f"No Gerber 1 file to diff with.")
    elif (secondgerbers[x].get() == "---"):
        messagebox.showwarning("Info", f"No Gerber 2 file to diff with.")
    else:
        print(gerbv_path["text"])
        filepath1 = os.path.join(gerber1_path, firstgerbers[x].get()).replace("/", os.sep)
        print(filepath1)
        filepath2 = os.path.join(gerber2_path, secondgerbers[x].get()).replace("/", os.sep)
        print(filepath2)
        process_args = [gerbv_path["text"], filepath1, filepath2]
        for a in diff_gerbv_args[diff_color_combobox.current()][1:]:
            process_args.append(a)
        print("Starting GerbV with these args:", process_args)
        subprocess.Popen(process_args, stdin=None, stdout=None, stderr=None)

for index, value in enumerate(filetypes):
    print(index, "Layer:", value[0], "Exp0:", value[1][0])
    layernames.append(Label(second_frame, text=value[0]))
    layernames[index].grid(column=1, row=row, sticky=W, padx=10)
    firstgerbers.append(Combobox(second_frame, width=70, values=["---"]))
    firstgerbers[index].grid(column=2, row=row, sticky=W, padx=10)
    firstgerbers[index].set("---")
    secondgerbers.append(Combobox(second_frame, width=70, values=["---"]))
    secondgerbers[index].grid(column=3, row=row, sticky=W, padx=10)
    secondgerbers[index].set("---")
    diffbutton.append(Button(second_frame, text='Diff in GerbV',command=lambda index=index: diff_gerbers(index)))
    diffbutton[index].grid(column=4, row=row, sticky=W, padx=10)
    row = row+1

second_frame.grid_columnconfigure(2, minsize=250)
second_frame.grid_columnconfigure(3, minsize=250)

def select_gerber_file(sel):
    sel_file = askopenfilename(title="Select a Gerber File or Zip archive", filetypes=[('Gerber files', '*.*')])
    if sel_file != '':
        if (sel == 1):
            settings_paths['grb_file1'] = sel_file
            write_settings_file()
        else:
            settings_paths['grb_file2'] = sel_file
            write_settings_file()
        open_gerber_file(sel_file, sel)

def open_gerber_file(sel_file, sel):
    # Clear filelist
    if (sel==1):
        for grb_file in firstgerbers:
            grb_file['values'] = "---"
            grb_file.set("---")
    else:
        for grb_file in secondgerbers:
            grb_file['values'] = "---"
            grb_file.set("---")

    listOfGlobals = globals()

    if (sel_file.endswith(".zip")):
        print("Chosen file is a zip archive.")
        if (sel==1):
            gerber1_dir.configure(text=sel_file)
            tmp_dir_name = "GrbDiff-Zip1"
            filedir = os.path.join(tempfile.gettempdir(), tmp_dir_name)
            listOfGlobals['gerber1_path'] = filedir
        else:
            gerber2_dir.configure(text=sel_file)
            tmp_dir_name = "GrbDiff-Zip2"
            filedir = os.path.join(tempfile.gettempdir(), tmp_dir_name)
            listOfGlobals['gerber2_path'] = filedir

        # If the directory exists, remove it
        if os.path.exists(filedir):
            shutil.rmtree(filedir)

        # Wait for the directory to be removed
        for delay in 0.1, 0.2, 0.3, 0.4, 0.5, 0.6:
            if not os.path.exists(filedir): break
            time.sleep(delay)

        # Create the directory
        os.mkdir(filedir)

        # Unpack zip archive
        with ZipFile(sel_file, 'r') as zipObj:
            # Extract all the contents of zip file in current directory
            zipObj.extractall(filedir)
    else:
        filedir = ntpath.dirname(sel_file)
        if (sel==1):
            gerber1_dir.configure(text=filedir)
            listOfGlobals['gerber1_path'] = filedir
        else:
            gerber2_dir.configure(text=filedir)
            listOfGlobals['gerber2_path'] = filedir


    print("Selected filepath for Gerber", sel, ":", filedir)

    if (single_gerber == True):
        print("Just using the single file supplied as argument.")
        filelist = [ntpath.basename(sel_file)]
    else:
        # Get all files an folders in path, and discard the folders
        filelist = [f for f in os.listdir(filedir) if os.path.isfile(os.path.join(filedir, f))]
        print("Files in path:")
    print(filelist)

    temp_filelist = filelist.copy()
    filelist_with_null = filelist.copy()
    filelist_with_null.insert (0, "---")
    for index, value in enumerate(filetypes):
        found=0
        if (sel == 1):
            firstgerbers[index]['values'] = filelist_with_null
        else:
            secondgerbers[index]['values'] = filelist_with_null
        #print(index, "filetype", value)
        for filter in value[1]:
            #print("filter", filter)
            for f in list(temp_filelist):
                #print("file:", f)
                if ( fnmatch.fnmatch(f, filter ) and not fnmatch.fnmatch(f, value[2] ) ):
                    #print("Match!", f, filter)
                    if (sel==1):
                        firstgerbers[index].set(f)
                    else:
                        secondgerbers[index].set(f)
                    # Remove file from temporary filelist so it won't be found again on other layers.
                    temp_filelist.remove(f)
                    found=1
                    break
            if (found == 1):
                break


def open_gerber_files(sel):
    print("PCB Color Template Name:", pcb_color_template[gerber_color_combobox.current()][0])
    print("PCB Background Color:", pcb_color_template[gerber_color_combobox.current()][1])

    if(not gerbv_path["text"]):
        messagebox.showwarning("No GerbV", f"You must first select a GerbV binary.")

    process_args = [gerbv_path["text"], "--background="+pcb_color_template[gerber_color_combobox.current()][1]]

    for layer in pcb_color_template[gerber_color_combobox.current()][2]:
        if (sel==1):
            filename = firstgerbers[layer[1]].get()
            path = gerber1_path
        else:
            filename = secondgerbers[layer[1]].get()
            path = gerber2_path
        if (filename != "---"):
            filepath = os.path.join(path, filename).replace("/", os.sep)
            color = layer[0]
            process_args.append(filepath)
            process_args.append("--foreground="+color)

    print("Starting GerbV with these args:", process_args)
    subprocess.Popen(process_args, stdin=None, stdout=None, stderr=None)


# Create buttons to open gerbers and labels showing the location
open_gerber1 = Button(second_frame, text='Open Gerber in GerbV', command=lambda: open_gerber_files(1))
open_gerber1.grid(column=2, row=row, sticky=W, padx=10)
open_gerber2 = Button(second_frame, text='Open Gerber in GerbV', command=lambda: open_gerber_files(2))
open_gerber2.grid(column=3, row=row, sticky=W, padx=10)
row = row + 1

second_frame.grid_rowconfigure(row, minsize=20)
row = row + 1

select_gerber1 = Button(second_frame, text='Select Gerber 1', command=lambda: select_gerber_file(1))
select_gerber1.grid(column=1, row=row, sticky=W, padx=10)
gerber1_dir = Label(second_frame, text="")
gerber1_dir.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
row = row + 1
select_gerber2 = Button(second_frame, text='Select Gerber 2', command=lambda: select_gerber_file(2))
select_gerber2.grid(column=1, row=row, sticky=W, padx=10)
gerber2_dir = Label(second_frame, text="")
gerber2_dir.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
row = row + 1


def select_png_export_dir():
    folder_selected = askdirectory(title="Select Directory for png export")
    if folder_selected is not None:
        print("Selected Folder:", folder_selected)
        png_export_dir_label.configure(text=folder_selected)
        settings_paths['png_export_path'] = folder_selected
        write_settings_file()


png_export_dir_btn = Button(second_frame, text='Select export png dir', command=lambda: select_png_export_dir())
png_export_dir_btn.grid(column=1, row=row, sticky=W, padx=10)
png_export_dir_label = Label(second_frame, text="")
png_export_dir_label.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
row = row + 1

def export_layer(layer_index, sel):
    print("Using png color template:", png_color_template[png_color_combobox.current()][0])
    bg_color = png_color_template[png_color_combobox.current()][1]
    if (sel == '1' or sel == '2'):
        if (sel=='1'):
            filename = firstgerbers[layer_index].get()
            path = gerber1_path
            layer_color = png_color_template[png_color_combobox.current()][2]
            outline_filename = firstgerbers[-1].get()  # Get filename of board outline layer
        elif (sel=='2'):
            filename = secondgerbers[layer_index].get()
            path = gerber2_path
            layer_color = png_color_template[png_color_combobox.current()][3]
            outline_filename = secondgerbers[-1].get()  # Get filename of board outline layer
        filepath = os.path.join(path, filename).replace("/", os.sep)
        outline_filepath = os.path.join(path, outline_filename).replace("/", os.sep)
        process_args = [gerbv_path["text"], "-a", "--background="+bg_color, "--foreground="+layer_color, "--foreground="+layer_color]
        process_args.append(filepath)
        process_args.append(outline_filepath)
    if (sel == 'combined'):
        filename1 = firstgerbers[layer_index].get()
        path1 = gerber1_path
        layer_color1 = png_color_template[png_color_combobox.current()][4]
        outline1_filename = firstgerbers[-1].get()  # Get filename of board outline layer

        filename2 = secondgerbers[layer_index].get()
        path2 = gerber2_path
        layer_color2 = png_color_template[png_color_combobox.current()][5]
        outline2_filename = secondgerbers[-1].get()  # Get filename of board outline layer

        filepath1 = os.path.join(path1, filename1).replace("/", os.sep)
        filepath2 = os.path.join(path2, filename2).replace("/", os.sep)
        outline_filepath1 = os.path.join(path1, outline1_filename).replace("/", os.sep)
        outline_filepath2 = os.path.join(path2, outline2_filename).replace("/", os.sep)
        process_args = [gerbv_path["text"], "-a", "--background="+bg_color, "--foreground="+layer_color1, "--foreground="+layer_color2, "--foreground="+layer_color1, "--foreground="+layer_color2]
        process_args.append(filepath1)
        process_args.append(filepath2)
        process_args.append(outline_filepath1)
        process_args.append(outline_filepath2)

    process_args.append("--export=png")
    process_args.append("--dpi="+png_dpi_entry.get())

    export_filename = filetypes[layer_index][0].replace(" ", "_") + "-" + sel + ".png"
    export_path = png_export_dir_label["text"]
    export_filepath = os.path.join(export_path, export_filename).replace("/", os.sep)
    process_args.append("-o" + export_filepath)

    print("Starting GerbV with these args:", process_args)
    returncode = subprocess.call(process_args, stdin=None, stdout=None, stderr=None)
    print("GerbV process exited with code:", returncode)

def export_png():
    # Save dpi setting
    settings_other['png_export_dpi'] = png_dpi_entry.get()
    write_settings_file()

    export_result = "Png Export Result:\r\n"
    for index, layer in enumerate(filetypes):
        export_result = export_result + layer[0] + ": "
        if (firstgerbers[index].get() == "---" or secondgerbers[index].get() == "---"):
            export_result = export_result + "Not available in both Gerbers.\r\n"
        else:
            export_png_status.configure(text="Exporting "+layer[0]+" Gerber 1")
            root.update()  # For the GUI to update
            export_layer(index, '1')
            export_png_status.configure(text="Exporting "+layer[0]+" Gerber 2")
            root.update()  # For the GUI to update
            export_layer(index, '2')
            export_png_status.configure(text="Exporting "+layer[0]+" Combined Gerber 1&2")
            root.update()  # For the GUI to update
            export_layer(index, 'combined')
            export_png_status.configure(text="Finding differences in "+layer[0])
            root.update()  # For the GUI to update

            img_path = png_export_dir_label["text"]
            img1_filename = layer[0].replace(" ", "_") + "-1.png"
            img2_filename = layer[0].replace(" ", "_") + "-2.png"
            img3_filename = layer[0].replace(" ", "_") + "-combined.png"
            img1 = os.path.join(img_path, img1_filename).replace("/", os.sep)
            img2 = os.path.join(img_path, img2_filename).replace("/", os.sep)
            img3 = os.path.join(img_path, img3_filename).replace("/", os.sep)

            # The code for finding the differences in the images is "borrowed" from Alison Américo:
            # https://github.com/alisonamerico/image-difference
            from skimage.metrics import structural_similarity  # scikit-image
            import imutils
            import cv2  # opencv-python

            # load the two input images
            imageA = cv2.imread(img1)
            imageB = cv2.imread(img2)
            imageC = cv2.imread(img3)

            h1, w1, c1 = imageA.shape
            print("Resolution of", img1, "is", w1, "x", h1)

            h2, w2, c2 = imageB.shape
            print("Resolution of", img2, "is", w2, "x", h2)

            # convert the images to grayscale
            grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
            grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)

            if (h1 == h2 and w1 == w2):
                try:
                    # compute the Structural Similarity Index (SSIM) between the two
                    # images, ensuring that the difference image is returned
                    (score, diff) = structural_similarity(grayA, grayB, full=True)
                    diff = (diff * 255).astype("uint8")
                    print("SSIM: {}".format(score))

                    # threshold the difference image, followed by finding contours to
                    # obtain the regions of the two input images that differ
                    thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
                    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cnts = imutils.grab_contours(cnts)

                    # loop over the contours
                    for c in cnts:
                        # compute the bounding box of the contour and then draw the
                        # bounding box on both input images to represent where the two
                        # images differ
                        (x, y, w, h) = cv2.boundingRect(c)
                        cv2.rectangle(imageA, (x, y), (x + w, y + h), (0, 0, 255), 2, cv2.LINE_AA)
                        cv2.rectangle(imageB, (x, y), (x + w, y + h), (0, 0, 255), 2, cv2.LINE_AA)
                        cv2.rectangle(imageC, (x, y), (x + w, y + h), (0, 0, 255), 2, cv2.LINE_AA)

                    cv2.imwrite(img1, imageA)
                    cv2.imwrite(img2, imageB)
                    cv2.imwrite(img3, imageC)

                    export_result = export_result + "OK. Images are "+format(round(score*100,2))+"% equal.\r\n"
                except Exception as e:
                    print("Unable to compare", img1, "and", img2, "Error:", e)
                    export_result = export_result+"Failed to compare images. Error: "+str(e)+"\r\n"
            else:
                print("Images does not have the same resolution. Not able to compare", img1, "and", img2)
                export_result = export_result+"Image 1 and 2 has different resolutions.\r\n"
    messagebox.showwarning("Info", export_result)
    export_png_status.configure(text="")

second_frame.grid_rowconfigure(row, minsize=15)
row = row + 1

export_png_btn = Button(second_frame, text='Export png', command=lambda: export_png())
export_png_btn.grid(column=1, row=row, sticky=W, padx=10)
export_png_status = Label(second_frame, text="")
export_png_status.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
row = row + 1

# Add headline
second_frame.grid_rowconfigure(row, minsize=15)
row = row + 1
headline_templates = Label(second_frame, text="Color templates", font='bold')
headline_templates.grid(column=1, row=row, sticky=W, padx=10)
row = row + 1

def combo_changed(*args):
    print("png_color_combobox", png_color_combobox.current())
    print("gerber_color_combobox", gerber_color_combobox.current())
    settings_templates['diff_color_combobox'] = str(diff_color_combobox.current())
    settings_templates['png_color_combobox'] = str(png_color_combobox.current())
    settings_templates['gerber_color_combobox'] = str(gerber_color_combobox.current())
    write_settings_file()

diff_color_template = []
for template in diff_gerbv_args:
    diff_color_template.append(template[0])

diff_color_label = Label(second_frame, text="GerbV Diff")
diff_color_label.grid(column=1, row=row, sticky=W, padx=10)
diff_color_combobox = Combobox(second_frame, width=50, values=diff_color_template)
diff_color_combobox.bind("<<ComboboxSelected>>",combo_changed)
diff_color_combobox.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
diff_color_combobox.current(settings_templates['diff_color_combobox'])
row = row + 1

gerber_color_template = []
for template in pcb_color_template:
    gerber_color_template.append(template[0])

gerber_color_label = Label(second_frame, text="GerbV View Gerber")
gerber_color_label.grid(column=1, row=row, sticky=W, padx=10)
gerber_color_combobox = Combobox(second_frame, width=50, values=gerber_color_template)
gerber_color_combobox.bind("<<ComboboxSelected>>",combo_changed)
gerber_color_combobox.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
gerber_color_combobox.current(settings_templates['gerber_color_combobox'])
row = row + 1

png_template_names = []
for template in png_color_template:
    png_template_names.append(template[0])

png_color_label = Label(second_frame, text="Png Export")
png_color_label.grid(column=1, row=row, sticky=W, padx=10)
png_color_combobox = Combobox(second_frame, width=50, values=png_template_names)
png_color_combobox.bind("<<ComboboxSelected>>",combo_changed)
png_color_combobox.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
png_color_combobox.current(settings_templates['png_color_combobox'])
row = row + 1


def select_gerbv():
    gerbv_file = askopenfilename(title="Select GerbV Executable", filetypes=[('GerbV executable', 'GerbV*.exe')])
    if gerbv_file is not None:
        print("Selected GerbV:", gerbv_file)
        gerbv_path.configure(text=gerbv_file)
        settings_paths['gerbv_path'] = gerbv_file
        write_settings_file()

# Add headline
second_frame.grid_rowconfigure(row, minsize=15)
row = row + 1
headline_templates = Label(second_frame, text="Settings", font='bold')
headline_templates.grid(column=1, row=row, sticky=W, padx=10)
row = row + 1

gerbv_path_btn = Button(second_frame, text='Select Gerbv', command=lambda: select_gerbv())
gerbv_path_btn.grid(column=1, row=row, sticky=W, padx=10)
gerbv_path = Label(second_frame, text="")
gerbv_path.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
row = row + 1

png_dpi_label = Label(second_frame, text="Export png DPI")
png_dpi_label.grid(column=1, row=row, sticky=W, padx=10)
png_dpi_entry = Entry(second_frame, width=50, textvariable=dpi_entry_variable)
png_dpi_entry.grid(column=2, row=row, columnspan=3, sticky=W, padx=10)
row = row + 1

# Get settings.
gerbv_path.configure(text=settings_paths['gerbv_path'])
dpi_entry_variable.set(settings_other['png_export_dpi'])
png_export_dir_label.configure(text=settings_paths['png_export_path'])

if (gerber1_arg == ''):
    file1_path_settings = settings_paths['grb_file1']
    if (file1_path_settings != ''):
        if ( os.path.isfile(file1_path_settings) or os.path.isdir(file1_path_settings) ):
            open_gerber_file(file1_path_settings, 1)
else:
    open_gerber_file(gerber1_arg, 1)

if (gerber2_arg == ''):
    file2_path_settings = settings_paths['grb_file2']
    if (file2_path_settings != ''):
        if ( os.path.isfile(file2_path_settings) or os.path.isdir(file2_path_settings) ):
            open_gerber_file(file2_path_settings, 2)
else:
    open_gerber_file(gerber2_arg, 2)

root.mainloop()