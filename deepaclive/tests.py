from deepac.tests.datagen import generate_read
import os
from deepaclive.receiver import Receiver
from deepaclive.sender import Sender
import pysam


def generate_sample_sams(n, filename_prefix, cycles, barcodes, barcode_len=8,
                         gc_pos=0.7, gc_neg=0.3, length=250):
    """Generate random reads to a fasta file."""

    header = "@HD\tVN:1.6\tSO:unknown\n@SQ\tSN:ref\tLN:1024\n"
    flag_unpaired = 4
    flags_paired = [77, 141]
    n_half = n//2
    reads_pos_1 = [generate_read(gc_pos, length, header) for i in range(0, n_half)]
    reads_neg_1 = [generate_read(gc_neg, length, header) for i in range(0, n-n_half)]
    reads_1 = reads_pos_1 + reads_neg_1
    reads_pos_2 = [generate_read(gc_pos, length, header) for i in range(0, n_half)]
    reads_neg_2 = [generate_read(gc_neg, length, header) for i in range(0, n-n_half)]
    reads_2 = reads_pos_2 + reads_neg_2
    for c in cycles:
        for b in barcodes:
            lines = [header]
            filename_sam = filename_prefix + "{}_{}.sam".format(c, b)
            if c <= length:
                for i in range(len(reads_1)):
                    lines.append("read_{id}\t{flag}\t*\t0\t255\t*\t*\t0\t0\t{read}\t*\n".format(
                        id=i,
                        flag=flag_unpaired,
                        read=reads_1[i].seq[:c]))
            else:
                for i in range(len(reads_1)):
                    lines.append("read_{id}\t{flag}\t*\t0\t255\t*\t*\t0\t0\t{read}\t*\n".format(
                        id=i,
                        flag=flags_paired[0],
                        read=reads_1[i].seq))
                for i in range(len(reads_2)):
                    lines.append("read_{id}\t{flag}\t*\t0\t255\t*\t*\t0\t0\t{read}\t*\n".format(
                        id=i,
                        flag=flags_paired[1],
                        read=reads_1[i].seq[:c-barcode_len]))
            with open(filename_sam, 'a') as f:
                f.writelines(lines)


def generate_sample_bams(n, filename_prefix, cycles, barcodes, barcode_len=8,
                         gc_pos=0.7, gc_neg=0.3, length=250):
    generate_sample_sams(n, filename_prefix, cycles, barcodes, barcode_len, gc_pos, gc_neg, length)

    for c in cycles:
        for b in barcodes:
            filename = filename_prefix + "{}_{}.bam".format(c, b)
            filename_sam = filename_prefix + "{}_{}.sam".format(c, b)
            # create the file upfront, so pysam can open it
            with open(filename, 'w') as fp:
                pass
            pysam.view("-bS", "-o", filename, filename_sam,  save_stdout=filename)


def run_tests(command="deepac", model="rapid", n_cpus=None, keep=False, scale=1, tpu_resolver=None):
    if not keep and os.path.exists("deepac-live-tests"):
        print("Deleting previous test output...")
        for root, dirs, files in os.walk("deepac-live-tests", topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
    if not os.path.exists("deepac-live-tests"):
        os.makedirs("deepac-live-tests")
    if not os.path.exists(os.path.join("deepac-live-tests", "mock_out")):
        os.makedirs(os.path.join("deepac-live-tests", "mock_out"))
    cycles = [50, 100, 150, 200, 250, 308, 358, 408, 458, 508]
    barcodes = ["undetermined"]
    if not keep:
        print("TEST: Generating data...")
        generate_sample_bams(1024*scale, os.path.join("deepac-live-tests", "mock_out", "hilive_out_cycle"), barcode_len=8,
                             cycles=cycles, barcodes=barcodes)

    receiver = Receiver(command, model=model, read_length=250, input_dir=os.path.join("deepac-live-tests", "rec_in"),
                        output_dir=os.path.join("deepac-live-tests", "rec_out"), n_cpus=n_cpus, threshold=0.5,
                        tpu_resolver=tpu_resolver)
    sender = Sender(read_length=250, input_dir=os.path.join("deepac-live-tests", "mock_out"),
                    output_dir=os.path.join("deepac-live-tests", "rec_in"), n_cpus=n_cpus)

    print("TEST: Filtering and sending data...")
    sender.run(cycles=cycles, barcodes=barcodes)
    assert (os.path.isfile(os.path.join("deepac-live-tests", "rec_in",
                                        "hilive_out_cycle50_undetermined_deepac_1.bam"))), \
        "Filtering or sending failed."
    assert (os.path.isfile(os.path.join("deepac-live-tests", "rec_in",
                                        "hilive_out_cycle508_undetermined_deepac_2.bam"))), \
        "Filtering or sending failed."

    print("TEST: Receiving data and running predictions...")
    receiver.run(cycles=cycles, barcodes=barcodes)
    assert (os.path.isfile(os.path.join("deepac-live-tests", "rec_out",
                                        "hilive_out_cycle250_undetermined_predicted_pos.fasta"))), \
        "Receiving or prediction failed."
    assert (os.path.isfile(os.path.join("deepac-live-tests", "rec_out",
                                        "hilive_out_cycle508_undetermined_predicted_neg.fasta"))), \
        "Receiving or prediction failed."



