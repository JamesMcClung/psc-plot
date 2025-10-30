from lib import parsing

args = parsing.get_parsed_args()

anim = args.get_animation()

if args.show:
    anim.show()
if args.save:
    anim.save()
