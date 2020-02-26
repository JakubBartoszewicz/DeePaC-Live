import pysam
import os


# TODO: get ambiguous
def get_unmapped_fasta(inpath, outpath_fasta, single=False, do_filter=True):
    # create the file upfront, so pysam can open it
    with open(outpath_fasta, 'w') as fp:
        pass
    # samtools view -bf 12 -o outpath inpath
    # set output in both pysam wrapper and samtools argument list
    if do_filter:
        if single:
            pysam.fasta("-f 4", inpath, save_stdout=outpath_fasta)
        else:
            pysam.fasta("-f 12", inpath, save_stdout=outpath_fasta)
    else:
        pysam.fasta(inpath, save_stdout=outpath_fasta)


def get_unmapped_bam(inpath, outpath_bam, single):
    # create the file upfront, so pysam can open it
    with open(outpath_bam, 'w') as fp:
        pass
    # samtools view -bf 12 -o outpath inpath
    # set output in both pysam wrapper and samtools argument list
    if single:
        pysam.view("-bf 4", "-o", outpath_bam, inpath, save_stdout=outpath_bam)
    else:
        pysam.view("-bf 12", "-o", outpath_bam, inpath, save_stdout=outpath_bam)


class Sender:
    def __init__(self, read_length, input_dir, output_dir):
        if not os.path.isdir(input_dir):
            os.mkdir(input_dir)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.read_length = read_length

    def run(self, cycles, mode="bam"):
        # TODO: send
        if mode == "bam":
            for c in cycles:
                print("Sending cycle {}.".format(c))
                single = c <= self.read_length
                inpath = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined.bam".format(c))
                outpath_bam = os.path.join(self.output_dir, "hilive_out_cycle{}_undetermined_unmapped.bam".format(c))
                get_unmapped_bam(inpath, outpath_bam, single)
        elif mode == "fasta":
            for c in cycles:
                print("Sending cycle {}.".format(c))
                inpath = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined.bam".format(c))
                outpath_fasta = os.path.join(self.output_dir, "hilive_out_cycle{}_undetermined_unmapped.fasta".format(c))
                get_unmapped_fasta(inpath, outpath_fasta)
        else:
            raise ValueError("Unrecognized sender format: {}".format(mode))
