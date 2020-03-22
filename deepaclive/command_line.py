import sklearn # to load libgomp early to solve problems with static TLS on some systems like bioconda mulled-tests
from deepaclive.receiver import Receiver
from deepaclive.sender import Sender
from deepaclive.refilter import Refilterer
import argparse
from deepaclive import __version__
from multiprocessing import Process


def main():
    parse()


def run_sender(args):
    sender = Sender(read_length=args.read_length, input_dir=args.in_dir, output_dir=args.send_out_dir,
                    user_hostname=args.remote, key=args.key, port=args.port,
                    n_cpus=args.n_cpus_send, do_all=args.all, do_mapped=args.mapped)
    barcodes = args.barcodes.split(',')
    cycles = [int(c) for c in args.cycle_list.split(',')]
    sender.run(cycles=cycles, barcodes=barcodes, mode=args.format)


def run_receiver(args):
    if args.custom:
        args.command = None
    receiver = Receiver(args.command, model=args.model, read_length=args.read_length, input_dir=args.rec_in_dir,
                        output_dir=args.rec_out_dir, n_cpus=args.n_cpus_rec, n_gpus=args.n_gpus,
                        threshold=args.threshold)
    cycles = [int(c) for c in args.cycle_list.split(',')]
    barcodes = args.barcodes.split(',')
    receiver.run(cycles=cycles, barcodes=barcodes, mode=args.format, discard_neg=args.discard_neg)


def run_refilter(args):
    preds_input_dirs = args.preds_in_dir.split(',')
    refilterer = Refilterer(read_length=args.read_length, input_fasta_dir=args.fasta_in_dir,
                            input_npy_dirs=preds_input_dirs, output_dir=args.ref_out_dir)
    cycles = [int(c) for c in args.cycle_list.split(',')]
    barcodes = args.barcodes.split(',')
    refilterer.run(cycles=cycles, barcodes=barcodes, discard_neg=args.discard_neg)


def run_local(args):
    pr = Process(target=run_receiver, args=(args,))
    pr.start()
    ps = Process(target=run_sender, args=(args,))
    ps.start()
    pr.join()
    ps.join()


def add_base_parser(bparser):
    bparser.add_argument('-l', '--read-length', dest='read_length', type=int, required=True,
                         help='Expected read length')
    bparser.add_argument('-s', '--seq-cycles', dest='cycle_list', required=True,
                         help='Comma-separated list of sequencing cycles to analyze.')
    bparser.add_argument('-f', '--format', default="bam",
                         help='Format of temp files. bam or fasta.')
    bparser.add_argument('-B', '--barcodes', default="undetermined",
                         help='Comma-separated list of barcodes of samples to analyze. Default: "undetermined"')

    return bparser


def add_receiver_parser(rparser):
    command_group = rparser.add_mutually_exclusive_group(required=True)
    command_group.add_argument('-c', '--command', default='deepac', help='DeePaC command to use '
                                                                         '(switches builtin models).')
    command_group.add_argument('-C', '--custom', action='store_true', help='Use a custom model.')
    rparser.add_argument('-m', '--model', default='rapid',  help='Model to use. "rapid", "sensitive" '
                                                                 'or custom .h5 file.')
    rparser.add_argument('-t', '--threshold', dest='threshold', type=float, default=0.5,
                         help='Classification threshold.')
    rparser.add_argument('-I', '--receiver-input', dest='rec_in_dir', required=True, help="Receiver input directory.")
    rparser.add_argument('-O', '--receiver-output', dest='rec_out_dir', required=True,
                         help="Receiver output directory.")
    rparser.add_argument('-N', '--n-cpus-rec', dest='n_cpus_rec', type=int, default=8,
                         help='Number of cores used by the receiver.')
    rparser.add_argument('-g', '--n-gpus', dest='n_gpus', type=int, default=0,
                         help='Number of GPUs used by the receiver.')
    rparser.add_argument('-d', '--discard-neg', dest='discard_neg', action='store_true',
                         help="Don't save predictions for nonpathogenic reads.")

    return rparser


def add_sender_parser(sparser):
    sparser.add_argument('-i', '--sender-input', dest='in_dir', required=True, help='Sender input directory.')
    sparser.add_argument('-o', '--sender-output', dest='send_out_dir', required=True, help='Sender output directory.')
    sparser.add_argument('-n', '--n-cpus-send', dest='n_cpus_send', type=int, default=8,
                         help='Number of cores used by the sender.')
    mapped_group = sparser.add_mutually_exclusive_group()
    mapped_group.add_argument('-A', '--all', action='store_true', help="Analyze all reads (default: unmapped only).")
    mapped_group.add_argument('-M', '--mapped', action='store_true', help="Analyze only MAPPED reads "
                                                                          "(default: unmapped only).")
    sparser.add_argument('-r', '--remote', help='Remote host and path (with username).')
    sparser.add_argument('-k', '--key', help='SSH key.')
    sparser.add_argument('-p', '--port', default=22, help='Port for SFTP connection.')
    return sparser


def add_refilter_parser(rparser):
    rparser.add_argument('-t', '--threshold', dest='threshold', type=float, default=0.5,
                         help='Classification threshold.')
    rparser.add_argument('-i', '--fasta-input', dest='fasta_in_dir', required=True, help="Receiver input directory.")
    rparser.add_argument('-I', '--preds-input', dest='preds_in_dir', required=True,
                         help="Comma-separated list of receiver output directories.")
    rparser.add_argument('-O', '--refilter-output', dest='ref_out_dir', required=True,
                         help="Refilter output directory.")
    rparser.add_argument('-d', '--discard-neg', dest='discard_neg', action='store_true',
                         help="Don't save predictions for nonpathogenic reads.")
    return rparser


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

    parser_refilter = subparsers.add_parser('refilter', help='Refilter data with ensembles or alternative thresholds.')
    parser_refilter = add_base_parser(parser_refilter)
    parser_refilter = add_refilter_parser(parser_refilter)
    parser_refilter.set_defaults(func=run_refilter)

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
