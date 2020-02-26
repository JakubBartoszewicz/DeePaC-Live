import sklearn # to load libgomp early to solve problems with static TLS on some systems like bioconda mulled-tests
from deepaclive.receiver import Receiver
from deepaclive.sender import Sender
import argparse
from deepaclive import __version__


def main():
    # TODO: asynch
    parse()


def run_sender(args):
    sender = Sender(read_length=args.read_length, input_dir=args.in_dir, output_dir=args.send_out_dir)
    cycles = [int(c) for c in args.cycle_list.split(',')]
    sender.run(cycles)


def run_receiver(args):
    receiver = Receiver(args.command, model=args.model, read_length=args.read_length, input_dir=args.rec_in_dir,
                        output_dir=args.rec_out_dir)
    cycles = [int(c) for c in args.cycle_list.split(',')]
    receiver.run(cycles)


def run_local(args):
    run_sender(args)
    run_receiver(args)


def add_base_parser(bparser):
    bparser.add_argument('-l', '--read-length', dest='read_length', type=int, required=True,
                         help='Expected read length')

    bparser.add_argument('-s', '--seq-cycles', dest='cycle_list', required=True,
                         help='Comma-separated list of sequencing cycles to analyze.')
    return bparser


def add_receiver_parser(rparser):
    command_group = rparser.add_mutually_exclusive_group()
    command_group.add_argument('-c', '--command', default='deepac', help='DeePaC command to use '
                                                                         '(switches builtin models).')
    command_group.add_argument('-C', '--custom', action='store_true', help='Use a custom model.')
    rparser.add_argument('-m', '--model', default='rapid',  help='Model to use. "rapid", "sensitive" '
                                                                 'or custom .h5 file.')

    rparser.add_argument('-I', '--receiver-input', dest='rec_in_dir', required=True)
    rparser.add_argument('-O', '--receiver-output', dest='rec_out_dir', required=True)
    return rparser


def add_sender_parser(sparser):
    sparser.add_argument('-i', '--sender-input', dest='in_dir', required=True)
    sparser.add_argument('-o', '--sender-output', dest='send_out_dir', required=True)
    return sparser


def parse():
    """Parse DeePaC-live CLI arguments."""
    parser = argparse.ArgumentParser(prog='deepac-live', description="Running DeePaC in real time.")
    parser.add_argument('-v', '--version', dest='version', action='store_true', help='Print version.')

    subparsers = parser.add_subparsers(help='DeePaC-live subcommands. See command --help for details.',
                                       dest='subparser')
    parser_sender = subparsers.add_parser('sender', help='Prepare and send data.')
    parser_sender = add_base_parser(parser_sender)
    parser_sender = add_sender_parser(parser_sender)
    parser_sender.set_defaults(func=run_sender)

    parser_receiver = subparsers.add_parser('receiver', help='Receive and analyze data.')
    parser_receiver = add_base_parser(parser_receiver)
    parser_receiver = add_receiver_parser(parser_receiver)
    parser_receiver.set_defaults(func=run_receiver)

    parser_local = subparsers.add_parser('local', help='Process data locally.')
    parser_local = add_base_parser(parser_local)
    parser_local = add_receiver_parser(parser_local)
    parser_local = add_sender_parser(parser_local)
    parser_local.set_defaults(func=run_local)

    args = parser.parse_args()

    if args.version:
        print(__version__)
    elif hasattr(args, 'func'):
        args.func(args)
    else:
        print(__version__)
        parser.print_help()


if __name__ == "__main__":
    main()
