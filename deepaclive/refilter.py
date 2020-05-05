import os
from deepac.predict import filter_paired_fasta, ensemble
import time


class Refilterer:
    def __init__(self, read_length, input_fasta_dir, input_npy_dirs, output_dir, threshold=0.5):
        print("Setting up the refilterer...")
        self.input_fasta_dir = os.path.abspath(os.path.realpath(os.path.expanduser(input_fasta_dir)))
        self.input_npy_dirs = [os.path.abspath(os.path.realpath(os.path.expanduser(i))) for i in input_npy_dirs]
        self.output_dir = os.path.abspath(os.path.realpath(os.path.expanduser(output_dir)))
        for i in self.input_npy_dirs:
            if not os.path.isdir(i):
                os.mkdir(i)
        if not os.path.isdir(self.output_dir):
            os.mkdir(self.output_dir)
        self.threshold = threshold
        self.read_length = read_length
        print("Refilterer ready.")

    def do_filter_fasta(self, inpath_fasta, preds_npy, out_fasta_pos, out_fasta_neg):
        if os.path.exists(inpath_fasta) and os.stat(inpath_fasta).st_size != 0:
            filter_paired_fasta(input_fasta_1=inpath_fasta, predictions_1=preds_npy, output_pos=out_fasta_pos,
                                output_neg=out_fasta_neg, threshold=self.threshold, print_potentials=True)

    def do_filter_paired_fasta(self, inpath_fasta_1, inpath_fasta_2, preds_npy_1, preds_npy_2, out_fasta_pos,
                               out_fasta_neg=None):
        if os.path.exists(inpath_fasta_1) and os.stat(inpath_fasta_1).st_size != 0:
            filter_paired_fasta(input_fasta_1=inpath_fasta_1, predictions_1=preds_npy_1, output_pos=out_fasta_pos,
                                input_fasta_2=inpath_fasta_2, predictions_2=preds_npy_2, output_neg=out_fasta_neg,
                                threshold=self.threshold, print_potentials=True)

    def run(self, cycles, barcodes, discard_neg=False):
        # copy by value
        cycles_todo = cycles[:]

        while len(cycles_todo) > 0:
            c = cycles_todo[0]
            single = c <= self.read_length
            barcodes_todo = barcodes[:]
            while len(barcodes_todo) > 0:
                barcode = barcodes_todo[0]
                inpath_fasta_1 = os.path.join(self.input_fasta_dir,
                                              "hilive_out_cycle{}_{}_deepac_1.fasta".format(c, barcode))
                inpath_fasta_2 = os.path.join(self.input_fasta_dir,
                                              "hilive_out_cycle{}_{}_deepac_2.fasta".format(c, barcode))
                inpath_npys_1 = [os.path.join(i, "hilive_out_cycle{}_{}_deepac_1.npy".format(c, barcode))
                                 for i in self.input_npy_dirs]
                inpath_npys_2 = [os.path.join(i, "hilive_out_cycle{}_{}_deepac_2.npy".format(c, barcode))
                                 for i in self.input_npy_dirs]

                singles_exist = single and all([os.path.exists(i) for i in inpath_npys_1])
                pairs_exist = all([os.path.exists(i) for i in inpath_npys_1]) and all(
                    [os.path.exists(i) for i in inpath_npys_2])

                fasta_valid_1 = os.path.exists(inpath_fasta_1) and os.stat(inpath_fasta_1).st_size != 0
                fasta_valid_2 = os.path.exists(inpath_fasta_2) and os.stat(inpath_fasta_2).st_size != 0

                if singles_exist or pairs_exist:
                    if (single and fasta_valid_1) or (fasta_valid_1 and fasta_valid_2):
                        print("Refiltering cycle {}, barcode {}.".format(c, barcode))

                        out_fasta_pos = os.path.join(self.output_dir,
                                                     "hilive_out_cycle{}_{}_predicted_pos.fasta".format(c, barcode))
                        if discard_neg:
                            out_fasta_neg = None
                        else:
                            out_fasta_neg = os.path.join(self.output_dir,
                                                         "hilive_out_cycle{}_{}_predicted_neg.fasta".format(c, barcode))
                        outpath_npy_1 = os.path.join(self.output_dir,
                                                     "hilive_out_cycle{}_{}_deepac_1.npy".format(c, barcode))
                        ensemble(inpath_npys_1, outpath_npy_1)

                        if single:
                            self.do_filter_fasta(inpath_fasta_1, outpath_npy_1, out_fasta_pos, out_fasta_neg)
                        else:
                            outpath_npy_2 = os.path.join(self.output_dir,
                                                         "hilive_out_cycle{}_{}_deepac_2.npy".format(c, barcode))
                            ensemble(inpath_npys_2, outpath_npy_2)

                            self.do_filter_paired_fasta(inpath_fasta_1, inpath_fasta_2, outpath_npy_1, outpath_npy_2,
                                                        out_fasta_pos, out_fasta_neg)
                    barcodes_todo.pop(0)
                else:
                    time.sleep(1)
            cycles_todo.pop(0)
            if len(cycles_todo) > 0:
                print("Done. Refilterer awaiting cycle {}.".format(cycles_todo[0]))
            else:
                print("All predictions done")
