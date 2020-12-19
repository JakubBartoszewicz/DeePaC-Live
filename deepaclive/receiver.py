import os
import fnmatch
import importlib
from deepac.predict import predict_fasta, filter_paired_fasta
from deepac.builtin_loading import BuiltinLoader
import tensorflow as tf
from tensorflow.keras.models import load_model
import time
import pysam
import numpy as np
from multiprocessing import cpu_count


def get_builtin(deepac_command):
    deepac_module = importlib.import_module(deepac_command)
    modulepath = os.path.dirname(deepac_module.__file__)
    rapid_ini = None
    sensitive_ini = None
    rapid_h5 = None
    sensitive_h5 = None

    for file in os.listdir(os.path.join(modulepath, "builtin", "config")):
        if fnmatch.fnmatch(file, '*rapid*ini'):
            if rapid_ini is not None:
                raise ValueError("Multiple rapid models in module {}".format(deepac_command))
            rapid_ini = file
        if fnmatch.fnmatch(file, '*sensitive*ini'):
            if sensitive_ini is not None:
                raise ValueError("Multiple sensitive models in module {}".format(deepac_command))
            sensitive_ini = file

    for file in os.listdir(os.path.join(modulepath, "builtin", "weights")):
        if fnmatch.fnmatch(file, '*rapid*h5'):
            if rapid_h5 is not None:
                raise ValueError("Multiple rapid models in module {}".format(deepac_command))
            rapid_h5 = file
        if fnmatch.fnmatch(file, '*sensitive*h5'):
            if sensitive_h5 is not None:
                raise ValueError("Multiple sensitive models in module {}".format(deepac_command))
            sensitive_h5 = file

    if rapid_ini is None or rapid_h5 is None:
        raise ValueError("Rapid model missing in module {}".format(deepac_command))
    if sensitive_ini is None or sensitive_h5 is None:
        raise ValueError("Sensitive model missing in module {}".format(deepac_command))

    builtin_configs = {"rapid": os.path.join(modulepath, "builtin", "config", rapid_ini),
                       "sensitive": os.path.join(modulepath, "builtin", "config", sensitive_ini)}
    builtin_weights = {"rapid": os.path.join(modulepath, "builtin", "weights", rapid_h5),
                       "sensitive": os.path.join(modulepath, "builtin", "weights", sensitive_h5)}

    return builtin_configs, builtin_weights


