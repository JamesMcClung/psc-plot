from lib import parsing

args = parsing.get_parsed_args()

fig = args.handle()

if args.show:
    fig.show()
if args.save:
    fig.save(args.save_name)
