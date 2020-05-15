import pysam
import os
import time
from deepaclive.sftp_client import sftp_push
from multiprocessing import cpu_count


class Sender:
    def __init__(self, read_length, input_dir, output_dir, user_hostname=None, key=None, port=22, n_cpus=None,
                 do_all=False, do_mapped=False):
        print("Setting up the sender...")
        self.input_dir = os.path.abspath(os.path.realpath(os.path.expanduser(input_dir)))
        self.output_dir = os.path.abspath(os.path.realpath(os.path.expanduser(output_dir)))
        if not os.path.isdir(self.input_dir):
            os.mkdir(self.input_dir)
        if not os.path.isdir(self.output_dir):
            os.mkdir(self.output_dir)
        self.read_length = read_length
        self.do_filter = not do_all
        self.do_mapped = do_mapped
        self.cores = n_cpus if n_cpus is not None else cpu_count()
        self.c_threads = str(self.cores - 1)
        self.user_hostname = user_hostname
        self.pkey = key
        if user_hostname is not None:
            print("***WARNING: Sending data to a remote server! "
                  "DO NOT send private data anywhere unless you know that (and why) you are allowed to.***")
            time.sleep(3)
            if key is None:
                print("***WARNING: No private key selected! Your connection is not secure. DO NOT send private data.***")
                time.sleep(5)
            else:
                self.pkey = os.path.abspath(os.path.realpath(os.path.expanduser(key)))
        self.port = port
        print("Sender ready.")

    def run(self, cycles, barcodes, mode="bam"):
        # copy by value
        cycles_todo = cycles[:]
        while len(cycles_todo) > 0:
            c = cycles_todo[0]
            single = c <= self.read_length
            barcodes_todo = barcodes[:]
            files = []
            while len(barcodes_todo) > 0:
                barcode = barcodes_todo[0]
                inpath = os.path.join(self.input_dir, "hilive_out_cycle{}_{}.bam".format(c, barcode))
                if os.path.exists(inpath):
                    print("Processing cycle {}, barcode {}.".format(c, barcode))
                    outpath = os.path.join(self.output_dir, "hilive_out_cycle{}_{}_deepac".format(c, barcode))
                    if mode == "bam":
                        if self.do_mapped:
                            outfiles = self.get_mapped_bam(inpath, outpath, single)
                        else:
                            outfiles = self.get_unmapped_bam(inpath, outpath, single, do_filter=self.do_filter)
                    elif mode == "fasta":
                        if self.do_mapped:
                            outfiles = self.get_mapped_fasta(inpath, outpath, single)
                        else:
                            outfiles = self.get_unmapped_fasta(inpath, outpath, single, do_filter=self.do_filter)
                    else:
                        raise ValueError("Unrecognized sender format: {}".format(mode))
                    files.append(outfiles[0])
                    if len(outfiles[1]) > 0:
                        files.append(outfiles[1])
                    barcodes_todo.pop(0)
                else:
                    time.sleep(1)
            if self.user_hostname is not None:
                sftp_push(self.user_hostname, files=files, key=self.pkey, port=self.port)
            cycles_todo.pop(0)
            if len(cycles_todo) > 0:
                print("Done. Sender awaiting cycle {}.".format(cycles_todo[0]))
            else:
                print("Sender done.")

    def get_unmapped_fasta(self, inpath, outpath, single=False, do_filter=True):
        # set output in both pysam wrapper and samtools argument list
        outpath_fasta_1 = outpath + "_1.fasta"
        # create the file upfront, so pysam can open it
        with open(outpath_fasta_1, 'w') as fp:
            pass
        if single:
            if do_filter:
                pysam.fasta("-f 4", "-@", self.c_threads, inpath, save_stdout=outpath_fasta_1)
            else:
                pysam.fasta(inpath, save_stdout=outpath_fasta_1)
            return outpath_fasta_1, ""
        else:
            if do_filter:
                pysam.fasta("-Nf 77", "-@", self.c_threads, inpath, save_stdout=outpath_fasta_1)
                outpath_fasta_2 = outpath + "_2.fasta"
                # create the file upfront, so pysam can open it
                with open(outpath_fasta_2, 'w') as fp:
                    pass
                pysam.fasta("-Nf 141", "-@", self.c_threads, inpath, save_stdout=outpath_fasta_2)
            else:
                pysam.fasta("-Nf 64", "-@", self.c_threads, inpath, save_stdout=outpath_fasta_1)
                outpath_fasta_2 = outpath + "_2.fasta"
                # create the file upfront, so pysam can open it
                with open(outpath_fasta_2, 'w') as fp:
                    pass
                pysam.fasta("-Nf 128", "-@", self.c_threads, inpath, save_stdout=outpath_fasta_2)
            return outpath_fasta_1, outpath_fasta_2

    def get_unmapped_bam(self, inpath, outpath, single=False, do_filter=True):
        outpath_bam_1 = outpath + "_1.bam"
        # create the file upfront, so pysam can open it
        with open(outpath_bam_1, 'w') as fp:
            pass
        # set output in both pysam wrapper and samtools argument list
        if single:
            if do_filter:
                pysam.view("-bf 4", "-@", self.c_threads, "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
            else:
                pysam.view("-b", "-@", self.c_threads, "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
            return outpath_bam_1, ""
        else:
            if do_filter:
                pysam.view("-bf 77", "-@", self.c_threads, "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
                outpath_bam_2 = outpath + "_2.bam"
                # create the file upfront, so pysam can open it
                with open(outpath_bam_2, 'w') as fp:
                    pass
                pysam.view("-bf 141", "-@", self.c_threads, "-o", outpath_bam_2, inpath, save_stdout=outpath_bam_2)
            else:
                pysam.view("-bf 64", "-@", self.c_threads, "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
                outpath_bam_2 = outpath + "_2.bam"
                # create the file upfront, so pysam can open it
                with open(outpath_bam_2, 'w') as fp:
                    pass
                pysam.view("-bf 128", "-@", self.c_threads, "-o", outpath_bam_2, inpath, save_stdout=outpath_bam_2)
            return outpath_bam_1, outpath_bam_2

    def get_mapped_bam(self, inpath, outpath, single=False):
        outpath_bam_1 = outpath + "_1.bam"
        # create the file upfront, so pysam can open it
        with open(outpath_bam_1, 'w') as fp:
            pass
        # set output in both pysam wrapper and samtools argument list
        if single:
            pysam.view("-bG 4", "-@", self.c_threads, "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)

            return outpath_bam_1, ""
        else:
            pysam.view("-bG 12", "-f 64", "-@", self.c_threads, "-o", outpath_bam_1, inpath, save_stdout=outpath_bam_1)
            outpath_bam_2 = outpath + "_2.bam"
            # create the file upfront, so pysam can open it
            with open(outpath_bam_2, 'w') as fp:
                pass
            pysam.view("-bG 12", "-f 128", "-@", self.c_threads, "-o", outpath_bam_2, inpath, save_stdout=outpath_bam_2)
            return outpath_bam_1, outpath_bam_2

    def get_mapped_fasta(self, inpath, outpath, single=False):
        # set output in both pysam wrapper and samtools argument list
        outpath_fasta_1 = outpath + "_1.fasta"
        # create the file upfront, so pysam can open it
        with open(outpath_fasta_1, 'w') as fp:
            pass
        if single:
            pysam.fasta("-G 4", "-@", self.c_threads, inpath, save_stdout=outpath_fasta_1)
            return outpath_fasta_1, ""
        else:
            pysam.fasta("-NG 12", "-f 64", "-@", self.c_threads, inpath, save_stdout=outpath_fasta_1)
            outpath_fasta_2 = outpath + "_2.fasta"
            # create the file upfront, so pysam can open it
            with open(outpath_fasta_2, 'w') as fp:
                pass
            pysam.fasta("-NG 12", "-f 128", "-@", self.c_threads, inpath, save_stdout=outpath_fasta_2)
            return outpath_fasta_1, outpath_fasta_2
