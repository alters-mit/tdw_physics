import numpy as np
import h5py
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def get_frame(f, idx, imkey='_img', N=1000):
    fkeys = sorted([k for k in f['frames'].keys()])
    img = f['frames'][fkeys[idx % N]]['images']
    return np.array(Image.open(io.BytesIO(img[imkey][:]))), len(fkeys)

def animate_movie(f):
    idx = 0
    fig, axes = plt.subplots(figsize=(4,4))
    im, num_frames = get_frame(f, idx)
    plot = plt.imshow(im, origin='upper')

    def animate(*args):
        global idx

        fr, N = get_frame(f, idx)
        plot.set_array(fr)
        idx += 1
        idx %= N

        return plot,

    ani = animation.FuncAnimation(fig, animate, interval=20)
    plt.show()
