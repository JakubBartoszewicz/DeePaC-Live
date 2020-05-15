import sklearn # to load libgomp early to solve problems with static TLS on some systems like bioconda mulled-tests
from deepaclive.receiver import Receiver
from deepaclive.sender import Sender
from deepaclive.refilter import Refilterer
from deepaclive.tests import run_tests
import argparse
from deepaclive import __version__
from multiprocessing import Process
from deepac.command_line import add_global_parser, global_setup
from deepac.utils import config_cpus, config_gpus
import numpy as np
import random as rn


def main():
    seed = 0
    np.random.seed(seed)
    rn.seed(seed)
    parse()


def run_tester(args):
    tpu_resolver = global_setup(args)
    if args.tpu is None:
        n_cpus = config_cpus(args.n_cpus_rec)
        config_gpus(args.gpus)
    else:
        n_cpus = args.n_cpus_rec
    if args.custom:
        args.command = None
    run_tests(args.command, args.model, n_cpus, args.keep, args.scale, tpu_resolver)


def run_sender(args):
    sender = Sender(read_length=args.read_length, input_dir=args.in_dir, output_dir=args.send_out_dir,
                    user_hostname=args.remote, key=args.key, port=args.port,
                    n_cpus=args.n_cpus_send, do_all=args.all, do_mapped=args.mapped)
    barcodes = args.barcodes.split(',')
    cycles = [int(c) for c in args.cycle_list.split(',')]
    sender.run(cycles=cycles, barcodes=barcodes, mode=args.format)


def run_receiver(args):
    tpu_resolver = global_setup(args)
    if args.tpu is None:
        n_cpus = config_cpus(args.n_cpus_rec)
        config_gpus(args.gpus)
    else:
        n_cpus = args.n_cpus_rec
    if args.custom:
        args.command = None
    receiver = Receiver(args.command, model=args.model, read_length=args.read_length, input_dir=args.rec_in_dir,
                        output_dir=args.rec_out_dir, n_cpus=n_cpus, threshold=args.threshold,
                        tpu_resolver=tpu_resolver)
    cycles = [int(c) for c in args.cycle_list.split(',')]
    barcodes = args.barcodes.split(',')
    receiver.run(cycles=cycles, barcodes=barcodes, mode=args.format, discard_neg=args.discard_neg)


def run_refilter(args):
    preds_input_dirs = args.preds_in_dir.split(',')
    refilterer = Refilterer(read_length=args.read_length, input_fasta_dir=args.fasta_in_dir,
                            input_npy_dirs=preds_input_dirs, output_dir=args.ref_out_dir,
                            threshold=args.threshold)
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
    tparser = add_tester_parser(rparser)
    tparser.add_argument('-t', '--threshold', dest='threshold', type=float, default=0.5,
                         help='Classification threshold.')
    tparser.add_argument('-I', '--receiver-input', dest='rec_in_dir', required=True, help="Receiver input directory.")
    tparser.add_argument('-O', '--receiver-output', dest='rec_out_dir', required=True,
                         help="Receiver output directory.")
    tparser.add_argument('-d', '--discard-neg', dest='discard_neg', action='store_true',
                         help="Don't save predictions for nonpathogenic reads.")

    return tparser


def add_tester_parser(tparser):
    command_group = tparser.add_mutually_exclusive_group()
    command_group.add_argument('-c', '--command', default='deepac', help='DeePaC command to use '
                                                                         '(switches builtin models).')
    command_group.add_argument('-C', '--custom', action='store_true', help='Use a custom model.')
    tparser.add_argument('-m', '--model', default='rapid',  help='Model to use. "rapid", "sensitive" '
                                                                 'or custom .h5 file.')
    tparser.add_argument('-N', '--n-cpus-rec', dest='n_cpus_rec', type=int,
                         help='Number of cores used by the receiver. Default: all')
    tparser.add_argument('-g', '--gpus', dest="gpus", nargs='+', type=int,
                         help="GPU devices to use (comma-separated). Default: all")
    return tparser


def add_sender_parser(sparser):
    sparser.add_argument('-i', '--sender-input', dest='in_dir', required=True, help='Sender input directory.')
    sparser.add_argument('-o', '--sender-output', dest='send_out_dir', required=True, help='Sender output directory.')
    sparser.add_argument('-n', '--n-cpus-send', dest='n_cpus_send', type=int,
                         help='Number of cores used by the sender. Default: all.')
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
    parser = add_global_parser(parser)

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

    parser_test = subparsers.add_parser('test', help='Test locally.')
    parser_test = add_tester_parser(parser_test)
    parser_test.add_argument('-k', '--keep', help="Don't delete previous test output.",
                             default=False, action="store_true")
    parser_test.add_argument('-s', '--scale', help="Generate s*1024 reads for testing (Default: s=1).",
                             default=1, type=int)
    parser_test.set_defaults(func=run_tester)

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
