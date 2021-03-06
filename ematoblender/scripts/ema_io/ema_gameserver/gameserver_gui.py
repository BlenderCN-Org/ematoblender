__author__ = 'Kristy James'
__credits__ = "Alexander Hewer"

import os
import tkinter as tk
import time
from tkinter import ttk
from tkinter import filedialog as fd

from .gameserver import GameServer, MyUDPHandler
from .GameServerSettings import GameServerSettings
from .SettingsReader import SettingsReader
from .SettingsWriter import SettingsWriter
from .OverrideSettings import OverrideSettings
from . import rtclient as rtc
from ...ema_shared import properties as pps


def main(args=None):
    # start the server
    global server
    GameServerSettings.port = pps.gameserver_port
    GameServerSettings.host = pps.gameserver_host

    server = GameServer(serve_in_thread=True)
#    server = GameServer(pps.game_server_cl_args if args is None else args,
#                        serve_in_thread=True)
    print('Server will now serve forever.')

    # start the GUI
    root = tk.Tk()
    root.geometry("900x500")
    root.title("Ematoblender Gameserver {}".format(server.server_address))

    if os.name == 'nt': # windows icon
        icon = os.path.normpath(__file__ + os.sep + '../../../../images/ti.ico')
        root.iconbitmap(icon)
    else:
        try:
            icon = os.path.normpath(__file__ + os.sep + '../../../../images/ti.png')
            root.iconphoto(True, tk.PhotoImage(file=icon))

        except FileNotFoundError:
            pass

        except:
            icon = os.path.normpath(__file__ + os.sep + '../../../../images/ti.xbm')
            root.iconbitmap('@'+icon)

    app = Application(master=root, servobj=server)

    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, app))

    app.mainloop()

    print('Application and server were shutdown.')


def on_closing(r, a):
    a.quit()
    r.destroy()

class Application(tk.Frame):
    """ GUI class for the gameserver application. """
    def __init__(self, master=None, servobj=None):

        OverrideSettings.save()
        tk.Frame.__init__(self, master)
        self.root = master

        self.shownetworking = tk.BooleanVar()
        self.streaming = False
        self.streamtext = tk.StringVar()
        self.streamtext.set("Start streaming")
        self.servobj = servobj

        self.createMenuBar()

        # create frame areas
        self.createTopFrame()
        self.createMiddleFrame()
        self.createStatusLabel()


    def quit(self):
        self.servobj.shutdown_server_threads()
        self.root.destroy()
        #  TODO: are there any other things needed to quit (eg saving?)


    def toggle_networking_display(self):
        self.shownetworking = not self.shownetworking
        if self.shownetworking:
            self.nt_in.pack()
            self.nt_out.pack()
        else:
            self.nt_in.pack_forget()
            self.nt_out.pack_forget()

    def update_disabled_buttons(self):
        for btn in self.manual_buttons:
            btn.configure(state=tk.NORMAL if self.allow_man_calls.get() == 1 else tk.DISABLED)

    def eval_smoothing(self, *args):
        """Convert the output of the smoothing options section into something that can be used in GS."""
        print('Key or button pressed in smoothing frame.')
        GameServerSettings.smoothFrames, GameServerSettings.smoothMs = None, None

        if self.smooth_by.get() == 1: # smooth by ms
            self.msentry.config(state=tk.NORMAL)
            self.frameentry.config(state=tk.DISABLED)
            if self.msentry.get().isnumeric():
                GameServerSettings.smoothFrames = self.servobj.n_frames_smoothed(ms=float(self.msentry.get()))
            else:  # entry is not numeric
                self.msentry.delete(0, tk.END) # delete any non-numeric things
        else: # smooth by frames
            self.msentry.config(state=tk.DISABLED)
            self.frameentry.config(state=tk.NORMAL)
            if self.frameentry.get().isdigit(): # must be an integer
                GameServerSettings.smoothFrames = self.servobj.n_frames_smoothed(frames=int(self.frameentry.get()))
            else:
                self.frameentry.delete(0, tk.END)

    def createMenuBar(self):
        """Create a manubar with pulldown menus"""
        # create a menubar
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)

        # create the filemenu
        filemenu.add_command(label="Open project", command=self.open_project)
        filemenu.add_command(label="Save project", command=self.save_project)
