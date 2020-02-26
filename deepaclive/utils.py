import numpy as np
from Bio.SeqIO.FastaIO import SimpleFastaParser
import itertools


def filter_paired_fasta(input_fasta_1, input_fasta_2, predictions_1, predictions_2,
                        output, threshold=0.5, print_potentials=False, precision=3):
    """Filter a reads in a fasta file by pathogenic potential."""
    with open(input_fasta_1) as in_handle:
        fasta_data_1 = [(title, seq) for (title, seq) in SimpleFastaParser(in_handle)]
    y_pred_1 = np.load(predictions_1, mmap_mode='r')
    with open(input_fasta_2) as in_handle:
        fasta_data_2 = [(title, seq) for (title, seq) in SimpleFastaParser(in_handle)]
    y_pred_2 = np.load(predictions_2, mmap_mode='r')
    y_pred = (y_pred_1 + y_pred_2)/2
    y_pred_class = (y_pred > threshold).astype('int8')
    fasta_filtered_1 = list(itertools.compress(fasta_data_1, y_pred_class))
    fasta_filtered_2 = list(itertools.compress(fasta_data_2, y_pred_class))
    if print_potentials and precision > 0:
        y_pred_filtered = [y for y in y_pred if y > threshold]
        with open(output, "w") as out_handle:
            for ((title, seq), y) in zip(fasta_filtered_1, y_pred_filtered):
                out_handle.write(
                    ">{}\n{}\n".format(title + " | pp={val:.{precision}f}".format(val=y, precision=precision), seq))

            for ((title, seq), y) in zip(fasta_filtered_2, y_pred_filtered):
                out_handle.write(
                    ">{}\n{}\n".format(title + " | pp={val:.{precision}f}".format(val=y, precision=precision), seq))
    else:
        with open(output, "w") as out_handle:
            for (title, seq) in fasta_filtered_1:
                out_handle.write(">{}\n{}\n".format(title, seq))
            for (title, seq) in fasta_filtered_1:
                out_handle.write(">{}\n{}\n".format(title, seq))
