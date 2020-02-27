import os
import fnmatch
import importlib
from deepaclive.sender import get_unmapped_fasta
from deepac.predict import predict_fasta
from deepac.predict import filter_fasta
from deepac.builtin_loading import BuiltinLoader
from deepaclive.utils import filter_paired_fasta
from tensorflow.compat.v1.keras.models import load_model
import time
import pysam


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
    def __init__(self, deepac_command, model, read_length, input_dir, output_dir, n_cpus=8, n_gpus=0, threshold=0.5):
        print("Setting up the receiver...")
        self.deepac = deepac_command
        if self.deepac is not None:
            # load a built-in model
            self.builtin_configs, self.builtin_weights = get_builtin(self.deepac)
            self.bloader = BuiltinLoader(self.builtin_configs, self.builtin_weights)

            if model == "rapid":
                self.model = self.bloader.load_rapid_model(n_cpus=n_cpus, n_gpus=n_gpus, training_mode=False)
            elif model == "sensitive":
                self.model = self.bloader.load_sensitive_model(n_cpus=n_cpus, n_gpus=n_gpus, training_mode=False)
            else:
                raise ValueError("Unrecognized model type: {}".format(model))
        else:
            # load custom model
            self.model = load_model(model)

        self.threshold = threshold
        self.read_length = read_length

        if not os.path.isdir(input_dir):
            os.mkdir(input_dir)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        self.input_dir = input_dir
        self.output_dir = output_dir
        print("Receiver ready.")

    def do_pred_bam(self, inpath_bam, outpath_npy):
        pre, ext = os.path.splitext(inpath_bam)
        temp_fasta = "{}.fasta".format(pre)
        # create the file upfront, so pysam can open it
        with open(temp_fasta, 'w') as fp:
            pass
        pysam.fasta(inpath_bam, save_stdout=temp_fasta)
        self.do_pred_fasta(temp_fasta, outpath_npy)

    def do_pred_fasta(self, inpath_fasta, outpath_npy):
        predict_fasta(model=self.model, input_fasta=inpath_fasta, output=outpath_npy)

    def do_filter_fasta(self, inpath_fasta, preds_npy, out_fasta_pos, out_fasta_neg):
        filter_paired_fasta(input_fasta_1=inpath_fasta, predictions_1=preds_npy, output_pos=out_fasta_pos,
                            output_neg=out_fasta_neg, threshold=self.threshold, print_potentials=True)

    def do_filter_paired_fasta(self, inpath_fasta_1, inpath_fasta_2, preds_npy_1, preds_npy_2, out_fasta_pos,
                               out_fasta_neg=None):
        filter_paired_fasta(input_fasta_1=inpath_fasta_1, predictions_1=preds_npy_1, output_pos=out_fasta_pos,
                            input_fasta_2=inpath_fasta_2, predictions_2=preds_npy_2, output_neg=out_fasta_neg,
                            threshold=self.threshold, print_potentials=True)

    def run(self, cycles, mode="bam", discard_neg=False):
        # TODO: barcodes
        # copy by value
        cycles_todo = cycles[:]
        while len(cycles_todo) > 0:
            c = cycles_todo[0]
            single = c <= self.read_length
            inpath_bam_1 = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined_deepac_1.bam".format(c))
            inpath_bam_2 = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined_deepac_2.bam".format(c))

            if (single and os.path.exists(inpath_bam_1)) \
                    or (os.path.exists(inpath_bam_1) and os.path.exists(inpath_bam_2)):
                print("Received cycle {}.".format(c))

                out_fasta_pos = os.path.join(self.output_dir,
                                             "hilive_out_cycle{}_undetermined_predicted_pos.fasta".format(c))
                if discard_neg:
                    out_fasta_neg = None
                else:
                    out_fasta_neg = os.path.join(self.output_dir,
                                                 "hilive_out_cycle{}_undetermined_predicted_pos.fasta".format(c))
                inpath_fasta_1 = os.path.join(self.input_dir,
                                              "hilive_out_cycle{}_undetermined_deepac_1.fasta".format(c))
                outpath_npy_1 = os.path.join(self.output_dir,
                                             "hilive_out_cycle{}_undetermined_deepac_1.npy".format(c))
                if mode == "bam":
                    self.do_pred_bam(inpath_bam_1, outpath_npy_1)
                elif mode == "fasta":
                    self.do_pred_fasta(inpath_fasta_1, outpath_npy_1)
                else:
                    raise ValueError("Unrecognized sender format: {}".format(mode))

                if single:
                    self.do_filter_fasta(inpath_fasta_1, outpath_npy_1, out_fasta_pos, out_fasta_neg)
                else:
                    inpath_fasta_2 = os.path.join(self.input_dir,
                                                  "hilive_out_cycle{}_undetermined_deepac_2.fasta".format(c))
                    outpath_npy_2 = os.path.join(self.output_dir,
                                                 "hilive_out_cycle{}_undetermined_deepac_2.npy".format(c))
                    if mode == "bam":
                        self.do_pred_bam(inpath_bam_2, outpath_npy_2)
                    elif mode == "fasta":
                        self.do_pred_fasta(inpath_fasta_2, outpath_npy_2)
                    else:
                        raise ValueError("Unrecognized sender format: {}".format(mode))

                    self.do_filter_paired_fasta(inpath_fasta_1, inpath_fasta_2, outpath_npy_1, outpath_npy_2,
                                                out_fasta_pos, out_fasta_neg)
                cycles_todo.pop(0)
                if len(cycles_todo) > 0:
                    print("Done. Receiver awaiting cycle {}.".format(cycles_todo[0]))
                else:
                    print("All predictions done")
            else:
                time.sleep(1)

    def refilter(self, cycles, discard_neg=False):
        for c in cycles:
            inpath_fasta_1 = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined_deepac_1.fasta".format(c))
            outpath_npy_1 = os.path.join(self.output_dir, "hilive_out_cycle{}_undetermined_deepac_1.npy".format(c))
            out_fasta_pos = os.path.join(self.output_dir,
                                         "hilive_out_cycle{}_undetermined_predicted_pos.fasta".format(c))
            if discard_neg:
                out_fasta_neg = None
            else:
                out_fasta_neg = os.path.join(self.output_dir,
                                             "hilive_out_cycle{}_undetermined_predicted_pos.fasta".format(c))

            single = c <= self.read_length
            if single:
                self.do_filter_fasta(inpath_fasta_1, outpath_npy_1, out_fasta_pos, out_fasta_neg)
            else:
                inpath_fasta_2 = os.path.join(self.input_dir,
                                              "hilive_out_cycle{}_undetermined_deepac_2.fasta".format(c))
                outpath_npy_2 = os.path.join(self.output_dir,
                                             "hilive_out_cycle{}_undetermined_deepac_2.npy".format(c))

                self.do_filter_paired_fasta(inpath_fasta_1, inpath_fasta_2, outpath_npy_1, outpath_npy_2,
                                            out_fasta_pos, out_fasta_neg)