#        filemenu.add_command(label="Clear Cache", command=example_command)
#        filemenu.add_command(label="Pause Sending/Receiving", command=example_command)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        # create the Edit menu
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Show/Hide Networking", command=self.toggle_networking_display)
        editmenu.add_separator()
#        editmenu.add_command(label="User Preferences", command=example_command)
        menubar.add_cascade(label="Edit", menu=editmenu)

        # create the Help menu
        helpmenu = tk.Menu(menubar, tearoff=0)
#        helpmenu.add_command(label="Go to documentation", command=example_command)
#        helpmenu.add_command(label="About", command=example_command)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.root.config(menu=menubar)

    def createTopFrame(self):
        """Put widgets in the top frame"""
        self.topframe = tk.Frame(self.root, relief='raised', bd=2)
        self.topframe.pack(side=tk.TOP, fill=tk.X, expand=False)
        lbl = tk.Label(self.topframe,justify=tk.LEFT,
                       text='''This gameserver is the control centre for the Ematoblender package.
It controls when data is requested from the data server, manipulates these data,
and passes them into Blender (or any other application that requests them).'''
        )
        lbl.pack(side=tk.LEFT)
        frame = tk.Frame(self.topframe)
        frame.pack(side=tk.RIGHT)
        btn = tk.Button(frame, text='Stop Server\nand Quit', fg='red', anchor=tk.E, command=self.quit)
        btn.pack(side=tk.RIGHT)

    def createMiddleFrame(self):
        self.middleframe = tk.Frame(self.root)
        self.middleframe.pack(expand=True, fill=tk.BOTH)
        self.createLeftFrame()
        self.createRightFrame()

    def createLeftFrame(self):
        """Put widgets in the left frame"""
        self.leftframe = tk.Frame(self.middleframe, relief='raised', bd=2)
        self.leftframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lbl = tk.Label(self.leftframe, text='Incoming data:')
        lbl.pack()

        # saving locations
        self.tsvfilelocation = tk.StringVar()
        self.savetsv = tk.BooleanVar()
        self.wavfilelocation = tk.StringVar()
        self.savewav = tk.BooleanVar()

        saveframe = tk.Frame(self.leftframe, relief='groove', bd=2)
        saveframe.pack(fill=tk.X,)

        def set_tsvdir():
            self.tsvfilelocation.set(fd.askdirectory())
            GameServerSettings.receivedDataOutputDir = self.tsvfilelocation.get()

        def set_wavdir():
            self.wavfilelocation.set(fd.askdirectory())
            GameServerSettings.waveDir = self.wavfilelocation.get()

        def set_tsvbtn():
            self.tsvbtn.config(state=tk.ACTIVE if self.savetsv.get() else tk.DISABLED)
            self.tsvlab.config(state=tk.ACTIVE if self.savetsv.get() else tk.DISABLED)
            self.servobj.repl.print_tsv = self.savetsv.get()
            GameServerSettings.saveReceivedData = self.savetsv.get()

        def set_wavbtn():
            self.wavbtn.config(state=tk.ACTIVE if self.savewav.get() else tk.DISABLED)
            self.wavlab.config(state=tk.ACTIVE if self.savewav.get() else tk.DISABLED)
            GameServerSettings.outputWave = self.savewav.get()

        tk.Label(saveframe, text="Save received TSV").grid(row=1, column=1, sticky=tk.W)
        btn = tk.Checkbutton(saveframe, variable=self.savetsv, command=set_tsvbtn)
        btn.grid(row=1, column=2)

        self.tsvbtn = tk.Button(saveframe, text="Choose location", command=set_tsvdir, state=tk.DISABLED)
        self.tsvbtn.grid(row=1, column=3)
        self.tsvlab = tk.Label(saveframe, textvariable=self.tsvfilelocation)
        self.tsvlab.grid(row=1,column=4)


        tk.Label(saveframe, text="Record audio while streaming").grid(row=2, column=1, sticky=tk.W)
        btn = tk.Checkbutton(saveframe, variable=self.savewav, command=set_wavbtn)
        btn.grid(row=2, column=2)

        self.wavbtn = tk.Button(saveframe, text="Choose location", command=set_wavdir, state=tk.DISABLED)
        self.wavbtn.grid(row=2, column=3)
        self.wavlab = tk.Label(saveframe, textvariable=self.wavfilelocation)
        self.wavlab.grid(row=2, column=4)

        self.savetsv.set(False)
        self.savewav.set(False)
        GameServerSettings.saveReceivedData, GameServerSettings.outputWave = self.savetsv.get(), self.savewav.get()

        # TODO: Choose which audio input


        # manual server calls
        callsframe = tk.Frame(self.leftframe, relief='groove', bd=2)
        callsframe.pack(fill=tk.X, expand=False)
        self.allow_man_calls = tk.BooleanVar()
        manallow = tk.Checkbutton(callsframe, text="Allow manual calls to the data server",
                                  variable=self.allow_man_calls,
                                  command=self.update_disabled_buttons)
        manallow.grid(row=1, column=1, columnspan=3)

        manbtn1 = tk.Button(callsframe, text='Single', state=tk.DISABLED,
                            command=lambda: rtc.get_one_df(self.servobj.conn, self.servobj.repl))
        manbtn1.grid(row=2, column=1)
        manbtn2 = tk.Button(callsframe, textvariable=self.streamtext, state=tk.DISABLED,
                            command=self.start_stop_streaming)
        manbtn2.grid(row=2, column=2)
        manbtn3 = tk.Button(callsframe, text='Status', state=tk.DISABLED,
                            command=lambda: rtc.test_communication(self.servobj.conn, self.servobj.repl))
        manbtn3.grid(row=2, column=3)
        self.manual_buttons = [manbtn1, manbtn2, manbtn3]

