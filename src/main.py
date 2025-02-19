from lib import xr_util
from lib.animation import BpAnimation


bp_name = "pfd_moments"
steps = xr_util.get_available_steps_bp(bp_name)
var = "rho_e"

anim = BpAnimation(steps, bp_name, var)
anim.show()
