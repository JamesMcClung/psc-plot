from lib import file_util
from lib.animation import BpAnimation


bp_name = "pfd_moments"
steps = file_util.get_available_steps(bp_name, "bp")
var = "rho_e"

anim = BpAnimation(steps, bp_name, var)
anim.show()