#        self.nt_in = NetworkTrafficFrame(self.leftframe)
#        self.nt_in.pack()

    def createRightFrame(self):
        """Put widgets in the right frame"""
        self.rightframe = tk.Frame(self.middleframe, relief='raised', bd=2)
        self.rightframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lbl = tk.Label(self.rightframe, text='Outgoing data:')
        lbl.pack()

        # options for data smoothing/delay
        smoothframe = tk.Frame(self.rightframe, relief='groove', bd=2)
        smoothframe.pack(fill=tk.X, expand=False)
        lbl = tk.Label(smoothframe, text='Apply rolling average by:') # todo - ensure is really applied
        lbl.grid(row=1, column=1, columnspan=4, sticky=tk.W)
        self.smooth_by = tk.IntVar()
        self.smooth_int = tk.StringVar()
        lbl = tk.Radiobutton(smoothframe, text='ms', variable=self.smooth_by, value=1, command=self.eval_smoothing)
        lbl.grid(row=2, column=1)
        self.msentry = tk.Entry(smoothframe, width=4, state=tk.DISABLED)
        self.msentry.bind("<Key>", self.eval_smoothing)
        self.msentry.grid(row=2, column=2, padx=4)
        lbl = tk.Radiobutton(smoothframe, text='frames', variable=self.smooth_by, value=2, command=self.eval_smoothing)
        lbl.grid(row=2, column=3)
        self.frameentry = tk.Entry(smoothframe, width=4, state=tk.DISABLED)
        self.frameentry.bind("<Key>", self.eval_smoothing)
        self.frameentry.grid(row=2, column=4, padx=4)


        def record_biteplane():
            self.biteplane_live_status.set('Button pressed')

            try:
                secs = int(self.biteplane_secentry.get())
            except ValueError:
                self.biteplane_secentry.text = ''
                self.biteplane_live_status.set('INVALID SECONDS')

            else:
                self.biteplane_live_status.set('RECORDING')

                self.servobj.headcorrection.load_live(self.servobj, seconds=secs)
                
                GameServerSettings.bitePlane["origin"] = tuple(self.servobj.headcorrection.biteplane.origin)
                GameServerSettings.bitePlane["xAxis"] = tuple(self.servobj.headcorrection.biteplane.x_axis)
                GameServerSettings.bitePlane["yAxis"] = tuple(self.servobj.headcorrection.biteplane.y_axis)
                GameServerSettings.bitePlane["zAxis"] = tuple(self.servobj.headcorrection.biteplane.z_axis)

                self.biteplane_live_status.set('COMPLETE')

        bitePlaneFrame = tk.Frame(self.rightframe, relief='groove', bd=2)
        bitePlaneFrame.pack(side=tk.TOP, fill=tk.X, expand=False)
        lbl = tk.Label(bitePlaneFrame, text='Record biteplane:', justify=tk.LEFT)
        lbl.grid(row=1, column=1, columnspan=1, sticky=tk.W)

        btn= tk.Button(bitePlaneFrame, text='Start streaming', command=record_biteplane)
        btn.grid(row=2, column=1, sticky=tk.W)
        lbl = tk.Label(bitePlaneFrame, text='Secs:')
        lbl.grid(row=2, column=2, columnspan=3)

        self.biteplane_secentry = tk.Entry(bitePlaneFrame, width=4)
        self.biteplane_secentry.grid(row=2, column=4)

        self.biteplane_live_status = tk.StringVar()
        self.biteplane_live_status_lbl = tk.Label(bitePlaneFrame, textvariable=self.biteplane_live_status)
        self.biteplane_live_status_lbl.grid(row=3, column=1, columnspan=3)

        def record_refpoint():
            self.ref_live_status.set('RECORDING')
            secs = int(self.ref_secentry.get())
            self.servobj.referencePointBuilder.load_live(self.servobj, seconds=secs)
            GameServerSettings.bitePlane["shiftedOrigin"] = tuple(self.servobj.headcorrection.biteplane.shiftedOrigin)
            self.ref_live_status.set('COMPLETE')

        referenceFrame = tk.Frame(self.rightframe, relief='groove', bd=2)
        referenceFrame.pack(side=tk.TOP, fill=tk.X, expand=False)
        lbl = tk.Label(referenceFrame, text='Record reference point:', justify=tk.LEFT)
        lbl.grid(row=1, column=1, columnspan=1, sticky=tk.W)

        btn= tk.Button(referenceFrame, text='Start streaming', command=record_refpoint)
        btn.grid(row=2, column=1, sticky=tk.W)
        lbl = tk.Label(referenceFrame, text='Secs:')
        lbl.grid(row=2, column=2, columnspan=3)

        self.ref_secentry = tk.Entry(referenceFrame, width=4)
        self.ref_secentry.grid(row=2, column=4)

        self.ref_live_status = tk.StringVar()
        self.ref_live_status_lbl = tk.Label(referenceFrame, textvariable=self.ref_live_status)
        self.ref_live_status_lbl.grid(row=3, column=1, columnspan=3)



