import pysam
import os


# TODO: get ambiguous
def get_unmapped_fasta(inpath, outpath, single=False, do_filter=True):
    # samtools view -bf 12 -o outpath inpath
    # set output in both pysam wrapper and samtools argument list
    if do_filter:
        outpath_fasta_1 = outpath + "_1.fasta"
        # create the file upfront, so pysam can open it
        with open(outpath_fasta_1, 'w') as fp:
            pass
        if single:
            pysam.fasta("-f 4", inpath, save_stdout=outpath_fasta_1)
        else:
            pysam.fasta("-f 77", inpath, save_stdout=outpath_fasta_1)
            outpath_fasta_2 = outpath + "_2.fasta"
            # create the file upfront, so pysam can open it
            with open(outpath_fasta_2, 'w') as fp:
                pass
            pysam.fasta("-f 141", inpath, save_stdout=outpath_fasta_2)
    else:
        outpath_fasta = outpath + ".fasta"
        # create the file upfront, so pysam can open it
        with open(outpath_fasta, 'w') as fp:
            pass
        pysam.fasta(inpath, save_stdout=outpath_fasta)


def get_unmapped_bam(inpath, outpath, single=False):
    outpath_bam_1 = outpath + "_1.bam"
    # create the file upfront, so pysam can open it
    with open(outpath_bam_1, 'w') as fp:
        pass
    # samtools view -bf 12 -o outpath inpath
    # set output in both pysam wrapper and samtools argument list
    if single:
        pysam.view("-bf 4", "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
    else:
        pysam.view("-bf 77", "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
        outpath_bam_2 = outpath + "_2.bam"
        # create the file upfront, so pysam can open it
        with open(outpath_bam_2, 'w') as fp:
            pass

        pysam.view("-bf 141", "-o", outpath_bam_2, inpath, save_stdout=outpath_bam_1)


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
                outpath = os.path.join(self.output_dir, "hilive_out_cycle{}_undetermined_unmapped".format(c))
                get_unmapped_bam(inpath, outpath, single)
        elif mode == "fasta":
            for c in cycles:
                print("Sending cycle {}.".format(c))
                single = c <= self.read_length
                inpath = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined.bam".format(c))
                outpath = os.path.join(self.output_dir, "hilive_out_cycle{}_undetermined_unmapped".format(c))
                get_unmapped_fasta(inpath, outpath, single)
        else:
            raise ValueError("Unrecognized sender format: {}".format(mode))
