# DeePaC-Live
A DeePaC plugin for real-time analysis of Illumina sequencing runs. Captures HiLive2 output and uses deep neural nets to
 detect novel pathogens directly from NGS reads. 
 
We recommend having a look at:

* DeePaC main repo: https://gitlab.com/rki_bioinformatics/DeePaC
    * tutorial
    * trained built-in models
    * datasets used for both original and deepac-live models
    * code and documentation

* HiLive2 repo: https://gitlab.com/rki_bioinformatics/HiLive2.
    * extensive tutorial
    * code and documentation
  
## Installation
```
# Optional, but recommended: for GPU users
conda install tensorflow-gpu
# Install deepac-live
conda install -c bioconda deepac-live
# Optional: viral built-in models
conda install -c bioconda deepacvir
```
Alternatively, you can also use pip:
```
# Optional, but recommended: for GPU users
pip install tensorflow-gpu
# Install deepac-live
pip install deepac-live
# Optional: viral built-in models
pip install deepacvir
```
## Basic usage
```
# Run locally: build-in model for bacteria
deepac-live local -c deepac -m rapid -s 25,50,75,100,133,158,183,208 -l 100 -i hilive-out -o temp -I temp -O output -B ACAG-TCGA,undetermined
# Run locally: build-in model for viruses
deepac-live local -c deepacvir -m rapid -s 25,50,75,100,133,158,183,208 -l 100 -i hilive-out -o temp -I temp -O output -B ACAG-TCGA,undetermined
# Run locally: custom model
deepac-live local -C -m custom_model.h5 -s 25,50,75,100,133,158,183,208 -l 100 -i hilive-out -o temp -I temp -O output -B ACAG-TCGA,undetermined
```

## Advanced usage
### Setting up a remote receiver
```
# Setup sender on the source machine
deepac-live sender -s 25,50,75,100,133,158,183,208 -l 100 -A -i hilive-out -o temp -r user@remote.host:~/rem-temp -k privatekey -B ACAG-TCGA,undetermined
# Setup receiver on the target machine
deepac-live receiver -c deepacvir -m rapid -s 25,50,75,100,133,158,183,208 -l 100 -I rem-temp -O output -B ACAG-TCGA,undetermined
```

### Refilter: ensembles and alternative thresholds
```
# Setup an ensemble on the target machine
deepac-live refilter -s 25,50,75,100,133,158,183,208 -l 100 -i rem-temp -I output_1,output_2 -O final_output -B ACAG-TCGA,undetermined
# Use another threshold
deepac-live refilter -s 25,50,75,100,133,158,183,208 -l 100 -i rem-temp -I output_1 -O final_output -t 0.75 -B ACAG-TCGA,undetermined
```
