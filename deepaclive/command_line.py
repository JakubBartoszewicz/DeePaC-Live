import sklearn # to load libgomp early to solve problems with static TLS on some systems like bioconda mulled-tests
from deepaclive.receiver import Receiver
from deepaclive.sender import Sender


def main():
    cycles = [50, 100, 158, 208]
    read_length = 100
    in_dir = "out"
    mid_dir = "dlmid"
    out_dir = "dlout"
    # TODO: asynch
    run_local("deepacvir", "rapid", read_length, in_dir, mid_dir, out_dir, cycles)


def run_sender(read_length, in_dir, out_dir, cycles):
    sender = Sender(read_length=read_length, input_dir=in_dir, output_dir=out_dir)
    sender.run(cycles)


def run_receiver(deepac_command, model, read_length, in_dir, out_dir, cycles):
    receiver = Receiver(deepac_command, model=model, read_length=read_length, input_dir=in_dir, output_dir=out_dir)
    receiver.run(cycles)


def run_local(deepac_command, model, read_length, in_dir, mid_dir, out_dir, cycles):
    run_sender(read_length, in_dir, mid_dir, cycles)
    run_receiver(deepac_command, model, read_length, mid_dir, out_dir, cycles)


if __name__ == "__main__":
    main()
