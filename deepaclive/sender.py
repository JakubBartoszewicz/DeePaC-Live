import pysam
import os
import time


def get_unmapped_fasta(inpath, outpath, single=False, do_filter=True):
    # set output in both pysam wrapper and samtools argument list
    outpath_fasta_1 = outpath + "_1.fasta"
    # create the file upfront, so pysam can open it
    with open(outpath_fasta_1, 'w') as fp:
        pass
    if single:
        if do_filter:
            pysam.fasta("-f 4", inpath, save_stdout=outpath_fasta_1)
        else:
            pysam.fasta(inpath, save_stdout=outpath_fasta_1)
    else:
        if do_filter:
            pysam.fasta("-f 77", inpath, save_stdout=outpath_fasta_1)
            outpath_fasta_2 = outpath + "_2.fasta"
            # create the file upfront, so pysam can open it
            with open(outpath_fasta_2, 'w') as fp:
                pass
            pysam.fasta("-f 141", inpath, save_stdout=outpath_fasta_2)
        else:
            pysam.fasta("-f 64", inpath, save_stdout=outpath_fasta_1)
            outpath_fasta_2 = outpath + "_2.fasta"
            # create the file upfront, so pysam can open it
            with open(outpath_fasta_2, 'w') as fp:
                pass
            pysam.fasta("-f 128", inpath, save_stdout=outpath_fasta_2)


def get_unmapped_bam(inpath, outpath, single=False, do_filter=True):
    outpath_bam_1 = outpath + "_1.bam"
    # create the file upfront, so pysam can open it
    with open(outpath_bam_1, 'w') as fp:
        pass
    # set output in both pysam wrapper and samtools argument list
    if single:
        if do_filter:
            pysam.view("-bf 4", "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
        else:
            pysam.view("-b", "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
    else:
        if do_filter:
            pysam.view("-bf 77", "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
            outpath_bam_2 = outpath + "_2.bam"
            # create the file upfront, so pysam can open it
            with open(outpath_bam_2, 'w') as fp:
                pass
            pysam.view("-bf 141", "-o", outpath_bam_2, inpath, save_stdout=outpath_bam_2)
        else:
            pysam.view("-bf 64", "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
            outpath_bam_2 = outpath + "_2.bam"
            # create the file upfront, so pysam can open it
            with open(outpath_bam_2, 'w') as fp:
                pass
            pysam.view("-bf 128", "-o", outpath_bam_2, inpath, save_stdout=outpath_bam_2)


class Sender:
    def __init__(self, read_length, input_dir, output_dir, do_all=False):
        print("Setting up the sender...")
        if not os.path.isdir(input_dir):
            os.mkdir(input_dir)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.read_length = read_length
        self.do_filter = not do_all
        print("Sender ready.")

    def run(self, cycles, barcodes, mode="bam"):
        # TODO: send
        # copy by value
        cycles_todo = cycles[:]
        while len(cycles_todo) > 0:
            c = cycles_todo[0]
            single = c <= self.read_length
            barcodes_todo = barcodes[:]
            while len(barcodes_todo) > 0:
                barcode = barcodes_todo[0]
                inpath = os.path.join(self.input_dir, "hilive_out_cycle{}_{}.bam".format(c, barcode))
                if os.path.exists(inpath):
                    print("Sending cycle {}, barcode {}.".format(c, barcode))
                    outpath = os.path.join(self.output_dir, "hilive_out_cycle{}_{}_deepac".format(c, barcode))
                    if mode == "bam":
                        get_unmapped_bam(inpath, outpath, single, do_filter=self.do_filter)
                    elif mode == "fasta":
                        get_unmapped_fasta(inpath, outpath, single, do_filter=self.do_filter)
                    else:
                        raise ValueError("Unrecognized sender format: {}".format(mode))
                    barcodes_todo.pop(0)
                else:
                    time.sleep(1)
            cycles_todo.pop(0)
            if len(cycles_todo) > 0:
                print("Done. Sender awaiting cycle {}.".format(cycles_todo[0]))
            else:
                print("Sender done.")