#        lbl = tk.Label(corrframe, text='Axis swap options:')
#        lbl.grid(row=4, column=1, columnspan=3, sticky=tk.W)
#        self.reflect_x, self.reflect_y, self.reflect_z = tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar()
#        check = tk.Checkbutton(corrframe, text='X', variable=self.reflect_x)
#        check.grid(row=5, column=1, sticky=tk.W)
#        check = tk.Checkbutton(corrframe, text='Y', variable=self.reflect_y)
#        check.grid(row=6, column=1, sticky=tk.W)
#        check = tk.Checkbutton(corrframe, text='Z', variable=self.reflect_z)
#        check.grid(row=7, column=1, sticky=tk.W)
#
#        lbl = tk.Label(corrframe, text='Axis order options:')
#        lbl.grid(row=4, column=3, columnspan=3, sticky=tk.W)
#        self.axis_order = tk.IntVar()
#        rad = tk.Radiobutton(corrframe, text='XYZ', variable=self.axis_order, value='XYZ')
#        rad.grid(row=5, column=3, sticky=tk.W)
#        rad = tk.Radiobutton(corrframe, text='YXZ', variable=self.axis_order, value='YXZ')
#        rad.grid(row=6, column=3, sticky=tk.W)
#        rad = tk.Radiobutton(corrframe, text='XZY', variable=self.axis_order, value='XZY')
#        rad.grid(row=7, column=3, sticky=tk.W)
#
#        lbl = tk.Label(corrframe, text='Order: Left-right, Back-front, Up-down')
#        lbl.grid(row=9, column=3, columnspan=3, sticky=tk.W)





        # TODO: Choose to perfoorm head correction
        # If yes, choose file with matrices
        # OR choose TSV file with recording
        # OR choose to do some live streaming

        # SHOW orientation


