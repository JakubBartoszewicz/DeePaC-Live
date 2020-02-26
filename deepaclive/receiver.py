import os
import fnmatch
import importlib
from deepaclive.sender import get_unmapped_fasta
from deepac.predict import predict_fasta
from deepac.predict import filter_fasta
from deepac.builtin_loading import BuiltinLoader
from deepaclive.utils import filter_paired_fasta


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
        self.deepac = deepac_command
        self.builtin_configs, self.builtin_weights = get_builtin(self.deepac)

        if not os.path.isdir(input_dir):
            os.mkdir(input_dir)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        self.input_dir = input_dir
        self.output_dir = output_dir

        self.bloader = BuiltinLoader(self.builtin_configs, self.builtin_weights)

        if model == "rapid":
            self.model = self.bloader.load_rapid_model(n_cpus=n_cpus, n_gpus=n_gpus, training_mode=False)
        elif model == "sensitive":
            self.model = self.bloader.load_sensitive_model(n_cpus=n_cpus, n_gpus=n_gpus, training_mode=False)
        else:
            #TODO: custom models
            raise ValueError("Unrecognized model type: {}".format(model))

        self.threshold = threshold
        self.read_length = read_length

    def do_pred_bam(self, inpath_bam, outpath_npy):
        pre, ext = os.path.splitext(inpath_bam)
        temp_fasta = "{}.fasta".format(pre)
        get_unmapped_fasta(inpath=inpath_bam, outpath=pre, do_filter=False)
        self.do_pred_fasta(temp_fasta, outpath_npy)

    def do_pred_fasta(self, inpath_fasta, outpath_npy):
        predict_fasta(model=self.model, input_fasta=inpath_fasta, output=outpath_npy)

    def do_filter_fasta(self, inpath_fasta, preds_npy, outpath_fasta):
        filter_fasta(input_fasta=inpath_fasta, predictions=preds_npy, output=outpath_fasta,
                     threshold=self.threshold, print_potentials=True)

    def do_filter_paired_fasta(self, inpath_fasta_1, inpath_fasta_2, preds_npy_1, preds_npy_2, outpath_fasta):
        filter_paired_fasta(input_fasta_1=inpath_fasta_1, input_fasta_2=inpath_fasta_2, predictions_1=preds_npy_1,
                            predictions_2=preds_npy_2, output=outpath_fasta,
                            threshold=self.threshold, print_potentials=True)

    def run(self, cycles, mode="bam"):
        if mode == "bam":
            for c in cycles:
                print("Received cycle {}.".format(c))
                single = c <= self.read_length

                outpath_fasta = os.path.join(self.output_dir,
                                             "hilive_out_cycle{}_undetermined_filtered.fasta".format(c))

                inpath_bam_1 = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined_unmapped_1.bam".format(c))
                inpath_fasta_1 = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined_unmapped_1.fasta".format(c))
                outpath_npy_1 = os.path.join(self.output_dir, "hilive_out_cycle{}_undetermined_unmapped_1.npy".format(c))
                self.do_pred_bam(inpath_bam_1, outpath_npy_1)

                if single:
                    self.do_filter_fasta(inpath_fasta_1, outpath_npy_1, outpath_fasta)
                else:
                    inpath_bam_2 = os.path.join(self.input_dir,
                                                "hilive_out_cycle{}_undetermined_unmapped_2.bam".format(c))
                    inpath_fasta_2 = os.path.join(self.input_dir,
                                                  "hilive_out_cycle{}_undetermined_unmapped_2.fasta".format(c))
                    outpath_npy_2 = os.path.join(self.output_dir,
                                                 "hilive_out_cycle{}_undetermined_unmapped_2.npy".format(c))
                    self.do_pred_bam(inpath_bam_2, outpath_npy_2)
                    self.do_filter_paired_fasta(inpath_fasta_1, inpath_fasta_2, outpath_npy_1,outpath_npy_2,
                                                outpath_fasta)

        elif mode == "fasta":
            for c in cycles:
                print("Received cycle {}.".format(c))
                single = c <= self.read_length
                outpath_fasta = os.path.join(self.output_dir,
                                             "hilive_out_cycle{}_undetermined_filtered.fasta".format(c))
                inpath_fasta_1 = os.path.join(self.input_dir,
                                              "hilive_out_cycle{}_undetermined_unmapped_1.fasta".format(c))
                outpath_npy_1 = os.path.join(self.output_dir,
                                             "hilive_out_cycle{}_undetermined_unmapped_1.npy".format(c))
                self.do_pred_fasta(inpath_fasta_1, outpath_npy_2)

                if single:
                    self.do_filter_fasta(inpath_fasta_1, outpath_npy_1, outpath_fasta)
                else:
                    inpath_fasta_2 = os.path.join(self.input_dir,
                                                  "hilive_out_cycle{}_undetermined_unmapped_2.fasta".format(c))
                    outpath_npy_2 = os.path.join(self.output_dir,
                                                 "hilive_out_cycle{}_undetermined_unmapped_2.npy".format(c))
                    self.do_pred_fasta(inpath_fasta_2, outpath_npy_2)
                    self.do_filter_paired_fasta(inpath_fasta_1, inpath_fasta_2, outpath_npy_1,outpath_npy_2,
                                                outpath_fasta)
        else:
            raise ValueError("Unrecognized sender format: {}".format(mode))

    def refilter(self, cycles):
        for c in cycles:
            inpath_fasta = os.path.join(self.input_dir, "hilive_out_cycle{}_undetermined_unmapped.fasta".format(c))
            outpath_npy = os.path.join(self.output_dir, "hilive_out_cycle{}_undetermined_unmapped.npy".format(c))
            outpath_fasta = os.path.join(self.output_dir,
                                         "hilive_out_cycle{}_undetermined_filtered.fasta".format(c))
            self.do_filter_fasta(inpath_fasta, outpath_npy, outpath_fasta)
