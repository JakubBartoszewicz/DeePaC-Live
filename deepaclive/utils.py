import numpy as np
from Bio.SeqIO.FastaIO import SimpleFastaParser
import itertools


def ensemble(predictions_list, outpath_npy):
    ys = []
    for p in predictions_list:
        ys.append(np.load(p, mmap_mode='r'))
    ys = np.array(ys)
    y_pred = np.average(ys, 0)
    np.save(outpath_npy, y_pred)


def filter_paired_fasta(input_fasta_1, predictions_1, output_pos, input_fasta_2=None, predictions_2=None,
                        output_neg=None, threshold=0.5, print_potentials=False, precision=3):
    """Filter a reads in a fasta file by pathogenic potential."""
    with open(input_fasta_1) as in_handle:
        fasta_data_1 = [(title, seq) for (title, seq) in SimpleFastaParser(in_handle)]
    y_pred_1 = np.load(predictions_1, mmap_mode='r')
    if input_fasta_2 is not None:
        with open(input_fasta_2) as in_handle:
            fasta_data_2 = [(title, seq) for (title, seq) in SimpleFastaParser(in_handle)]
        y_pred_2 = np.load(predictions_2, mmap_mode='r')
        y_pred = (y_pred_1 + y_pred_2)/2
    else:
        y_pred = y_pred_1
    y_pred_pos = (y_pred > threshold).astype('int8')
    y_pred_neg = (y_pred <= threshold).astype('int8')

    fasta_pos_1 = list(itertools.compress(fasta_data_1, y_pred_pos))
    fasta_neg_1 = list(itertools.compress(fasta_data_1, y_pred_neg))
    if input_fasta_2 is not None:
        fasta_pos_2 = list(itertools.compress(fasta_data_2, y_pred_pos))
        fasta_neg_2 = list(itertools.compress(fasta_data_2, y_pred_neg))
    else:
        fasta_pos_2 = []
        fasta_neg_2 = []
    if print_potentials and precision > 0:
        y_pred_pos = [y for y in y_pred if y > threshold]
        with open(output_pos, "w") as out_handle:
            for ((title, seq), y) in zip(fasta_pos_1, y_pred_pos):
                out_handle.write(
                    ">{}\n{}\n".format(title + " | pp={val:.{precision}f}".format(val=y, precision=precision), seq))
            if input_fasta_2 is not None:
                for ((title, seq), y) in zip(fasta_pos_2, y_pred_pos):
                    out_handle.write(
                        ">{}\n{}\n".format(title + " | pp={val:.{precision}f}".format(val=y,
                                                                                      precision=precision), seq))
        if output_neg is not None:
            y_pred_neg = [y for y in y_pred if y <= threshold]
            with open(output_neg, "w") as out_handle:
                for ((title, seq), y) in zip(fasta_neg_1, y_pred_neg):
                    out_handle.write(
                        ">{}\n{}\n".format(title + " | pp={val:.{precision}f}".format(val=y, precision=precision), seq))
                if input_fasta_2 is not None:
                    for ((title, seq), y) in zip(fasta_neg_2, y_pred_neg):
                        out_handle.write(
                            ">{}\n{}\n".format(title + " | pp={val:.{precision}f}".format(val=y,
                                                                                          precision=precision), seq))
    else:
        with open(output_pos, "w") as out_handle:
            for (title, seq) in fasta_pos_1:
                out_handle.write(">{}\n{}\n".format(title, seq))
            if input_fasta_2 is not None:
                for (title, seq) in fasta_pos_2:
                    out_handle.write(">{}\n{}\n".format(title, seq))
        if output_neg is not None:
            with open(output_neg, "w") as out_handle:
                for (title, seq) in fasta_neg_1:
                    out_handle.write(">{}\n{}\n".format(title, seq))
                if input_fasta_2 is not None:
                    for (title, seq) in fasta_neg_2:
                        out_handle.write(">{}\n{}\n".format(title, seq))