#        self.nt_out = NetworkTrafficFrame(self.rightframe)
#        self.nt_out.pack(expand=False)

    def createStatusLabel(self):
        """Put a label with some configurable text along the bottom"""
        self.bottomframe = tk.Frame(self.root, relief='sunken', bd=3)
        self.bottomframe.pack(side=tk.BOTTOM, fill=tk.X)
        labeltext = self.servobj.last_status
        self.bottomlabel = tk.Label(self.bottomframe, text=labeltext)
        self.bottomlabel.pack(side=tk.RIGHT, fill=tk.X)
        self.bottomlabel.after(10, func=self.updateStatusLabel)

    def updateStatusLabel(self):
        self.bottomlabel.config(text=self.servobj.last_status)
        self.after(10, self.updateStatusLabel)

    def start_stop_streaming(self):
        """Toggle streaming, and text on button"""
        if self.streaming:
            self.servobj.gs_stop_streaming()
            self.streamtext.set("Start streaming")
            self.streaming = False

        else:
            self.servobj.gs_start_streaming()
            self.streamtext.set("Stop streaming")
            self.streaming = True

    def open_project(self):

        options = {}
        options['defaultextension'] = '.json'
        options['filetypes'] = [('JSON files', '.json')]
        fn = fd.askopenfilename(**options)

        if fn != "":

            SettingsReader.read_from(fn)
            if GameServerSettings.useHeadCorrection:
                self.servobj.init_headcorrection()

            self.servobj.externalServer.reset()
            # wait a  little bit for the commands to reach the
            # server
            time.sleep(0.5)
            self.servobj.externalServer.set_settings()

            time.sleep(0.5)
            self.servobj.externalServer.set_model_vertex_indices()

    def save_project(self):

        options = {}
        options['defaultextension'] = '.json'
        options['filetypes'] = [('JSON files', '.json')]
        fn = fd.asksaveasfilename(**options)

        if fn != "":

            SettingsWriter.write_to(fn)


class NetworkTrafficFrame(tk.Frame):
    """Class that makes a frame with two side-by-side scrolling lists,
    Text that shows the content.
    Whole thing can be hidden on checkbox
    """
    def __init__(self, master=None):
        super().__init__(master)
        upperframe = tk.Frame(self)
        upperframe.pack(side=tk.TOP, fill=tk.X)
        leftframe = tk.Frame(upperframe)
        leftframe.pack(side=tk.LEFT)
        self.scrollbarleft = tk.Scrollbar(leftframe, orient='vertical')
        self.listboxleft = tk.Listbox(leftframe, selectmode='single', yscrollcommand=self.scrollbarleft.set)
        self.listboxleft.select_set(0)
        self.scrollbarleft.config(command=self.listboxleft.yview)
        self.scrollbarleft.pack(side='right', fill=tk.BOTH, expand=True)
        self.listboxleft.pack()

        rightframe = tk.Frame(upperframe)
        rightframe.pack(side=tk.LEFT, fill=tk.X)
        self.scrollbarright = tk.Scrollbar(rightframe, orient='vertical')
        self.listboxright = tk.Listbox(rightframe, selectmode='single', yscrollcommand=self.scrollbarright.set)
        self.listboxright.select_set(0)
        self.scrollbarright.config(command=self.listboxright.yview)
        self.scrollbarright.pack(side='right', fill=tk.BOTH, expand=True)
        self.listboxright.pack()

        lowerframe = tk.Frame(self)
        lowerframe.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.cantext = tk.StringVar().set('lblablajn')
        canvas = tk.Text(lowerframe, width=leftframe.winfo_width(), text=self.cantext)
        canvas.pack(side='left', fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    main()
