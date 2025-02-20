from lib import h5_util
from lib.animation import H5Animation


h5_name = "prt"
steps = h5_util.get_available_steps_h5(h5_name)

anim = H5Animation(steps, h5_name)
anim.show()