class Receiver:
    def __init__(self, deepac_command, model, read_length, input_dir, output_dir, n_cpus=None, threshold=0.5,
                 tpu_resolver=None):
        print("Setting up the receiver...")

        self.input_dir = os.path.abspath(os.path.realpath(os.path.expanduser(input_dir)))
        self.output_dir = os.path.abspath(os.path.realpath(os.path.expanduser(output_dir)))
        if not os.path.isdir(self.input_dir):
            os.mkdir(self.input_dir)
        if not os.path.isdir(self.output_dir):
            os.mkdir(self.output_dir)

        self.deepac = deepac_command
        if self.deepac is not None:
            # load a built-in model
            self.builtin_configs, self.builtin_weights = get_builtin(self.deepac)
            self.bloader = BuiltinLoader(self.builtin_configs, self.builtin_weights)

            if model == "rapid":
                self.model = self.bloader.load_rapid_model(training_mode=False, tpu_resolver=tpu_resolver)
            elif model == "sensitive":
                self.model = self.bloader.load_sensitive_model( training_mode=False, tpu_resolver=tpu_resolver)
            else:
                raise ValueError("Unrecognized model type: {}".format(model))
        else:
            # load custom model
            if tpu_resolver is not None:
                tpu_strategy = tf.distribute.experimental.TPUStrategy(tpu_resolver)
                with tpu_strategy.scope():
                    self.model = load_model(model)
            else:
                self.model = load_model(model)

        self.threshold = threshold
        self.read_length = read_length
        self.cores = n_cpus if n_cpus is not None else cpu_count()

        print("Receiver ready.")

    def do_pred_bam(self, inpath_bam, outpath_npy):
        if os.stat(inpath_bam).st_size != 0:
            pre, ext = os.path.splitext(inpath_bam)
            temp_fasta = "{}.fasta".format(pre)
            # create the file upfront, so pysam can open it
            with open(temp_fasta, 'w') as fp:
                pass
            pysam.fasta("-@", str(self.cores - 1), inpath_bam, save_stdout=temp_fasta)
            self.do_pred_fasta(temp_fasta, outpath_npy)
        else:
            np.save(outpath_npy, np.empty(0))

    def do_pred_fasta(self, inpath_fasta, outpath_npy):
        if os.stat(inpath_fasta).st_size != 0:
            predict_fasta(model=self.model, input_fasta=inpath_fasta, output=outpath_npy, token_cores=self.cores)
        else:
            np.save(outpath_npy, np.empty(0))

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

    def run(self, cycles, barcodes, mode="bam", discard_neg=False):
        # copy by value
        cycles_todo = cycles[:]
        if mode != "bam" and mode != "fasta":
            raise ValueError("Unrecognized sender format: {}".format(mode))

        while len(cycles_todo) > 0:
            c = cycles_todo[0]
            single = c <= self.read_length
            barcodes_todo = barcodes[:]
            while len(barcodes_todo) > 0:
                barcode = barcodes_todo[0]
                inpath_bam_1 = os.path.join(self.input_dir, "hilive_out_cycle{}_{}_deepac_1.bam".format(c, barcode))
                inpath_bam_2 = os.path.join(self.input_dir, "hilive_out_cycle{}_{}_deepac_2.bam".format(c, barcode))
                inpath_fasta_1 = os.path.join(self.input_dir, "hilive_out_cycle{}_{}_deepac_1.fasta".format(c, barcode))
                inpath_fasta_2 = os.path.join(self.input_dir, "hilive_out_cycle{}_{}_deepac_2.fasta".format(c, barcode))

                if mode == "bam":
                    single_exists = single and os.path.exists(inpath_bam_1)
                    pair_exists = os.path.exists(inpath_bam_1) and os.path.exists(inpath_bam_2)
                else:
                    single_exists = single and os.path.exists(inpath_fasta_1)
                    pair_exists = os.path.exists(inpath_fasta_1) and os.path.exists(inpath_fasta_2)

                if single_exists or pair_exists:
                    print("Received cycle {}, barcode {}.".format(c, barcode))

                    out_fasta_pos = os.path.join(self.output_dir,
                                                 "hilive_out_cycle{}_{}_predicted_pos.fasta".format(c, barcode))
                    if discard_neg:
                        out_fasta_neg = None
                    else:
                        out_fasta_neg = os.path.join(self.output_dir,
                                                     "hilive_out_cycle{}_{}_predicted_neg.fasta".format(c, barcode))
                    outpath_npy_1 = os.path.join(self.output_dir,
                                                 "hilive_out_cycle{}_{}_deepac_1.npy".format(c, barcode))
                    if mode == "bam":
                        self.do_pred_bam(inpath_bam_1, outpath_npy_1)
                    else:
                        # mode == "fasta"
                        self.do_pred_fasta(inpath_fasta_1, outpath_npy_1)

                    if single:
                        self.do_filter_fasta(inpath_fasta_1, outpath_npy_1, out_fasta_pos, out_fasta_neg)
                    else:
                        outpath_npy_2 = os.path.join(self.output_dir,
                                                     "hilive_out_cycle{}_{}_deepac_2.npy".format(c, barcode))
                        if mode == "bam":
                            self.do_pred_bam(inpath_bam_2, outpath_npy_2)
                        else:
                            self.do_pred_fasta(inpath_fasta_2, outpath_npy_2)

                        self.do_filter_paired_fasta(inpath_fasta_1, inpath_fasta_2, outpath_npy_1, outpath_npy_2,
                                                    out_fasta_pos, out_fasta_neg)
                    barcodes_todo.pop(0)
                else:
                    time.sleep(1)
            cycles_todo.pop(0)
            if len(cycles_todo) > 0:
                print("Done. Receiver awaiting cycle {}.".format(cycles_todo[0]))
            else:
                print("All predictions done")

    def refilter(self, cycles, barcodes, discard_neg=False):
        for c in cycles:
            for barcode in barcodes:
                inpath_fasta_1 = os.path.join(self.input_dir, "hilive_out_cycle{}_{}_deepac_1.fasta".format(c, barcode))
                outpath_npy_1 = os.path.join(self.output_dir, "hilive_out_cycle{}_{}_deepac_1.npy".format(c, barcode))
                out_fasta_pos = os.path.join(self.output_dir,
                                             "hilive_out_cycle{}_{}_predicted_pos.fasta".format(c, barcode))
                if discard_neg:
                    out_fasta_neg = None
                else:
                    out_fasta_neg = os.path.join(self.output_dir,
                                                 "hilive_out_cycle{}_{}_predicted_pos.fasta".format(c, barcode))

                single = c <= self.read_length
                if single:
                    self.do_filter_fasta(inpath_fasta_1, outpath_npy_1, out_fasta_pos, out_fasta_neg)
                else:
                    inpath_fasta_2 = os.path.join(self.input_dir,
                                                  "hilive_out_cycle{}_{}_deepac_2.fasta".format(c, barcode))
                    outpath_npy_2 = os.path.join(self.output_dir,
                                                 "hilive_out_cycle{}_{}_deepac_2.npy".format(c, barcode))

                    self.do_filter_paired_fasta(inpath_fasta_1, inpath_fasta_2, outpath_npy_1, outpath_npy_2,
                                                out_fasta_pos, out_fasta_neg)
