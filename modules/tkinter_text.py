import signal
import sys
import textwrap
import tkinter as tk
from os import getenv

from dotenv import load_dotenv

load_dotenv()
WIDTH_RATIO = 0.5
HEIGHT_RATIO = 0.2
OFFSET_X_RATIO = round((1 - WIDTH_RATIO) / 2, 2)
OFFSET_Y_RATIO = 0.6
SUBTITLE_FONT = str(getenv("SUBTITLE_FONT"))
SUBTITLE_FONT_SIZE = int(getenv("SUBTITLE_FONT_SIZE"))
SUBTITLE_COLOR = getenv("SUBTITLE_COLOR")
SUBTITLE_BG_COLOR = getenv("SUBTITLE_BG_COLOR")
SACRIFICIAL_COLOR = getenv("SACRIFICIAL_COLOR")
WRAP_SIZE = 110 / (SUBTITLE_FONT_SIZE * 0.1)


def subtitle_updater(root: tk.Tk, queue, labels: list[tk.Label]):
    # Check if there is something new in the queue to display.
    while not queue.empty():
        # destroy old label since new message inbound
        old_label = labels.pop(0)
        # old_label.destroy()
        if root.wm_state() == "withdrawn":
            # show root window
            None
            # root.deiconify()

        # create subtitle based on message in queue
        msg_data = queue.get()
        origin = msg_data["origin"]
        orig_text = textwrap.fill(str(origin), WRAP_SIZE)
        display_text = f"{orig_text}"

        translation = msg_data["translation_format"]
        if translation != "":
            trans_text = textwrap.fill(str(translation), WRAP_SIZE)
            display_text = f"{orig_text}\n{trans_text}"

        new_label = tk.Label(
            text=display_text,
            # font=("Comic Sans MS", SUBTITLE_FONT_SIZE, "bold"),
            font=(SUBTITLE_FONT, SUBTITLE_FONT_SIZE),
            fg=SUBTITLE_COLOR,
            bg=SUBTITLE_BG_COLOR,
            justify=tk.LEFT,
            anchor=tk.W,
            padx=10,
        )
        # hide root and destroy label after 5s
        label_time_ms = 5 * 1000
        old_label.after(label_time_ms, old_label.destroy)
        new_label.after(label_time_ms, new_label.destroy)
        # new_label.after(label_time, root.withdraw)

        # place subtitle at top middle of screen
        new_label.pack(side="top", anchor="n", fill=tk.X)
        labels.append(new_label)
        root.update_idletasks()

    run_interval = 100  # run every 0.1s
    root.after(run_interval, lambda: subtitle_updater(root, queue, labels))


x, y = 0, 0


def setup_overlay():
    # set tkinter gui to be topmost without window
    root = tk.Tk()
    root.overrideredirect(True)
    WIDTH = round(root.winfo_screenwidth() * WIDTH_RATIO)
    HEIGHT = round(root.winfo_screenheight() * HEIGHT_RATIO)
    OFFSET_X = round(root.winfo_screenwidth() * OFFSET_X_RATIO)
    OFFSET_Y = round(root.winfo_screenheight() * OFFSET_Y_RATIO)
    root.geometry(f"{WIDTH}x{HEIGHT}+{OFFSET_X}+{OFFSET_Y}")

    def move(event):
        global x, y
        deltax = event.x - x
        deltay = event.y - y
        new_x = root.winfo_x() + deltax
        new_y = root.winfo_y() + deltay
        root.geometry(f"+{new_x}+{new_y}")

    def start_move(event):
        global x, y
        x = event.x
        y = event.y

    root.bind("<ButtonPress-1>", start_move)
    root.bind("<B1-Motion>", move)
    root.lift()
    root.wm_attributes("-topmost", True)
    root.wm_attributes("-alpha", 0.7)

    # root.wm_attributes("-disabled", True) # disable the window, can not move window

    # Sacrifice random color for transparency
    # root.wm_attributes("-transparentcolor", SACRIFICIAL_COLOR)
    root.config(bg=SACRIFICIAL_COLOR)

    # root.config(bg="black")

    # hide initial window
    # root.withdraw()
    # root.deiconify()
    # root.iconify()

    return root


def close_app(*_):
    print("Closing subtitler.")
    sys.exit(0)


def start_app(subtitle_queue):
    print("Start showing subtitles...")
    # catch keyboard interrupt to stop main thread
    signal.signal(signal.SIGINT, close_app)

    overlay = setup_overlay()
    subtitles = [tk.Label()]
    # subtitle_queue = Queue()

    # thread to listen and translate audio
    # threading.Thread(target=translate_audio, args=[subtitle_queue], daemon=True).start()

    # updates subtitles every 0.5s by checking queue
    subtitle_updater(overlay, subtitle_queue, subtitles)

    # set full-screen applications to borderless window for subtitles to appear over it
    overlay.mainloop()


if __name__ == "__main__":
    start_app()
