import matplotlib.pyplot as plt
from matplotlib.image import AxesImage
from matplotlib.axes import Axes


def update_cbar(im: AxesImage):
    im_data = im.get_array()
    data_min = im_data.min()
    data_max = im_data.max()

    if data_min >= 0:
        cmin = 0
        cmax = data_max
        cmap = "inferno"
    elif data_max <= 0:
        cmin = data_min
        cmax = 0
        cmap = "inferno_r"
    else:
        cmax = max(abs(im_data.max()), abs(im_data.min()))
        cmin = -cmax
        cmap = "RdBu_r"

    im.set_clim(cmin, cmax)
    im.set_cmap(plt.get_cmap(cmap))


def update_title(ax: Axes, var: str, time: float):
    ax.set_title(f"{var} (t={time:.2f})")
